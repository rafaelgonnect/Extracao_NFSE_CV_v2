import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from contextvars import ContextVar

# ContextVar para rastrear o Request ID em threads/async
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="system")

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get()
        return True

def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Formato detalhado: Timestamp | Nível | RequestID | Logger | Mensagem
    log_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s'
    )

    # Handler para Console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.addFilter(RequestIdFilter())

    # Handler para Arquivo com Rotação (10MB por arquivo, mantém 5 backups)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(log_format)
    file_handler.addFilter(RequestIdFilter())

    # Configuração Global
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remover handlers existentes para evitar duplicidade
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Silenciar logs de bibliotecas externas (opcional)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)

    logging.info("Sistema de logs inicializado com sucesso.")
