import base64
import json
import os
import hashlib
import logging
import time
import asyncio
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance
from io import BytesIO
from typing import List
from openai import AsyncOpenAI
from app.models.schemas import NFSeData
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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

def process_pdf_to_enhanced_image(pdf_content: bytes) -> str:
    """Converte a primeira página do PDF em uma imagem de alta resolução e aplica melhorias para OCR."""
    try:
        conv_start = time.time()
        # 1. Abrir PDF com alta resolução (DPI 216+)
        # Reduzimos o zoom de 4.0 para 3.0 para economizar memória e CPU em alta concorrência,
        # mantendo precisão suficiente para OCR de notas fiscais.
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        if doc.page_count == 0:
            raise ValueError("O PDF não contém páginas.")
        
        page = doc.load_page(0)
        
        zoom = 3.0 
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # 2. Carregar no Pillow para processamento de imagem
        img = Image.open(BytesIO(pix.tobytes("png")))
        
        # Converter para escala de cinza
        img = img.convert("L")
        
        # Aumentar o contraste (otimizado)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5) # Reduzido levemente para evitar artefatos
        
        # 3. Converter de volta para Base64 (JPEG com compressão balanceada)
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=85, optimize=True)
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        doc.close()
        conv_time = time.time() - conv_start
        logger.info(f"Conversão PDF->Imagem concluída em {conv_time:.2f}s (Zoom: {zoom})")
        return img_base64
        
    except Exception as e:
        logger.error(f"Erro no processamento de imagem do PDF: {str(e)}", exc_info=True)
        raise ValueError(f"Falha ao processar imagem para OCR: {str(e)}")

async def extract_data_from_pdf(pdf_content: bytes) -> NFSeData:
    start_time = time.time()
    pdf_hash = get_pdf_hash(pdf_content)
    
    if pdf_hash in extraction_cache:
        logger.info(f"Cache HIT para PDF (hash: {pdf_hash})")
        return extraction_cache[pdf_hash]

    # Usando o semáforo para controlar a carga pesada simultânea no servidor
    async with heavy_task_semaphore:
        logger.debug(f"Cache MISS para PDF (hash: {pdf_hash}). Processando imagem aprimorada...")

        # 1. Converter PDF para Imagem Aprimorada
        image_base64 = process_pdf_to_enhanced_image(pdf_content)

        # 2. Montar o prompt e chamar OpenAI
        logger.info(f"Chamando API da OpenAI com Imagem Aprimorada (Modelo: gpt-5-nano-2025-08-07)... ")
        ai_start = time.time()
        
        # Gerar JSON Schema a partir do modelo Pydantic para garantir extração perfeita
        json_schema = NFSeData.model_json_schema()
        json_schema = add_additional_properties_false(json_schema)
        
        system_prompt = f"""
        Você é um assistente especializado em extração de dados de Notas Fiscais de Serviço Eletrônicas (NFS-e) brasileiras, capaz de interpretar layouts variados de diferentes prefeituras (padrão ABRASF, Ginfes, Betha, DSf, etc.).
        Sua tarefa é analisar a imagem e extrair os dados para o schema JSON fornecido com extrema precisão técnica.

        DIRETRIZES TÉCNICAS DE EXTRAÇÃO POR CAMPO (NÃO ALTERE OS NOMES DAS CHAVES DO JSON):

        1. GRUPO IDENTIFICAÇÃO DA NOTA:
           - numero_nota: Número sequencial da NFS-e. Geralmente destacado no topo (ex: "Número da Nota", "Nº", "Nota Fiscal Nº"). Diferencie do número do RPS. Apenas dígitos numéricos.
           - codigo_verificacao: Campo Crítico. Pode ser denominado como "Código de Verificação", "Chave de Acesso", "Código de Acesso" ou "Código de Autenticidade". Trata-se de uma sequência alfanumérica única (case-sensitive) usada para validar a autenticidade da nota. Copie exatamente como impresso, preservando letras maiúsculas/minúsculas e números.
           - data_emissao: Data de competência/emissão da nota. Formato estrito: DD/MM/YYYY. Ignore a hora de emissão. Exemplo: Se "25/10/2023 14:30", extraia "25/10/2023".
           - outras_informacoes: Extraia prioritariamente o número e série do RPS (Recibo Provisório de Serviços) se presente (ex: "RPS Nº 123 Série A"). Caso não haja RPS, capture outras observações relevantes do campo "Outras Informações".

        2. GRUPO PRESTADOR E TOMADOR (ENTIDADES):
           - prestador_cnpj: CNPJ da empresa que emitiu a nota (Prestador de Serviços). **ATENÇÃO: NÃO extraia o CNPJ da Prefeitura ou do órgão emissor, que frequentemente fica no cabeçalho ou topo da página.** Busque EXCLUSIVAMENTE dentro do quadro/seção destinado ao "Prestador de Serviços" (quem prestou o serviço). Remova pontuação (pontos, barras, traço). Formato final: 14 dígitos numéricos.
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
        {{json.dumps(json_schema, indent=2)}}
        
        Instruções de Validação Final:
        1. Campos não encontrados devem ser null.
        2. Dê prioridade máxima para encontrar o CÓDIGO DE VERIFICAÇÃO / CHAVE DE ACESSO correto, independente da nomenclatura usada pela prefeitura.
        3. Evite confundir CNPJ do Tomador com CNPJ do Prestador (verifique os rótulos dos quadros).
        4. Ignore carimbos ou assinaturas que sobreponham o texto.
        5. IMPORTANTE: O CNPJ do Prestador nunca é o mesmo da Prefeitura Municipal.
        """

        user_prompt = "Analise esta imagem de NFS-e e extraia os dados conforme o schema, focando na precisão do Número e Código de Verificação."

        # Configurações comuns
        model_params = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "high"
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
            response = await client.chat.completions.create(
                model="gpt-5-nano-2025-08-07",
                **model_params
            )
        except Exception as e:
            logger.warning(f"Erro na primeira tentativa com gpt-5-nano, tentando novamente... Erro: {str(e)}")
            # Tentativa de reprocessamento com o mesmo modelo gpt-5-nano
            response = await client.chat.completions.create(
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
