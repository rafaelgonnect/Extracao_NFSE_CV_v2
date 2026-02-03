import pytest
from app.main import extract_nfse_legacy
from app.models.schemas import LegacyRequest, NFSeData

# Mocking extract_data_from_pdf to return controlled data
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_legacy_date_format():
    # Setup mock return value
    mock_data = NFSeData(
        numero_nota="123",
        data_emissao="2023-10-25T14:30:00", # ISO with time
        codigo_verificacao="ABC",
        valor_total=100.00
    )
    
    with patch('app.main.extract_data_from_pdf', new=AsyncMock(return_value=mock_data)) as mock_extract:
        # Create a dummy request with valid base64 header
        # Base64 for "%PDF-" is JVBERi0=
        
        request = LegacyRequest(Base64File="JVBERi0=") 
        
        response = await extract_nfse_legacy(request)
        
        # Find the "Data" field in predictions
        predictions = response.Result[0].Prediction
        data_pred = next((p for p in predictions if p.Label == "Data"), None)
        
        assert data_pred is not None
        assert data_pred.OCR_Text == "25/10/2023" # Should be converted
        
@pytest.mark.asyncio
async def test_legacy_date_format_already_correct():
    mock_data = NFSeData(
        data_emissao="25/10/2023",
        valor_total=100.00
    )
    
    with patch('app.main.extract_data_from_pdf', new=AsyncMock(return_value=mock_data)):
        request = LegacyRequest(Base64File="JVBERi0=")
        response = await extract_nfse_legacy(request)
        
        predictions = response.Result[0].Prediction
        data_pred = next((p for p in predictions if p.Label == "Data"), None)
        
        assert data_pred.OCR_Text == "25/10/2023"

@pytest.mark.asyncio
async def test_legacy_date_format_iso_simple():
    mock_data = NFSeData(
        data_emissao="2023-10-25",
        valor_total=100.00
    )
    
    with patch('app.main.extract_data_from_pdf', new=AsyncMock(return_value=mock_data)):
        request = LegacyRequest(Base64File="JVBERi0=")
        response = await extract_nfse_legacy(request)
        
        predictions = response.Result[0].Prediction
        data_pred = next((p for p in predictions if p.Label == "Data"), None)
        
        assert data_pred.OCR_Text == "25/10/2023" 
