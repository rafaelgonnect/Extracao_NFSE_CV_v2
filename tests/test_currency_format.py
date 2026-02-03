import pytest
from app.main import extract_nfse_legacy
from app.models.schemas import LegacyRequest, NFSeData

# Mocking extract_data_from_pdf to return controlled data
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_legacy_currency_format():
    # Setup mock return value with various float values
    mock_data = NFSeData(
        numero_nota="123",
        valor_total=304.0,   # Should become "304.00"
        valor_iss=15.5,      # Should become "15.50"
        aliquota_iss=5.0,    # Should become "5.00"
        valor_pis=0.0,       # Should become "0.00"
        valor_cofins=None    # Should use default "0.00"
    )
    
    with patch('app.main.extract_data_from_pdf', new=AsyncMock(return_value=mock_data)):
        # Valid base64 PDF header
        request = LegacyRequest(Base64File="JVBERi0=") 
        
        response = await extract_nfse_legacy(request)
        
        predictions = response.Result[0].Prediction
        
        # Helper to get value by label
        def get_val(label):
            return next((p.OCR_Text for p in predictions if p.Label == label), None)
            
        assert get_val("Valor_Total") == "304.00"
        assert get_val("Valor_ISS") == "15.50"
        assert get_val("Aliquota") == "5.00"
        assert get_val("PIS") == "0.00"
        assert get_val("COFINS") == "0.00" # Default value check
