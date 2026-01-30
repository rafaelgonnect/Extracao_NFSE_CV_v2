import asyncio
import base64
import json
import logging
import os
import shutil
import time
from pathlib import Path
import httpx

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('batch_processing.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Configurações do Script
INPUT_DIR = Path("exemplos pdf")
API_URL = "https://webviewer-nfsextractor.bdoje9.easypanel.host/extract"
CONCURRENCY_LIMIT = 5  # Reduzi para 5 para evitar sobrecarga no servidor remoto
TIMEOUT = 180.0        # Aumentei para 3 minutos devido à complexidade da visão computacional
MAX_RETRIES = 3        # Número máximo de tentativas por arquivo

# Semáforo para controle de concorrência
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

async def process_single_pdf(client: httpx.AsyncClient, pdf_path: Path):
    """Processa um único arquivo PDF com lógica de retentativa e criação de pastas."""
    async with semaphore:
        pdf_name = pdf_path.stem
        target_dir = INPUT_DIR / pdf_name
        
        # 1. Validação e Preparação (fora do loop de retry)
        try:
            with open(pdf_path, "rb") as f:
                header = f.read(5)
                if header != b"%PDF-":
                    return pdf_name, "ERRO: Arquivo não é um PDF válido"
            
            target_dir.mkdir(exist_ok=True)
            shutil.copy2(pdf_path, target_dir / pdf_path.name)
            
            with open(pdf_path, "rb") as f:
                pdf_b64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            return pdf_name, f"ERRO PREPARAÇÃO: {str(e)}"

        # 2. Loop de Retentativa para Chamada de API
        for attempt in range(MAX_RETRIES):
            start_time = time.time()
            try:
                logger.info(f"Processando: {pdf_path.name} (Tentativa {attempt + 1}/{MAX_RETRIES})...")
                
                response = await client.post(
                    API_URL,
                    json={"pdf_base64": pdf_b64},
                    timeout=TIMEOUT
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    result_file = target_dir / f"result_{pdf_name}.json"
                    with open(result_file, "w", encoding="utf-8") as f:
                        json.dump(result_data, f, indent=4, ensure_ascii=False)
                    
                    duration = time.time() - start_time
                    logger.info(f"SUCESSO: {pdf_path.name} em {duration:.2f}s")
                    return pdf_name, "SUCESSO"
                
                elif response.status_code == 401:
                    error_detail = response.json().get("detail", "Erro de Autenticação (401)")
                    logger.error(f"FALHA CRÍTICA (401): {pdf_path.name} | Verifique a API KEY no Easypanel! | {error_detail}")
                    return pdf_name, f"ERRO 401: {error_detail}"
                
                else:
                    try:
                        error_msg = response.json().get("detail", response.text)
                    except:
                        error_msg = response.text
                    
                    logger.warning(f"FALHA TENTATIVA {attempt + 1}: {pdf_path.name} | Status {response.status_code} | {error_msg}")
                    
                    if attempt < MAX_RETRIES - 1:
                        wait_time = (attempt + 1) * 5 # Backoff simples
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        return pdf_name, f"ERRO API ({response.status_code}): {error_msg}"

            except httpx.TimeoutException:
                logger.warning(f"TIMEOUT na tentativa {attempt + 1}: {pdf_path.name}")
                if attempt < MAX_RETRIES - 1:
                    continue
                return pdf_name, "ERRO: Timeout da API"
            except Exception as e:
                logger.error(f"ERRO INESPERADO: {pdf_path.name} | {str(e)}")
                return pdf_name, f"ERRO: {str(e)}"
        
        return pdf_name, "FALHA APÓS RETENTATIVAS"

async def main():
    # Garantir que a pasta de entrada existe
    if not INPUT_DIR.exists():
        logger.error(f"Pasta '{INPUT_DIR}' não encontrada!")
        return

    # Listar todos os arquivos PDF
    pdf_files = [f for f in INPUT_DIR.glob("*.pdf")]
    if not pdf_files:
        logger.warning("Nenhum arquivo .pdf encontrado na pasta de entrada.")
        return

    logger.info(f"Iniciando processamento em lote de {len(pdf_files)} arquivos...")
    total_start = time.time()

    results = []
    async with httpx.AsyncClient() as client:
        tasks = [process_single_pdf(client, pdf_file) for pdf_file in pdf_files]
        results = await asyncio.gather(*tasks)

    # Relatório Final
    total_duration = time.time() - total_start
    success_count = sum(1 for _, status in results if status == "SUCESSO")
    failure_count = len(results) - success_count

    logger.info("="*50)
    logger.info("RELATÓRIO FINAL DE PROCESSAMENTO")
    logger.info("="*50)
    logger.info(f"Total de arquivos:    {len(results)}")
    logger.info(f"Sucessos:             {success_count}")
    logger.info(f"Falhas:               {failure_count}")
    logger.info(f"Tempo total:          {total_duration:.2f}s")
    logger.info(f"Média por arquivo:    {total_duration/len(results) if results else 0:.2f}s")
    logger.info("="*50)

    # Detalhes das falhas
    if failure_count > 0:
        logger.info("DETALHES DAS FALHAS:")
        for name, status in results:
            if status != "SUCESSO":
                logger.info(f"- {name}: {status}")
    
    logger.info("Processamento finalizado. Verifique as pastas individuais e o arquivo batch_processing.log.")

if __name__ == "__main__":
    asyncio.run(main())
