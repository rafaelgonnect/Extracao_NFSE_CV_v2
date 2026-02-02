using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using Newtonsoft.Json;
using Microsoft.Web.WebView2.Core;

namespace NFSeExtractorApp
{
    public partial class Form1 : Form
    {
        private const string API_ENDPOINT = "https://webviewer-nfsextractor.bdoje9.easypanel.host/extract";
        private string selectedFilePath = string.Empty;

        public Form1()
        {
            InitializeComponent();
            InitializeWebView();
        }

        private async void InitializeWebView()
        {
            try
            {
                await pdfViewer.EnsureCoreWebView2Async(null);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Erro ao inicializar WebView2 (PDF Viewer): " + ex.Message + "\nVerifique se o WebView2 Runtime está instalado.");
            }
        }

        private void btnSelect_Click(object sender, EventArgs e)
        {
            using (OpenFileDialog openFileDialog = new OpenFileDialog())
            {
                openFileDialog.Filter = "Arquivos PDF (*.pdf)|*.pdf";
                openFileDialog.Title = "Selecione a NFS-e em PDF";

                if (openFileDialog.ShowDialog() == DialogResult.OK)
                {
                    selectedFilePath = openFileDialog.FileName;
                    txtFilePath.Text = selectedFilePath;
                    btnSend.Enabled = true;
                    UpdateStatus("Arquivo selecionado. Pronto para enviar.");
                    dgvResults.Rows.Clear();
                    
                    // Carrega o PDF no WebBrowser (WebView2)
                    if (pdfViewer != null && pdfViewer.CoreWebView2 != null)
                    {
                        pdfViewer.CoreWebView2.Navigate(selectedFilePath);
                    }
                    else
                    {
                        pdfViewer.Source = new Uri(selectedFilePath);
                    }
                }
            }
        }

        private async void btnSend_Click(object sender, EventArgs e)
        {
            if (string.IsNullOrEmpty(selectedFilePath) || !File.Exists(selectedFilePath))
            {
                MessageBox.Show("Arquivo inválido ou não encontrado.", "Erro", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            try
            {
                // UI Update
                btnSend.Enabled = false;
                btnSelect.Enabled = false;
                dgvResults.Rows.Clear();
                UpdateStatus("Lendo arquivo e convertendo...", Color.Blue);

                // 1. Converter PDF para Base64
                byte[] fileBytes = File.ReadAllBytes(selectedFilePath);
                string base64String = Convert.ToBase64String(fileBytes);

                // 2. Montar Payload
                var requestData = new ExtractionRequest { PdfBase64 = base64String };
                string jsonPayload = JsonConvert.SerializeObject(requestData);
                var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                UpdateStatus("Enviando para API...", Color.Orange);

                // 3. Enviar Requisição (Async)
                using (HttpClient client = new HttpClient())
                {
                    // Timeout de 1 minuto para garantir processamento
                    client.Timeout = TimeSpan.FromMinutes(1);

                    HttpResponseMessage response = await client.PostAsync(API_ENDPOINT, content);

                    if (response.IsSuccessStatusCode)
                    {
                        string responseBody = await response.Content.ReadAsStringAsync();
                        ProcessResponse(responseBody);
                        UpdateStatus("Extração concluída com sucesso!", Color.Green);
                    }
                    else
                    {
                        string errorBody = await response.Content.ReadAsStringAsync();
                        UpdateStatus($"Erro na API: {response.StatusCode}", Color.Red);
                        MessageBox.Show($"Falha na extração.\nStatus: {response.StatusCode}\nDetalhes: {errorBody}", 
                            "Erro de API", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }
                }
            }
            catch (Exception ex)
            {
                UpdateStatus("Erro interno.", Color.Red);
                MessageBox.Show($"Ocorreu um erro: {ex.Message}", "Erro", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                btnSend.Enabled = true;
                btnSelect.Enabled = true;
            }
        }

        private void ProcessResponse(string jsonResponse)
        {
            try
            {
                var data = JsonConvert.DeserializeObject<NFSeData>(jsonResponse);

                if (data != null)
                {
                    // Adiciona as linhas no DataGridView
                    AddResultRow("Número da Nota", data.NumeroNota);
                    AddResultRow("Data Emissão", data.DataEmissao);
                    AddResultRow("Código Verificação", data.CodigoVerificacao);
                    
                    AddResultRow("Prestador", data.PrestadorRazaoSocial);
                    AddResultRow("CNPJ Prestador", data.PrestadorCnpj);
                    AddResultRow("IM Prestador", data.PrestadorInscricaoMunicipal);
                    AddResultRow("Endereço Prestador", data.PrestadorEndereco);

                    AddResultRow("Tomador", data.TomadorRazaoSocial);
                    AddResultRow("CNPJ Tomador", data.TomadorCnpj);
                    AddResultRow("IM Tomador", data.TomadorInscricaoMunicipal);
                    AddResultRow("Endereço Tomador", data.TomadorEndereco);

                    AddResultRow("Valor Serviços", data.ValorServicos?.ToString("C2"));
                    AddResultRow("Valor Total", data.ValorTotal?.ToString("C2"));
                    AddResultRow("Valor Líquido", data.ValorLiquido?.ToString("C2"));
                    
                    AddResultRow("ISS Retido", data.IssRetido == true ? "Sim" : "Não");
                    AddResultRow("Valor ISS", data.ValorIss?.ToString("C2"));
                    AddResultRow("Alíquota ISS", data.AliquotaIss != null ? $"{data.AliquotaIss}%" : "");
                    AddResultRow("Base Cálculo", data.BaseCalculo?.ToString("C2"));

                    AddResultRow("Valor PIS", data.ValorPis?.ToString("C2"));
                    AddResultRow("Valor COFINS", data.ValorCofins?.ToString("C2"));
                    AddResultRow("Valor IR", data.ValorIr?.ToString("C2"));
                    AddResultRow("Valor CSLL", data.ValorCsll?.ToString("C2"));
                    AddResultRow("Valor INSS", data.ValorInss?.ToString("C2"));

                    AddResultRow("Código Serviço", data.CodigoServico);
                    AddResultRow("CNAE", data.Cnae);
                    AddResultRow("Município Prestação", data.MunicipioPrestacao);
                    
                    AddResultRow("Descrição", data.DiscriminacaoServicos);
                    AddResultRow("Outras Informações", data.OutrasInformacoes);
                }
            }
            catch (JsonException jsonEx)
            {
                MessageBox.Show("Erro ao ler o JSON de resposta: " + jsonEx.Message);
            }
        }

        private void AddResultRow(string campo, string valor)
        {
            if (!string.IsNullOrEmpty(valor))
            {
                dgvResults.Rows.Add(campo, valor);
            }
        }

        private void UpdateStatus(string message, Color? color = null)
        {
            lblStatus.Text = message;
            lblStatus.ForeColor = color ?? Color.Black;
        }
    }
}
