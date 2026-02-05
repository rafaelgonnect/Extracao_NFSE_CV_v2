FROM python:3.10-slim

# Evitar buffering do Python para ver logs em tempo real
ENV PYTHONUNBUFFERED=1
ENV PORT=8002

# Instalar dependências do sistema (Poppler é obrigatório para pdf2image)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Configurar diretório de trabalho
WORKDIR /app

# Copiar arquivos de dependência
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Criar o script de entrypoint diretamente no build para garantir LF (Linux)
# e evitar erros de CRLF do Windows
RUN printf '#!/bin/bash\n\
set -e\n\
echo "--- ENTRYPOINT INICIADO ---"\n\
export PORT=${PORT:-80}\n\
echo "--- PORTA CONFIGURADA: $PORT ---"\n\
exec python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT\n\
' > /app/entrypoint.sh

# Dar permissão de execução
RUN chmod +x /app/entrypoint.sh

# Copiar o restante do código
COPY . .

# Expor a porta 80 (padrão container)
EXPOSE 80

# Comando de execução usando o entrypoint script criado
CMD ["/app/entrypoint.sh"]
