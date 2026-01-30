from pydantic import BaseModel, Field
from typing import List, Optional

class PDFRequest(BaseModel):
    pdf_base64: str = Field(..., description="Arquivo PDF codificado em Base64")

class NFSeItem(BaseModel):
    descricao: str
    quantidade: Optional[float] = None
    valor_unitario: Optional[float] = None
    valor_total: Optional[float] = None

class NFSeData(BaseModel):
    # Cabeçalho
    numero_nota: Optional[str] = Field(None, description="Número da Nota Fiscal")
    data_emissao: Optional[str] = Field(None, description="Data de emissão da nota")
    codigo_verificacao: Optional[str] = Field(None, description="Código de verificação de autenticidade")
    
    # Prestador
    prestador_cnpj: Optional[str] = None
    prestador_razao_social: Optional[str] = None
    prestador_inscricao_municipal: Optional[str] = None
    prestador_endereco: Optional[str] = None
    
    # Tomador
    tomador_cnpj: Optional[str] = None
    tomador_razao_social: Optional[str] = None
    tomador_inscricao_municipal: Optional[str] = None
    tomador_endereco: Optional[str] = None
    
    # Valores e Impostos
    valor_total: Optional[float] = None
    valor_servicos: Optional[float] = None
    valor_iss: Optional[float] = None
    aliquota_iss: Optional[float] = None
    base_calculo: Optional[float] = None
    iss_retido: Optional[bool] = None
    valor_liquido: Optional[float] = None
    
    # Retenções Federais
    valor_pis: Optional[float] = None
    valor_cofins: Optional[float] = None
    valor_ir: Optional[float] = None
    valor_csll: Optional[float] = None
    valor_inss: Optional[float] = None
    
    # Detalhes do Serviço
    discriminacao_servicos: Optional[str] = None
    codigo_servico: Optional[str] = None
    cnae: Optional[str] = None
    itens_servico: List[NFSeItem] = Field(default_factory=list)
    
    # Outros
    municipio_prestacao: Optional[str] = None
    outras_informacoes: Optional[str] = None
