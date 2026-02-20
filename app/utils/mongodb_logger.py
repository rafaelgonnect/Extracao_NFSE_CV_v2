import logging
import random
from datetime import datetime
from app.database import get_logs_collection
from app.utils.logging_config import request_id_ctx

logger = logging.getLogger(__name__)

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
            "response_payload": response_data
        }
        await logs_collection.insert_one(log_entry)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar log no MongoDB: {str(e)}")
        return False
