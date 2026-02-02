from fastapi import FastAPI, HTTPException, Request
from app.services.openai_service import extract_data_from_pdf
from app.models.schemas import NFSeData, PDFRequest, LegacyRequest, LegacyResponse, LegacyResult, LegacyPredictionItem
from app.utils.logging_config import setup_logging, request_id_ctx
from dotenv import load_dotenv
import uvicorn
import logging
import base64
import time
import uuid

# Inicializar Logs
setup_logging()
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

app = FastAPI(
    title="API de Extração de NFS-e com Monitoramento",
    description="API para extração de dados de NFS-e com logs detalhados e métricas.",
    version="1.2.0"
)

# Middleware para Request ID e Performance
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request_id_ctx.set(request_id)
    
    start_time = time.time()
    
    logger.info(f"Início da requisição: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Alerta se demorar mais de 30 segundos
        if process_time > 30:
            logger.warning(f"ALERTA: Tempo de processamento crítico: {process_time:.2f}s")
        
        logger.info(f"Fim da requisição: Status {response.status_code} | Tempo: {process_time:.2f}s")
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Falha na requisição após {process_time:.2f}s: {str(e)}", exc_info=True)
        raise

@app.post("/extract", response_model=NFSeData)
async def extract_nfse(request: PDFRequest):
    logger.debug("Validando entrada Base64...")
    
    try:
        # Decodificar Base64
        try:
            pdf_content = base64.b64decode(request.pdf_base64)
            file_size_kb = len(pdf_content) / 1024
            logger.info(f"Arquivo recebido: {file_size_kb:.2f} KB")
            
            # Validação básica de PDF (Header %PDF-)
            if not pdf_content.startswith(b"%PDF-"):
                logger.error("Arquivo enviado não é um PDF válido (header ausente).")
                raise HTTPException(status_code=400, detail="O arquivo enviado não é um PDF válido.")
                
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            logger.error(f"Erro na decodificação Base64: {str(e)}")
            raise HTTPException(status_code=400, detail="String Base64 inválida.")
            
        # Iniciar extração
        logger.info("Iniciando extração inteligente de PDF direto...")
        data = await extract_data_from_pdf(pdf_content)
        
        logger.info("Extração concluída e dados validados.")
        return data
        
    except HTTPException as he:
        raise he
    except Exception as e:
        # Erro genérico capturado pelo middleware, mas logamos detalhes específicos aqui também
        logger.error(f"Erro durante o fluxo de extração: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno no processamento: {str(e)}")

@app.post("/api/extractData2", response_model=LegacyResponse)
async def extract_nfse_legacy(request: LegacyRequest):
    logger.debug("Recebendo requisição legado (Base64File)...")
    
    try:
        # Decodificar Base64
        try:
            pdf_content = base64.b64decode(request.Base64File)
            
            # Validação básica de PDF (Header %PDF-)
            if not pdf_content.startswith(b"%PDF-"):
                logger.error("Arquivo enviado não é um PDF válido (header ausente).")
                raise HTTPException(status_code=400, detail="O arquivo enviado não é um PDF válido.")
                
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            logger.error(f"Erro na decodificação Base64: {str(e)}")
            raise HTTPException(status_code=400, detail="String Base64 inválida.")
            
        # Iniciar extração
        logger.info("Iniciando extração legado...")
        data = await extract_data_from_pdf(pdf_content)
        
        # Mapeamento para LegacyResponse
        predictions = []
        
        def add_pred(label, value, default_value=""):
            final_value = str(value) if value is not None else default_value
            predictions.append(LegacyPredictionItem(Label=label, OCR_Text=final_value, Score="1.0"))
        
        add_pred("CNPJ_Prest", data.prestador_cnpj)
        add_pred("CNPJ_Tom", data.tomador_cnpj)
        add_pred("Numero", data.numero_nota)
        add_pred("RPS", data.outras_informacoes, "0") # Tentativa de mapear algo, ou deixar 0
        add_pred("Codigo_Servico", data.codigo_servico)
        add_pred("Data", data.data_emissao)
        add_pred("Valor_Total", data.valor_total, "0.00")
        add_pred("Aliquota", data.aliquota_iss, "0.00")
        add_pred("Valor_ISS", data.valor_iss, "0.00")
        add_pred("PIS", data.valor_pis, "0.00")
        add_pred("COFINS", data.valor_cofins, "0.00")
        add_pred("INSS", data.valor_inss, "0.00")
        add_pred("IRRF", data.valor_ir, "0.00")
        add_pred("CSLL", data.valor_csll, "0.00")
        add_pred("Discriminacao", data.discriminacao_servicos)
        add_pred("Chave", data.codigo_verificacao)
        add_pred("Municipio_Prestacao", data.municipio_prestacao)
        
        logger.info(f"Retornando resposta legado com {len(predictions)} campos.")
        return LegacyResponse(Result=[LegacyResult(Prediction=predictions)])
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro legado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": time.time()}

if __name__ == "__main__":
    # Nota: No ambiente real, use uvicorn via CLI ou python -m
    uvicorn.run(app, host="0.0.0.0", port=8000)
