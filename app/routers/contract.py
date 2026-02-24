import os
import json
import time
import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.utils.mongodb_logger import log_to_mongo
from pydantic import BaseModel
from openai import AsyncOpenAI

router = APIRouter()

# Initialize OpenAI client variable
_client = None

def get_client():
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _client

from typing import Optional

class ContractRequest(BaseModel):
    file_url: Optional[str] = None
    local_filename: Optional[str] = None
    bank: str = "itau"

SYSTEM_PROMPT = """Voce e um analista senior de contratos imobiliarios do Banco Itau.
Seu papel e analisar o PDF completo do contrato e devolver um unico resultado consolidado.
Nao invente informacoes. Responda apenas em JSON valido conforme o esquema definido."""

USER_PROMPT = """Analise o PDF completo e consolide os campos abaixo.
Instrucoes detalhadas:
- Numero do contrato: Identifique o número do contrato impresso, localizado preferencialmente na página que contém o logo do Banco Itaú. Ignore números manuscritos (escritos à mão) pois geralmente são números de protocolo.
- Logo Itau: true se apareceu em alguma pagina.
- Clausulas: true se houver paginas com texto de clausulas.
- Quadro resumo: usar summary_registration_number e verbacao_creditor encontrados no quadro.
- Clausula de seguro: exists=true se alguma pagina indicar clausula de seguro; clause_number se visivel.
- Matricula: received=true se houver pagina cartorial; numero se legivel.
- Assinaturas: true se houver evidencia clara das assinaturas obrigatorias.
- Portabilidade: true se houver evidencia de portabilidade.
- Verbacao (credor): considere como Itau se o credor consolidado contiver "itau" ou "itau unibanco" ou "itau unibanco s.a.".
- Justificativas: para cada regra critica, se o valor final for null ou false, explique de forma objetiva o que nao foi encontrado nas paginas. Para contrato_assinado, a justificativa deve ser mais detalhada, citando quais assinaturas nao foram vistas.
Regras:
- Se houver conflito, escolha o valor mais consistente com a maioria das paginas ou com maior clareza textual.
- Se nenhuma pagina tiver indicio visual do campo, use null.
- Nao invente numeros.
- Para SEGURO: se qualquer pagina mencionar MIP/DFI/seguro habitacional, consolidar exists=true.
- Para CORRESPONDENCIA DO IMOVEL: se qualquer pagina tiver matricula + cartorio + descricao/endereco do imovel ou quadro resumo com imovel, consolidar SIM.
- Para ASSINATURAS: se houver bloco de assinaturas em alguma pagina, consolidar true para as partes visiveis; nao usar null se o bloco existir.
Retorne exatamente este JSON (sem comentarios):
{
  "contract_number": { "value": string|null, "found": boolean|null, "legible": boolean|null },
  "itau_logo_present": boolean|null,
  "contract_clauses_present": boolean|null,
  "contract_legible": boolean|null,
  "insurance_clause": { "exists": boolean|null, "clause_number": number|null },
  "registration": { "received": boolean|null, "legible": boolean|null, "number": string|null },
  "summary_registration_number": string|null,
  "verbacao_creditor": string|null,
  "signatures": { "bank": boolean|null, "intermediary": boolean|null, "financed": boolean|null, "previous_bank": boolean|null },
  "portability_case": boolean|null,
  "notes": string|null,
  "justificativas_criticas": {
    "contrato_recebido": string|null,
    "contrato_legivel": string|null,
    "matricula_recebida": string|null,
    "matricula_legivel": string|null,
    "correspondencia_imovel": string|null,
    "verbacao": string|null,
    "contrato_assinado": string|null
  }
}"""

async def delete_temp_file(path: str):
    try:
        os.remove(path)
    except Exception:
        pass

