import os
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logger = logging.getLogger(__name__)

MONGO_URI = "mongodb://mongo:L3afarodnil@webviewer_mongowv:27017/?tls=false"
DB_NAME = "nfse_extractor_logs"

class Database:
    client: AsyncIOMotorClient = None
    db = None

    def connect(self):
        try:
            self.client = AsyncIOMotorClient(MONGO_URI)
            self.db = self.client[DB_NAME]
            logger.info(f"Conectado ao MongoDB: {MONGO_URI}")
        except Exception as e:
            logger.error(f"Erro ao conectar ao MongoDB: {str(e)}")
            raise e

    def close(self):
        if self.client:
            self.client.close()
            logger.info("Conexão com MongoDB encerrada.")

db = Database()

async def get_logs_collection():
    return db.db["api_logs"]
