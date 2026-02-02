using System;
using Newtonsoft.Json;

namespace NFSeExtractorApp
{
    public class NFSeData
    {
        [JsonProperty("numero_nota")]
        public string NumeroNota { get; set; }

        [JsonProperty("data_emissao")]
        public string DataEmissao { get; set; }

        [JsonProperty("codigo_verificacao")]
        public string CodigoVerificacao { get; set; }

        [JsonProperty("prestador_cnpj")]
        public string PrestadorCnpj { get; set; }

        [JsonProperty("prestador_razao_social")]
        public string PrestadorRazaoSocial { get; set; }

        [JsonProperty("prestador_inscricao_municipal")]
        public string PrestadorInscricaoMunicipal { get; set; }

        [JsonProperty("prestador_endereco")]
        public string PrestadorEndereco { get; set; }

        [JsonProperty("tomador_cnpj")]
        public string TomadorCnpj { get; set; }

        [JsonProperty("tomador_razao_social")]
        public string TomadorRazaoSocial { get; set; }

        [JsonProperty("tomador_inscricao_municipal")]
        public string TomadorInscricaoMunicipal { get; set; }

        [JsonProperty("tomador_endereco")]
        public string TomadorEndereco { get; set; }

        [JsonProperty("valor_total")]
        public decimal? ValorTotal { get; set; }

        [JsonProperty("valor_servicos")]
        public decimal? ValorServicos { get; set; }

        [JsonProperty("valor_iss")]
        public decimal? ValorIss { get; set; }

        [JsonProperty("aliquota_iss")]
        public decimal? AliquotaIss { get; set; }

        [JsonProperty("base_calculo")]
        public decimal? BaseCalculo { get; set; }

        [JsonProperty("iss_retido")]
        public bool? IssRetido { get; set; }

        [JsonProperty("valor_liquido")]
        public decimal? ValorLiquido { get; set; }

        [JsonProperty("valor_pis")]
        public decimal? ValorPis { get; set; }

        [JsonProperty("valor_cofins")]
        public decimal? ValorCofins { get; set; }

        [JsonProperty("valor_ir")]
        public decimal? ValorIr { get; set; }

        [JsonProperty("valor_csll")]
        public decimal? ValorCsll { get; set; }

        [JsonProperty("valor_inss")]
        public decimal? ValorInss { get; set; }

        [JsonProperty("discriminacao_servicos")]
        public string DiscriminacaoServicos { get; set; }

        [JsonProperty("codigo_servico")]
        public string CodigoServico { get; set; }

        [JsonProperty("cnae")]
        public string Cnae { get; set; }

        [JsonProperty("municipio_prestacao")]
        public string MunicipioPrestacao { get; set; }

        [JsonProperty("outras_informacoes")]
        public string OutrasInformacoes { get; set; }
    }

    // Classe auxiliar para o envio
    public class ExtractionRequest
    {
        [JsonProperty("pdf_base64")]
        public string PdfBase64 { get; set; }
    }
}
