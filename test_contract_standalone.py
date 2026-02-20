import os
import json
import base64
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """Voce e um analista senior de contratos imobiliarios do Banco Itau.
Seu papel e analisar o PDF completo do contrato e devolver um unico resultado consolidado.
Nao invente informacoes. Responda apenas em JSON valido conforme o esquema definido."""

USER_PROMPT = """Analise o PDF completo e consolide os campos abaixo.
... (truncado para brevidade no teste) ...
Retorne exatamente este JSON:
{
  "contract_number": { "value": "string", "found": true, "legible": true },
  "itau_logo_present": true,
  "contract_clauses_present": true,
  "contract_legible": true,
  "insurance_clause": { "exists": true, "clause_number": 1 },
  "registration": { "received": true, "legible": true, "number": "123" },
  "summary_registration_number": "123",
  "verbacao_creditor": "itau",
  "signatures": { "bank": true, "intermediary": true, "financed": true, "previous_bank": true },
  "portability_case": false,
  "notes": "teste",
  "justificativas_criticas": {}
}"""

async def test_contract():
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    file_path = os.path.join(os.getcwd(), "exemplos pdf", "10144331007.pdf")
    
    with open(file_path, "rb") as f:
        pdf_content = f.read()
    
    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
    
    print("Calling OpenAI...")
    response = await client.chat.completions.create(
        model="gpt-5-nano-2025-08-07",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {
                        "type": "input_file",
                        "input_file": {
                            "data": pdf_base64,
                            "format": "pdf"
                        }
                    }
                ]
            }
        ],
        response_format={"type": "json_object"}
    )
    
    print("Response received:")
    print(response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(test_contract())