@router.post("/analyze-contract-file")
async def analyze_contract_file(request: ContractRequest, background_tasks: BackgroundTasks):
    start_time = time.time()
    try:
        tmp_path = None
        
        # 1. Obtain File (URL or Local)
        if request.local_filename:
            # Secure path handling
            base_dir = os.path.join(os.getcwd(), "exemplos pdf")
            file_path = os.path.join(base_dir, request.local_filename)
            
            # Simple path traversal check
            if not os.path.abspath(file_path).startswith(os.path.abspath(base_dir)):
                 raise HTTPException(status_code=400, detail="Invalid file path")
            
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="Local file not found in 'exemplos pdf' directory")
            
            with open(file_path, "rb") as f:
                pdf_content = f.read()

        elif request.file_url:
            async with httpx.AsyncClient() as http_client:
                resp = await http_client.get(request.file_url)
                resp.raise_for_status()
                pdf_content = resp.content
        else:
            raise HTTPException(status_code=400, detail="Must provide either 'file_url' or 'local_filename'")

        # 2. Upload do arquivo para a OpenAI com propósito 'assistants'
        client = get_client()
        print("Uploading file to OpenAI...")
        file_obj = await client.files.create(
            file=("contrato.pdf", pdf_content),
            purpose="assistants"
        )
        print(f"File uploaded. ID: {file_obj.id}")

        # 3. Call OpenAI Responses API (GPT-5-Nano)
        print("Calling OpenAI Responses API...")
        response = await client.responses.create(
            model="gpt-5-nano-2025-08-07",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": USER_PROMPT},
                        {"type": "input_file", "file_id": file_obj.id}
                    ],
                },
            ],
            text={"format": {"type": "json_object"}}
        )

        # Busca robusta do conteúdo na Responses API
        response_text = None
        if hasattr(response, 'choices') and response.choices:
            response_text = response.choices[0].message.content
        elif hasattr(response, 'output') and response.output:
            for item in response.output:
                if getattr(item, 'type', None) == 'message' and hasattr(item, 'content'):
                    for part in item.content:
                        if getattr(part, 'type', None) == 'output_text':
                            response_text = part.text
                            break
                if response_text: break

        if not response_text:
            response_text = str(response)

        data = json.loads(response_text)

        # 4. Transform to legacy envelope format expected by client
        legacy_prediction = transform_to_legacy(data)
        legacy_output = {
            "Result": [
                {
                    "Prediction": legacy_prediction
                }
            ]
        }
        
        # Cleanup
        try:
            await client.files.delete(file_obj.id)
        except Exception as e:
            print(f"Error deleting file: {str(e)}")

        # 5. Usage and Logging
        usage_data = getattr(response, 'usage', None)
        input_tokens = getattr(usage_data, 'input_tokens', 0) if usage_data else 0
        output_tokens = getattr(usage_data, 'completion_tokens', 0) if usage_data else 0
        
        # Calculate cost for gpt-5-nano
        cost_input = (input_tokens / 1_000_000) * 0.05
        cost_output = (output_tokens / 1_000_000) * 0.40
        total_cost = cost_input + cost_output

        usage_dict = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost": total_cost,
            "model": "gpt-5-nano-2025-08-07"
        }

        # Log to MongoDB
        processing_time = time.time() - start_time
        await log_to_mongo(
            endpoint="/analyze-contract-file",
            request_data={"file_url": request.file_url, "local_filename": request.local_filename},
            response_data=legacy_output,
            usage=usage_dict,
            processing_time=processing_time
        )
            
        return legacy_output

    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to download file: {str(e)}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse JSON from AI response")
    except Exception as e:
        processing_time = time.time() - start_time
        await log_to_mongo(
            endpoint="/analyze-contract-file",
            request_data={"file_url": request.file_url, "local_filename": request.local_filename},
            response_data=None,
            status_code=500,
            error=str(e),
            processing_time=processing_time
        )
        print(f"Contract analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def transform_to_legacy(data: dict) -> list:
    """Transforms the OpenAI JSON to the legacy list format."""
    
    def to_sim_nao(val):
        return "SIM" if val else "NÃO"

    output = []

    # 1. Numero_Contrato
    contract_num = data.get("contract_number", {}) or {}
    output.append({
        "Label": "Numero_Contrato",
        "OCR_Text": contract_num.get("value") or "",
        "Score": "1" if contract_num.get("found") else "0"
    })

    # Helpers
    itau_logo = data.get("itau_logo_present")
    clauses = data.get("contract_clauses_present")
    
    # 2. Recebido
    # Regra: contract_number.found AND itau_logo_present AND contract_clauses_present
    is_received = (contract_num.get("found") and itau_logo and clauses)
    output.append({
        "Label": "Recebido",
        "OCR_Text": to_sim_nao(is_received),
        "Score": "1"
    })

    # 3. Legivel
    output.append({
        "Label": "Legivel",
        "OCR_Text": to_sim_nao(data.get("contract_legible")),
        "Score": "1"
    })

    # 4. Consta_Clausula_Do_Seguro
    ins_clause = data.get("insurance_clause", {}) or {}
    output.append({
        "Label": "Consta_Clausula_Do_Seguro",
        "OCR_Text": to_sim_nao(ins_clause.get("exists")),
        "Score": "1"
    })

    # 5. Matricula_Recebida
    reg = data.get("registration", {}) or {}
    output.append({
        "Label": "Matricula_Recebida",
        "OCR_Text": to_sim_nao(reg.get("received")),
        "Score": "1"
    })

    # 6. Matricula_Legivel
    output.append({
        "Label": "Matricula_Legivel",
        "OCR_Text": to_sim_nao(reg.get("legible")),
        "Score": "1"
    })

    # 7. Correspondente_Imovel_Do_Contrato
    # Regra: summary_registration_number == registration.number
    summary_reg_num = data.get("summary_registration_number")
    reg_num = reg.get("number")
    # Loose comparison
    match_imovel = False
    if summary_reg_num and reg_num and (summary_reg_num.strip() == reg_num.strip()):
        match_imovel = True
    
    output.append({
        "Label": "Correspondente_Imovel_Do_Contrato",
        "OCR_Text": to_sim_nao(match_imovel),
        "Score": "1"
    })

    # 8. Averbacao_Do_Contrato
    # Regra: verificar se contem "itau"
    verbacao = data.get("verbacao_creditor") or ""
    is_itau_verb = "itau" in verbacao.lower()
    output.append({
        "Label": "Averbacao_Do_Contrato",
        "OCR_Text": to_sim_nao(is_itau_verb),
        "Score": "1"
    })

    # 9. Contrato_Assinado
    # Regra: bank AND intermediary AND financed
    sigs = data.get("signatures", {}) or {}
    # Note: Logic says "bank AND intermediary AND financed", but usually intermediary is optional? 
    # Sticking to requested logic:
    is_signed = (sigs.get("bank") and sigs.get("intermediary") and sigs.get("financed"))
    output.append({
        "Label": "Contrato_Assinado",
        "OCR_Text": to_sim_nao(is_signed),
        "Score": "1"
    })

    return output
