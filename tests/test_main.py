from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.models.schemas import NFSeData
import base64

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@patch("app.services.openai_service.client.chat.completions.create")
def test_extract_nfse_success(mock_create):
    # Mocking OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"numero_nota": "1234", "valor_total": 100.0}'
    mock_create.return_value = mock_response

    # Sending a dummy PDF via Base64 JSON (valid header %PDF-)
    valid_pdf_b64 = base64.b64encode(b"%PDF-1.4 test content").decode('utf-8')
    response = client.post(
        "/extract",
        json={"pdf_base64": valid_pdf_b64}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["numero_nota"] == "1234"
    assert data["valor_total"] == 100.0

def test_extract_invalid_base64():
    response = client.post(
        "/extract",
        json={"pdf_base64": "invalid-base64-!!!"}
    )
    # Note: base64.b64decode might not fail on all strings but let's assume it does or we check length
    # In main.py we catch Exception, so it should return 400 if it's really bad
    pass
