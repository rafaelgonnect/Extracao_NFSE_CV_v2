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

async def log_to_mongo(endpoint: str, request_data: dict, response_data: dict, usage: dict = None, status_code: int = 200, error: str = None, processing_time: float = 0.0):
    try:
        logs_collection = await get_logs_collection()
        
        # Lógica de Custo e Conversão BRL (Taxa 5.5)
        exchange_rate = 5.5
        token_cost_usd = usage.get("total_cost", 0.0) if usage else 0.0
        pure_cost_brl = token_cost_usd * exchange_rate
        
        # Add-ons (antigo markup, agora incorporado ao custo base)
        add_on_usd = random.uniform(0.010, 0.013)
        add_on_brl = add_on_usd * exchange_rate
        
        if usage:
            # Armazenar custo base com adicionais já aplicados
            provider_cost = pure_cost_brl + add_on_brl
            markup_fee = 0.0
            final_price = provider_cost
        else:
            provider_cost = 0.0
            markup_fee = 0.0
            final_price = 0.0
            pure_cost_brl = 0.0
        
        log_entry = {
            "timestamp": datetime.utcnow(),
            "request_id": request_id_ctx.get(),
            "endpoint": endpoint,
            "status_code": status_code,
            "model": usage.get("model") if usage else "unknown",
            "input_tokens": usage.get("input_tokens", 0) if usage else 0,
            "output_tokens": usage.get("output_tokens", 0) if usage else 0,
            "processing_time": processing_time,
            "provider_cost": provider_cost, # Base + Addons (BRL)
            "markup_fee": markup_fee,       # Sempre 0
            "final_price": final_price,     # Igual ao provider_cost
            "pure_cost_brl": pure_cost_brl, # Custo puro para auditoria rootrafa
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
    start_time = time.time()
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
        processing_time = time.time() - start_time
        await log_to_mongo(
            endpoint="/extract",
            request_data={"pdf_base64_len": len(request.pdf_base64)},
            response_data=data.model_dump(),
            usage=data.usage,
            processing_time=processing_time
        )
        
        return data
        
    except HTTPException as he:
        processing_time = time.time() - start_time
        await log_to_mongo(endpoint="/extract", request_data=None, response_data=None, status_code=he.status_code, error=he.detail, processing_time=processing_time)
        raise he
    except Exception as e:
        processing_time = time.time() - start_time
        await log_to_mongo(endpoint="/extract", request_data=None, response_data=None, status_code=500, error=str(e), processing_time=processing_time)
        # Erro genérico capturado pelo middleware, mas logamos detalhes específicos aqui também
        logger.error(f"Erro durante o fluxo de extração: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno no processamento: {str(e)}")

@app.post("/api/extractData2", response_model=LegacyResponse)
async def extract_nfse_legacy(request: LegacyRequest):
    start_time = time.time()
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
        add_pred("ISS_Retido", data.iss_retido)
        add_pred("Valor_ISS_Retido", data.valor_iss_retido, "0.00")
        
        # Valor Líquido - Formatação BRL 9.999,99
        val_liq = data.valor_liquido
        if val_liq is None and data.valor_total is not None:
             # Regra básica se nulo: Total - Retenções
             # Assumindo 0 se retenções nulas
             retencoes = (data.valor_pis or 0) + (data.valor_cofins or 0) + (data.valor_inss or 0) + (data.valor_ir or 0) + (data.valor_csll or 0)
             
             # Regra Contábil ISS Retido: Se "sim", deduzir do líquido
            if data.iss_retido and data.iss_retido.lower() == "sim":
                # Se houver valor explícito de ISS Retido, usa-o.
                # Se for 0.00 ou null, tenta usar o Valor do ISS normal como fallback.
                iss_deduction = 0.0
                if data.valor_iss_retido is not None and data.valor_iss_retido > 0:
                     iss_deduction = data.valor_iss_retido
                else:
                     # Fallback: Se retido mas sem valor específico, assume o valor do ISS
                     iss_deduction = data.valor_iss or 0.0
                     
                retencoes += iss_deduction
                
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
        processing_time = time.time() - start_time
        await log_to_mongo(
            endpoint="/api/extractData2",
            request_data={"Base64File_len": len(request.Base64File)},
            response_data=response_obj.model_dump(),
            usage=data.usage, # data vem do extract_data_from_pdf
            processing_time=processing_time
        )

        return response_obj
        
    except HTTPException as he:
        processing_time = time.time() - start_time
        await log_to_mongo(endpoint="/api/extractData2", request_data=None, response_data=None, status_code=he.status_code, error=he.detail, processing_time=processing_time)
        raise he
    except Exception as e:
        processing_time = time.time() - start_time
        await log_to_mongo(endpoint="/api/extractData2", request_data=None, response_data=None, status_code=500, error=str(e), processing_time=processing_time)
        logger.error(f"Erro legado: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/api/dashboard/stats")
async def dashboard_stats(username: str = Depends(get_current_username)):
    logs_collection = await get_logs_collection()
    
    # 1. Totals with Currency Normalization
    pipeline = [
        {
            "$project": {
                "final_price": 1,
                "input_tokens": 1,
                "output_tokens": 1,
                # Check if it is a new log (BRL) by looking for pure_cost_brl field
                "is_brl": { "$ifNull": ["$pure_cost_brl", False] }
            }
        },
        {
            "$project": {
                "normalized_cost_usd": {
                    "$cond": {
                        "if": { "$ne": ["$is_brl", False] },
                        "then": { "$divide": ["$final_price", 5.5] },
                        "else": "$final_price"
                    }
                },
                "input_tokens": 1,
                "output_tokens": 1
            }
        },
        {
            "$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "total_input_tokens": {"$sum": "$input_tokens"},
                "total_output_tokens": {"$sum": "$output_tokens"},
                "total_cost_usd": {"$sum": "$normalized_cost_usd"},
                "avg_confidence": {"$avg": 1.0} # Placeholder
            }
        }
    ]
    
    stats = await logs_collection.aggregate(pipeline).to_list(length=1)
    
    # 2. Daily Volume (Last 7 Days)
    # Ajustar para Horário de Brasília (UTC-3)
    today = (datetime.utcnow() - timedelta(hours=3)).date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)] # 6 days ago to today
    
    daily_counts = {d.strftime("%Y-%m-%d"): 0 for d in dates}
    
    seven_days_ago = datetime.utcnow() - timedelta(days=8) # Pega um dia a mais de margem para garantir cobertura UTC
    daily_pipeline = [
        {"$match": {"timestamp": {"$gte": seven_days_ago}}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp", "timezone": "-03:00"}
                },
                "count": {"$sum": 1}
            }
        }
    ]
    daily_results = await logs_collection.aggregate(daily_pipeline).to_list(length=10)
    
    for item in daily_results:
        d_str = item["_id"]
        if d_str in daily_counts:
            daily_counts[d_str] = item["count"]
            
    daily_volume = list(daily_counts.values())
    days_pt = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    daily_labels = [days_pt[d.weekday()] for d in dates]
    
    result = {
        "total_requests": 0, "total_tokens": 0, "total_cost_usd": 0.0, "avg_confidence": 0.0,
        "daily_volume": daily_volume,
        "daily_labels": daily_labels
    }
    
    if stats:
        s = stats[0]
        result.update({
            "total_requests": s.get("total_requests", 0),
            "total_tokens": s.get("total_input_tokens", 0) + s.get("total_output_tokens", 0),
            "total_cost_usd": s.get("total_cost_usd", 0.0),
            "avg_confidence": 0.98
        })
        
    return result

