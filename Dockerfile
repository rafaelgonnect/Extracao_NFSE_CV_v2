FROM python:3.10-slim

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
EXPOSE 8000

# Comando de execução
CMD ["python", "-m", "app.main"]
