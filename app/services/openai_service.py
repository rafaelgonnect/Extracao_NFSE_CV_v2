import base64
import json
import os
import hashlib
import logging
import time
from typing import List
from openai import OpenAI
from app.models.schemas import NFSeData
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger = logging.getLogger(__name__)

# Simple in-memory cache
extraction_cache = {}

def add_additional_properties_false(schema):
    """Recursivamente adiciona additionalProperties: false e torna todos os campos obrigatórios, como exigido pela OpenAI em modo strict."""
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            schema["additionalProperties"] = False
            # Em modo strict, todos os campos devem estar no array 'required'
            if "properties" in schema:
                schema["required"] = list(schema["properties"].keys())
        for key, value in schema.items():
            add_additional_properties_false(value)
    elif isinstance(schema, list):
        for item in schema:
            add_additional_properties_false(item)
    return schema

def get_pdf_hash(pdf_content: bytes) -> str:
    return hashlib.md5(pdf_content).hexdigest()

def extract_data_from_pdf(pdf_content: bytes) -> NFSeData:
    start_time = time.time()
    pdf_hash = get_pdf_hash(pdf_content)
    
    if pdf_hash in extraction_cache:
        logger.info(f"Cache HIT para PDF (hash: {pdf_hash})")
        return extraction_cache[pdf_hash]

    logger.debug(f"Cache MISS para PDF (hash: {pdf_hash}). Enviando PDF direto para o modelo...")

    # 1. Preparar o PDF em Base64 para envio direto
    try:
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    except Exception as e:
        logger.error(f"Erro ao codificar PDF para Base64: {str(e)}", exc_info=True)
        raise ValueError(f"Erro ao processar PDF: {str(e)}")

    # 2. Montar o prompt e chamar OpenAI
    logger.info(f"Chamando API da OpenAI com PDF direto (Modelo: gpt-5-nano-2025-08-07)...")
    ai_start = time.time()
    
    # Gerar JSON Schema a partir do modelo Pydantic para garantir extração perfeita
    json_schema = NFSeData.model_json_schema()
    json_schema = add_additional_properties_false(json_schema)
    
    system_prompt = f"""
    Você é um assistente especializado em extração de dados de Notas Fiscais de Serviço Eletrônicas (NFS-e) brasileiras.
    Sua tarefa é analisar o documento PDF fornecido e extrair TODOS os dados estruturados possíveis.
    
    Você DEVE seguir rigorosamente este schema JSON para a saída:
    {json.dumps(json_schema, indent=2)}
    
    Instruções Adicionais:
    1. Identifique os dados do Prestador e Tomador (CNPJ, Razão Social, Endereço).
    2. Extraia valores monetários como números decimais (float).
    3. Se um campo não for encontrado, use null.
    4. Para datas, utilize o formato original encontrado ou YYYY-MM-DD.
    5. A discriminação dos serviços deve ser o texto completo descrevendo o serviço.
    """

    user_prompt = "Extraia os dados desta NFS-e conforme o schema fornecido."

    # Configurações comuns
    model_params = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "file",
                        "file": {
                            "filename": "nfse.pdf",
                            "file_data": f"data:application/pdf;base64,{pdf_base64}"
                        }
                    },
                ],
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "nfse_extraction",
                "schema": json_schema,
                "strict": True
            }
        }
    }

    try:
        # Chamada com o modelo gpt-5-nano
        response = client.chat.completions.create(
            model="gpt-5-nano-2025-08-07",
            **model_params
        )
    except Exception as e:
        logger.warning(f"Erro na primeira tentativa com gpt-5-nano, tentando novamente... Erro: {str(e)}")
        # Tentativa de reprocessamento com o mesmo modelo gpt-5-nano
        response = client.chat.completions.create(
            model="gpt-5-nano-2025-08-07",
            **model_params
        )

    ai_time = time.time() - ai_start
    logger.info(f"Resposta da OpenAI recebida em {ai_time:.2f}s")

    # Calcular custos (Preços fornecidos: $0,05/1M input, $0,40/1M output)
    usage = response.usage
    input_tokens = usage.prompt_tokens
    output_tokens = usage.completion_tokens
    
    cost_input = (input_tokens / 1_000_000) * 0.05
    cost_output = (output_tokens / 1_000_000) * 0.40
    total_cost = cost_input + cost_output

    logger.info(
        f"Uso de Tokens: Input={input_tokens} | Output={output_tokens} | "
        f"Custo Estimado: ${total_cost:.6f}"
    )

    # 4. Parsear e Cache
    content = response.choices[0].message.content
    logger.debug(f"Conteúdo bruto recebido da IA: {content}")
    
    try:
        data_dict = json.loads(content)
        result = NFSeData(**data_dict)
        extraction_cache[pdf_hash] = result
        
        total_time = time.time() - start_time
        logger.info(f"Processamento total finalizado com sucesso em {total_time:.2f}s")
        return result
    except Exception as e:
        logger.error(f"Erro ao parsear resposta da IA ou validar schema: {str(e)}", exc_info=True)
        logger.error(f"Conteúdo que falhou: {content}")
        raise ValueError(f"Erro ao processar dados extraídos: {str(e)}")
