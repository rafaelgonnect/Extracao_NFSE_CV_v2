
import httpx
import time

def check_url(start_id):
    base_url = "https://ocr-webviewersolutions.com/WVC/Validation/{}/0002.pdf"
    current_id = start_id
    
    print(f"Iniciando busca a partir do ID: {current_id}")
    
    with httpx.Client() as client:
        while True:
            url = base_url.format(current_id)
            try:
                # Usamos HEAD request para ser mais rápido e eficiente (baixa só os headers)
                response = client.head(url)
                
                if response.status_code == 200:
                    print(f"\n[SUCESSO] Arquivo encontrado!")
                    print(f"URL: {url}")
                    return url
                elif response.status_code == 404:
                    print(f"Checking {current_id}... (404 Not Found)", end='\r')
                else:
                    print(f"Checking {current_id}... (Status: {response.status_code})", end='\r')
                
                current_id += 1
                # Pequena pausa para evitar sobrecarregar o servidor
                time.sleep(0.1)
                
            except Exception as e:
                print(f"\nErro ao verificar ID {current_id}: {e}")
                # Em caso de erro de conexão, espera um pouco mais e tenta o próximo
                time.sleep(1)
                current_id += 1

if __name__ == "__main__":
    # ID inicial fornecido pelo usuário
    START_ID = 378778
    found_url = check_url(START_ID)
