import asyncio
import base64
import json
import time
from pathlib import Path
import httpx
import logging

# Configuração simples de log para o teste
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

API_URL = "http://localhost:8000/extract"
CONCURRENT_REQUESTS = 15
# Use um PDF pequeno para o teste de carga
SAMPLE_PDF_PATH = "35057082220729538000149000000000003126017564074962 (1).pdf"

async def send_request(client, pdf_b64, worker_id):
    start = time.time()
    try:
        logger.info(f"Worker {worker_id}: Iniciando requisição...")
        response = await client.post(
            API_URL, 
            json={"pdf_base64": pdf_b64},
            timeout=300.0
        )
        duration = time.time() - start
        if response.status_code == 200:
            logger.info(f"Worker {worker_id}: SUCESSO em {duration:.2f}s")
            return True, duration
        else:
            logger.error(f"Worker {worker_id}: FALHA (Status {response.status_code}) em {duration:.2f}s | {response.text}")
            return False, duration
    except Exception as e:
        duration = time.time() - start
        logger.error(f"Worker {worker_id}: ERRO {str(e)} em {duration:.2f}s")
        return False, duration

async def main():
    if not Path(SAMPLE_PDF_PATH).exists():
        logger.error(f"Arquivo de amostra {SAMPLE_PDF_PATH} não encontrado!")
        return

    with open(SAMPLE_PDF_PATH, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode('utf-8')

    logger.info(f"Iniciando teste de carga com {CONCURRENT_REQUESTS} requisições simultâneas...")
    
    async with httpx.AsyncClient() as client:
        tasks = [send_request(client, pdf_b64, i) for i in range(CONCURRENT_REQUESTS)]
        results = await asyncio.gather(*tasks)

    successes = sum(1 for r, _ in results if r)
    durations = [d for _, d in results]
    
    logger.info("="*50)
    logger.info("RESULTADO DO TESTE DE CARGA")
    logger.info("="*50)
    logger.info(f"Requisições: {CONCURRENT_REQUESTS}")
    logger.info(f"Sucessos:    {successes}")
    logger.info(f"Falhas:      {CONCURRENT_REQUESTS - successes}")
    logger.info(f"Tempo Médio: {sum(durations)/len(durations):.2f}s")
    logger.info(f"Tempo Máximo: {max(durations):.2f}s")
    logger.info(f"Tempo Mínimo: {min(durations):.2f}s")
    logger.info("="*50)

if __name__ == "__main__":
    asyncio.run(main())