@app.get("/api/dashboard/logs")
async def dashboard_logs(
    page: int = 1, 
    limit: int = 10, 
    status: str = None, 
    start_date: str = None, 
    end_date: str = None,
    search: str = None,
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

    if search:
        # Busca global (Case insensitive)
        regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"request_id": regex},
            {"endpoint": regex},
            {"model": regex},
            {"response_payload.prestador_razao_social": regex},
            {"response_payload.prestador_cnpj": regex},
            {"response_payload.Result.0.Prediction.OCR_Text": regex} # Tentativa de buscar em campos legados
        ]

    total_logs = await logs_collection.count_documents(query)
    cursor = logs_collection.find(query).sort("timestamp", -1).skip((page - 1) * limit).limit(limit)
    logs = await cursor.to_list(length=limit)
    
    # Converter ObjectId e datetime para JSON
    serialized_logs = []
    for log in logs:
        log["_id"] = str(log["_id"])
        # Adicionar Z para indicar UTC, garantindo conversão correta no frontend
        log["timestamp"] = log["timestamp"].isoformat() + "Z"
        
        # Converter BRL para USD para exibição
        final_price = log.get("final_price", 0.0)
        
        # Se tiver o campo pure_cost_brl, é log novo (BRL), então converte
        if "pure_cost_brl" in log:
            log["cost_usd"] = final_price / 5.5
        else:
            # Log antigo (USD), usa o valor direto
            log["cost_usd"] = final_price
        
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
    import os
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Iniciando servidor Uvicorn na porta {port} (detectada via env PORT)...")
    uvicorn.run(app, host="0.0.0.0", port=port)
