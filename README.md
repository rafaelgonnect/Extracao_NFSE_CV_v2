# API de Extração de NFS-e

API RESTful para extração automatizada de dados de Notas Fiscais de Serviço Eletrônicas (NFS-e) utilizando Computer Vision e OpenAI.

## Tecnologias

- **Python 3.9+**
- **FastAPI**: Framework web moderno e rápido.
- **OpenAI API**: Modelo `gpt-5-nano-2025-08-07` com suporte nativo a PDF (sem conversão intermediária).
- **Pydantic**: Validação de dados.

## Pré-requisitos

1. Python instalado.
2. (Opcional) Docker para deploy em container.

## Instalação

1. Clone o repositório.
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure a variável de ambiente `OPENAI_API_KEY` no arquivo `.env`.

## Execução

Execute o servidor de desenvolvimento:

```bash
uvicorn app.main:app --reload
```

A API estará acessível em `http://localhost:8000`.

## Endpoints

### `POST /extract`

Envia um arquivo PDF para extração.

- **URL**: `/extract`
- **Método**: `POST`
- **Body**: `multipart/form-data` com campo `file` (arquivo PDF).
- **Resposta**: JSON com os dados extraídos.

**Exemplo de Resposta:**

```json
{
  "numero_nota": "1234",
  "data_emissao": "2023-10-27",
  "prestador_cnpj": "00.000.000/0001-00",
  "valor_total": 1500.00,
  "itens_servico": [...]
}
```

### `GET /docs`

Documentação interativa (Swagger UI).
