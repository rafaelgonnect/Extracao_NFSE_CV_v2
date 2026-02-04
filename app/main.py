from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from app.services.openai_service import extract_data_from_pdf
from app.models.schemas import NFSeData, PDFRequest, LegacyRequest, LegacyResponse, LegacyResult, LegacyPredictionItem
from app.utils.logging_config import setup_logging, request_id_ctx
from app.database import db, get_logs_collection
from dotenv import load_dotenv
import uvicorn
import logging
import base64
import time
import uuid
import secrets
import random
from datetime import datetime, timedelta

# Inicializar Logs

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

# Segurança
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "admin@gonnect@123")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais incorretas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.on_event("startup")
async def startup_db_client():
    db.connect()

@app.on_event("shutdown")
async def shutdown_db_client():
    db.close()

async def log_to_mongo(endpoint: str, request_data: dict, response_data: dict, usage: dict = None, status_code: int = 200, error: str = None):
    try:
        logs_collection = await get_logs_collection()
        
        # Cálculo de Custo com Markup (Entre $0.010 e $0.013)
        markup_fee = random.uniform(0.010, 0.013)
        provider_cost = usage.get("total_cost", 0.0) if usage else 0.0
        final_price = provider_cost + markup_fee if usage else 0.0
        
        log_entry = {
            "timestamp": datetime.utcnow(),
            "request_id": request_id_ctx.get(),
            "endpoint": endpoint,
            "status_code": status_code,
            "model": usage.get("model") if usage else "unknown",
            "input_tokens": usage.get("input_tokens", 0) if usage else 0,
            "output_tokens": usage.get("output_tokens", 0) if usage else 0,
            "provider_cost": provider_cost,
            "markup_fee": markup_fee,
            "final_price": final_price,
            "error": error,
            # Evitar salvar Base64 muito grande no log se não for estritamente necessário para debug
            # "request_payload": str(request_data)[:500] + "..." if request_data else None, 
            "response_payload": response_data
        }
        await logs_collection.insert_one(log_entry)
    except Exception as e:
        logger.error(f"Erro ao salvar log no MongoDB: {str(e)}")

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
    logger.info(f"Processando documento com versão da API: {app.version}")
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
        logger.info(f"Resposta da API: {data.model_dump_json()}")
        
        # Logar no MongoDB
        await log_to_mongo(
            endpoint="/extract",
            request_data={"pdf_base64_len": len(request.pdf_base64)},
            response_data=data.model_dump(),
            usage=data.usage
        )
        
        return data
        
    except HTTPException as he:
        await log_to_mongo(endpoint="/extract", request_data=None, response_data=None, status_code=he.status_code, error=he.detail)
        raise he
    except Exception as e:
        await log_to_mongo(endpoint="/extract", request_data=None, response_data=None, status_code=500, error=str(e))
        # Erro genérico capturado pelo middleware, mas logamos detalhes específicos aqui também
        logger.error(f"Erro durante o fluxo de extração: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno no processamento: {str(e)}")

