import base64
import json
import os
import hashlib
import logging
import time
import asyncio
from typing import List
from openai import AsyncOpenAI
from app.models.schemas import NFSeData
from dotenv import load_dotenv

load_dotenv()
_client = None

def get_client():
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

logger = logging.getLogger(__name__)

# Simple in-memory cache
extraction_cache = {}

# Controle de Concorrência Global: Limita o número de tarefas pesadas (IA + Imagem) simultâneas no servidor.
# Isso evita picos de CPU/RAM que derrubariam o serviço sob alta carga.
# Definimos como 15 para atender seu requisito, mas o servidor precisa ter recursos suficientes.
MAX_CONCURRENT_EXTRACTIONS = 15
heavy_task_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXTRACTIONS)

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

async def extract_data_from_pdf(pdf_content: bytes) -> NFSeData:
    start_time = time.time()
    pdf_hash = get_pdf_hash(pdf_content)
    
    if pdf_hash in extraction_cache:
        logger.info(f"Cache HIT para PDF (hash: {pdf_hash})")
        return extraction_cache[pdf_hash]

    # Usando o semáforo para controlar a carga pesada simultânea no servidor
    async with heavy_task_semaphore:
        logger.debug(f"Cache MISS para PDF (hash: {pdf_hash}). Preparando entrada nativa de documento...")

        # 1. Upload do arquivo para a OpenAI com propósito 'assistants'
        logger.info(f"Fazendo upload do PDF para OpenAI (purpuse='assistants')...")
        client = get_client()
        
        # O modelo Responses API exige que o arquivo seja pré-carregado
        file_obj = await client.files.create(
            file=("nota_fiscal.pdf", pdf_content),
            purpose="assistants"
        )
        logger.info(f"Arquivo carregado com ID: {file_obj.id}")

        # 2. Montar o prompt e chamar OpenAI Responses API
        logger.info(f"Chamando API de Responses com PDF (Modelo: gpt-5-nano-2025-08-07)...")
        ai_start = time.time()
        
        # Gerar JSON Schema a partir do modelo Pydantic para garantir extração perfeita
        json_schema = NFSeData.model_json_schema()
        json_schema = add_additional_properties_false(json_schema)
        
        system_prompt = f"""
        Você é um assistente especializado em extração de dados de Notas Fiscais de Serviço Eletrônicas (NFS-e) brasileiras, capaz de interpretar layouts variados de diferentes prefeituras (padrão ABRASF, Ginfes, Betha, DSf, etc.).
        Sua tarefa é analisar o documento PDF completo e extrair os dados para o schema JSON fornecido com extrema precisão técnica.

        DIRETRIZES TÉCNICAS DE EXTRAÇÃO POR CAMPO (NÃO ALTERE OS NOMES DAS CHAVES DO JSON):

        1. GRUPO IDENTIFICAÇÃO DA NOTA:
           - numero_nota: Número sequencial da NFS-e. Geralmente destacado no topo (ex: "Número da Nota", "Nº", "Nota Fiscal Nº"). Diferencie do número do RPS. Apenas dígitos numéricos.
           - codigo_verificacao: Campo Crítico. Pode ser denominado como "Código de Verificação", "Chave de Acesso", "Código de Acesso" ou "Código de Autenticidade". Trata-se de uma sequência alfanumérica única (case-sensitive) usada para validar a autenticidade da nota. Copie exatamente como impresso, preservando letras maiúsculas/minúsculas e números.
           - data_emissao: Data de competência/emissão da nota. Formato estrito: DD/MM/YYYY. Ignore a hora de emissão. Exemplo: Se "25/10/2023 14:30", extraia "25/10/2023".
           - outras_informacoes: Extraia prioritariamente o número e série do RPS (Recibo Provisório de Serviços) se presente (ex: "RPS Nº 123 Série A"). Caso não haja RPS, capture outras observações relevantes do campo "Outras Informações".

        2. GRUPO PRESTADOR E TOMADOR (ENTIDADES):
           - prestador_cnpj: CNPJ da empresa que emitiu a nota (Prestador). Busque no quadro "Prestador de Serviços". Remova pontuação (pontos, barras, traço). Formato final: 14 dígitos numéricos.
           - tomador_cnpj: CNPJ ou CPF da empresa/pessoa que contratou o serviço (Tomador/Destinatário). Busque no quadro "Tomador de Serviços". Remova pontuação. Se vazio/não identificado, retorne null.

        3. GRUPO DETALHES DO SERVIÇO:
           - codigo_servico: Código do item da Lista de Serviços (Lei Complementar 116/2003). Geralmente no formato "X.XX" ou "XX.XX" (ex: "14.01", "17.05"). Pode estar junto à descrição do serviço.
           - discriminacao_servicos: Descrição completa do serviço prestado. Capture o texto integral do corpo da nota, preservando quebras de linha se possível ou unificando com espaços.
           - municipio_prestacao: Nome do município onde o serviço foi efetivamente prestado (Local da Prestação). Pode diferir do município do prestador.

        4. GRUPO VALORES E TRIBUTAÇÃO (PRECISÃO DECIMAL OBRIGATÓRIA):
           * Regra Geral: Converta vírgula decimal para ponto (ex: "1.250,00" -> 1250.00). Se o campo existir mas estiver zerado ("0,00", "-", "Isento"), retorne 0.00.
           
           - valor_total: Valor Bruto da Nota ou Valor Total dos Serviços.
           - valor_iss: Valor monetário do Imposto Sobre Serviços (ISS).
           - aliquota_iss: Percentual do ISS aplicado (ex: 5.0, 2.0). Se estiver em %, converta para decimal simples (ex: "5%" -> 5.00).
           
           - iss_retido: "Sim" ou "Não".
           
           REGRAS OBRIGATÓRIAS PARA ISS RETIDO (SIGA A HIERARQUIA):
           
           ANALISE O DOCUMENTO BUSCANDO POR ESTES TERMOS EXATOS (Case Insensitive):

           GRUPO 1 - RETENÇÃO CONFIRMADA (iss_retido = "Sim"):
           - "ISS RETIDO NA FONTE"
           - "NATUREZA DA OPERACAO: TRIBUTCAO FORA DO MUNICIPIO"
           - "ISS RETIDO PELO TOMADOR"
           - "RECOLHIMENTO: ISS RETIDO NA FONTE PELO TOMADOR"
           - "SUBSTITUTO TRIBUTARIO: SIM"
           - "TIPO DE TRIBUTACAO: FORA DO MUNICIPIO"
           - "TRIBUTADO FORA DO MUNICIPIO"
           - "RESPONSÁVEL PELO RECOLHIMENTO: TOMADOR"
           - "O ISS DESTA NFSE É DEVIDO FORA DO MUNICIPIO"
           - "O ISS DESTA NFSE SERÁ RETIDO PELO TOMADOR DE SERVIÇO"
           - "SITUACAO DE TRIBUTACAO RETIDO NO TOMADOR"
           - "SIT. TRIB = TIST" ou "SIT. TRIB = TIRF"

           GRUPO 2 - SEM RETENÇÃO (iss_retido = "Não"):
           - "NATUREZA DA OPERAÇÃO TRIBUTAÇÃO NO MUNICÍPIO"
           - "SUBSTITUTO TRIBUTARIO: NÃO"
           - "RECOLHIMENTO : SEM RETENÇÃO"
           - "RESPONSÁVEL RECOLHIMENTO: PRESTADOR"
           - "NA AUSÊNCIA DE PROVAS EM CONTRÁRIO, NÃO RETEM"
           - "ISS ISENÇÃO"
           - "NÃO SUJEITO A RETENÇÃO NA FONTE"
           - "ISS SEM RETENÇÃO"
           - "SIT. TRIB = TI"
           - "SITUACAO: NÃO TRIBUTADA"

           REGRA DE CONFLITO:
           Se houver termos conflitantes, dê preferência aos termos do GRUPO 1.
           Se não encontrar nenhum termo específico, assuma "Não".
           - valor_pis: Valor do PIS (Retenção Federal).
           - valor_cofins: Valor da COFINS (Retenção Federal).
           - valor_inss: Valor do INSS (Retenção Federal).
           - valor_ir: Valor do Imposto de Renda (IRRF).
           - valor_csll: Valor da Contribuição Social (CSLL).
           
        5. NOVOS CAMPOS ESPECÍFICOS:
           - ibs: Indicador de Situação (IBS). Campo numérico. Se encontrado, extraia com 2 casas decimais.
           - cbs: Código de Base de Substituição (CBS). Campo de texto.
           - valor_liquido: Valor Líquido da Nota. Se não estiver explícito, calcule: Valor Total - Retenções.
           - base_calculo: Base de Cálculo do ISS. Se não estiver explícito, geralmente é igual ao Valor dos Serviços.

        Você DEVE seguir rigorosamente este schema JSON para a saída:
        {json.dumps(json_schema, indent=2)}
        
        Instruções de Validação Final:
        1. Campos não encontrados devem ser null.
        2. Dê prioridade máxima para encontrar o CÓDIGO DE VERIFICAÇÃO / CHAVE DE ACESSO correto, independente da nomenclatura usada pela prefeitura.
        3. Evite confundir CNPJ do Tomador com CNPJ do Prestador (verifique os rótulos dos quadros).
        4. Analise todas as páginas do documento se houver mais de uma.
        """

        user_prompt = "Analise este PDF de NFS-e e extraia os dados conforme o schema, focando na precisão do Número e Código de Verificação."

        # Configurações para entrada nativa via Responses API
        response_params = {
            "model": "gpt-5-nano-2025-08-07",
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": user_prompt},
                        {"type": "input_file", "file_id": file_obj.id}
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "nfse_extraction",
                        "schema": json_schema,
                        "strict": True
                    }
                }
            }
        }

        try:
            # Chamada com o modelo gpt-5-nano via Responses API (Beta)
            response = await client.responses.create(
                **response_params
            )
        except Exception as e:
            logger.warning(f"Erro na primeira tentativa com gpt-5-nano, tentando novamente... Erro: {str(e)}")
            # Tentativa de reprocessamento
            response = await client.responses.create(
                **response_params
            )
        finally:
            # Limpar o arquivo após o uso
            try:
                await client.files.delete(file_obj.id)
            except Exception as e:
                logger.error(f"Erro ao deletar arquivo {file_obj.id}: {str(e)}")

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
        # DEBUG: Imprimir o objeto de resposta completo para inspeção
        logger.info(f"DEBUG RAW RESPONSE: {response}")

        # Busca robusta pelo conteúdo de texto no objeto de resposta multimodal
        try:
            content = None
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
            elif hasattr(response, 'output') and response.output:
                # Na Responses API, o output é uma lista. Procuramos o item do tipo 'message'
                for item in response.output:
                    if getattr(item, 'type', None) == 'message' and hasattr(item, 'content'):
                        for part in item.content:
                            if getattr(part, 'type', None) == 'output_text':
                                content = part.text
                                break
                    if content: break
                
                # Fallback: Se não achou 'message', tenta o primeiro item que tenha conteúdo (caso de layouts diferentes)
                if not content and len(response.output) > 0:
                    for item in response.output:
                        if hasattr(item, 'content') and item.content:
                            content = getattr(item.content[0], 'text', None)
                            if content: break
            
            if not content:
                # Fallback final: tenta converter o objeto para string/dict
                content = str(response)
        except Exception as e:
            logger.error(f"Erro ao acessar conteúdo da resposta: {str(e)}")
            content = str(response)

        logger.debug(f"Conteúdo bruto para parse: {content}")
        
        try:
            data_dict = json.loads(content)
            result = NFSeData(**data_dict)
            
            # Anexar metadados de uso
            result.usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_cost": total_cost,
                "model": "gpt-5-nano-2025-08-07"
            }
            
            # extraction_cache[pdf_hash] = result
            
            total_time = time.time() - start_time
            logger.info(f"Processamento total finalizado com sucesso em {{total_time:.2f}}s")
            return result
        except Exception as e:
            logger.error(f"Erro ao parsear resposta da IA ou validar schema: {{str(e)}}", exc_info=True)
            logger.error(f"Conteúdo que falhou: {{content}}")
            raise ValueError(f"Erro ao processar dados extraídos: {{str(e)}}")
