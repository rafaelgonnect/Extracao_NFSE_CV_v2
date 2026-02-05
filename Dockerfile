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

# Copiar o restante do código
COPY . .

# Expor a porta
EXPOSE 8002

# Comando de execução
CMD ["python", "-m", "app.main"]