@app.post("/api/extractData2", response_model=LegacyResponse)
async def extract_nfse_legacy(request: LegacyRequest):
    logger.info(f"Processando documento com versão da API: {app.version}")
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
            final_value = default_value
            if value is not None:
                # Se for float (campos monetários), formatar com 2 casas decimais
                if isinstance(value, float):
                    final_value = f"{value:.2f}"
                else:
                    final_value = str(value)
            
            predictions.append(LegacyPredictionItem(Label=label, OCR_Text=final_value, Score="1.0"))
        
        add_pred("CNPJ_Prest", data.prestador_cnpj)
        add_pred("CNPJ_Tom", data.tomador_cnpj)
        add_pred("Numero", data.numero_nota)
        add_pred("RPS", data.outras_informacoes, "0") # Tentativa de mapear algo, ou deixar 0
        add_pred("Codigo_Servico", data.codigo_servico)
        
        # Garantir formatação de data DD/MM/YYYY
        data_formatada = data.data_emissao
        if data_formatada:
             # Remover horário se houver (separador T ou espaço)
             if "T" in data_formatada:
                 data_formatada = data_formatada.split("T")[0]
             elif " " in data_formatada:
                 data_formatada = data_formatada.split(" ")[0]
             
             # Se estiver em YYYY-MM-DD, converter para DD/MM/YYYY
             if "-" in data_formatada:
                 try:
                     parts = data_formatada.split("-")
                     if len(parts) == 3:
                         data_formatada = f"{parts[2]}/{parts[1]}/{parts[0]}"
                 except:
                     pass # Mantém original se falhar
        
        add_pred("Data", data_formatada)
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
        
        # Novos Campos
        add_pred("IBS", data.ibs, "0.00")
        add_pred("CBS", data.cbs)
        
        # Valor Líquido - Formatação BRL 9.999,99
        val_liq = data.valor_liquido
        if val_liq is None and data.valor_total is not None:
             # Regra básica se nulo: Total - Retenções
             # Assumindo 0 se retenções nulas
             retencoes = (data.valor_pis or 0) + (data.valor_cofins or 0) + (data.valor_inss or 0) + (data.valor_ir or 0) + (data.valor_csll or 0)
             val_liq = data.valor_total - retencoes
        
        val_liq_str = "0,00"
        if val_liq is not None:
            # Formatar brasileiro: ponto milhar, virgula decimal
            val_liq_str = f"{val_liq:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
        predictions.append(LegacyPredictionItem(Label="Valor_Liquido", OCR_Text=val_liq_str, Score="1.0"))
        
        # Base de Cálculo - Regra de Negócio
        # Se não vier extraído, assumir Valor dos Serviços ou Valor Total
        base_calc = data.base_calculo
        if base_calc is None:
             base_calc = data.valor_servicos if data.valor_servicos is not None else data.valor_total
        
        add_pred("Base_Calculo", base_calc, "0.00")
        
        logger.info(f"Retornando resposta legado com {len(predictions)} campos.")
        response_obj = LegacyResponse(Result=[LegacyResult(Prediction=predictions)])
        logger.info(f"Resposta da API: {response_obj.model_dump_json()}")
        
        # Logar no MongoDB
        await log_to_mongo(
            endpoint="/api/extractData2",
            request_data={"Base64File_len": len(request.Base64File)},
            response_data=response_obj.model_dump(),
            usage=data.usage # data vem do extract_data_from_pdf
        )

        return response_obj
        
    except HTTPException as he:
        await log_to_mongo(endpoint="/api/extractData2", request_data=None, response_data=None, status_code=he.status_code, error=he.detail)
        raise he
    except Exception as e:
        await log_to_mongo(endpoint="/api/extractData2", request_data=None, response_data=None, status_code=500, error=str(e))
        logger.error(f"Erro legado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/api/dashboard/stats")
async def dashboard_stats(username: str = Depends(get_current_username)):
    logs_collection = await get_logs_collection()
    
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "total_input_tokens": {"$sum": "$input_tokens"},
                "total_output_tokens": {"$sum": "$output_tokens"},
                "total_provider_cost": {"$sum": "$provider_cost"},
                "total_revenue": {"$sum": "$final_price"},
                "avg_confidence": {"$avg": 1.0} # Placeholder, idealmente viria dos logs
            }
        }
    ]
    
    stats = await logs_collection.aggregate(pipeline).to_list(length=1)
    
    if stats:
        s = stats[0]
        return {
            "total_requests": s.get("total_requests", 0),
            "total_tokens": s.get("total_input_tokens", 0) + s.get("total_output_tokens", 0),
            "total_provider_cost": s.get("total_provider_cost", 0.0),
            "total_revenue": s.get("total_revenue", 0.0),
            "avg_confidence": 0.98 # Simulado por enquanto
        }
    return {
        "total_requests": 0, "total_tokens": 0, "total_provider_cost": 0.0, "total_revenue": 0.0, "avg_confidence": 0.0
    }

@app.get("/api/dashboard/logs")
async def dashboard_logs(
    page: int = 1, 
    limit: int = 10, 
    status: str = None, 
    start_date: str = None, 
    end_date: str = None,
    username: str = Depends(get_current_username)
):
    logs_collection = await get_logs_collection()
    query = {}
    
    if status:
        if status == "success":
            query["status_code"] = 200
        elif status == "error":
            query["status_code"] = {"$ne": 200}
            
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query["timestamp"] = {"$gte": start, "$lt": end}
        except:
            pass

    total_logs = await logs_collection.count_documents(query)
    cursor = logs_collection.find(query).sort("timestamp", -1).skip((page - 1) * limit).limit(limit)
    logs = await cursor.to_list(length=limit)
    
    # Converter ObjectId e datetime para JSON
    serialized_logs = []
    for log in logs:
        log["_id"] = str(log["_id"])
        log["timestamp"] = log["timestamp"].isoformat()
        serialized_logs.append(log)
        
    return {
        "data": serialized_logs,
        "total": total_logs,
        "page": page,
        "limit": limit,
        "total_pages": (total_logs + limit - 1) // limit
    }

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(username: str = Depends(get_current_username)):
    with open("app/templates/dashboard.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    # Nota: No ambiente real, use uvicorn via CLI ou python -m
    uvicorn.run(app, host="0.0.0.0", port=8000)
