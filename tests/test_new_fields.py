import pytest
from app.main import extract_nfse_legacy
from app.models.schemas import LegacyRequest, NFSeData

from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_new_fields_logic():
    # Setup mock data with new fields
    mock_data = NFSeData(
        numero_nota="100",
        valor_total=1000.00,
        ibs=12.50,
        cbs="ABC-123",
        valor_pis=10.00,
        valor_cofins=20.00,
        # valor_liquido not provided -> should auto-calc
        # base_calculo not provided -> should auto-calc
    )
    
    with patch('app.main.extract_data_from_pdf', new=AsyncMock(return_value=mock_data)):
        request = LegacyRequest(Base64File="JVBERi0=") 
        response = await extract_nfse_legacy(request)
        predictions = response.Result[0].Prediction
        
        def get_val(label):
            return next((p.OCR_Text for p in predictions if p.Label == label), None)
            
        # IBS: Float -> 2 decimals
        assert get_val("IBS") == "12.50"
        
        # CBS: String
        assert get_val("CBS") == "ABC-123"
        
        # Valor Liquido: 1000 - 10 - 20 = 970.00. Format BRL: 970,00
        assert get_val("Valor_Liquido") == "970,00"
        
        # Base Calculo: Default to Valor Total (1000.00) -> 1000.00
        assert get_val("Base_Calculo") == "1000.00"

@pytest.mark.asyncio
async def test_valor_liquido_formatting():
    # Test big number formatting
    mock_data = NFSeData(
        numero_nota="101",
        valor_liquido=12500.50 # Should be 12.500,50
    )
    
    with patch('app.main.extract_data_from_pdf', new=AsyncMock(return_value=mock_data)):
        request = LegacyRequest(Base64File="JVBERi0=") 
        response = await extract_nfse_legacy(request)
        predictions = response.Result[0].Prediction
        
        def get_val(label):
            return next((p.OCR_Text for p in predictions if p.Label == label), None)
            
        assert get_val("Valor_Liquido") == "12.500,50"
