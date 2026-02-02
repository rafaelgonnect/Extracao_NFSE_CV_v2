private int ReadAI(string sClassify)
		{
			int iRet = 0;
			string sDiscr = ""; string sINFO = "";

			string sFolder = @"\\" + Environment.MachineName.ToString() + @"\WVC\vOCR_1\" + lblBatchID.Text + @"\";
			string[] files = Directory.GetFiles(sFolder + @"\", ".", SearchOption.TopDirectoryOnly);

			//string sBase64 = 


			//string sHost = "";


			try
			{

				
				WriteLog("DEBUG", "Starting AI");
				

				lblAction.Text = "Starting AI";
				this.Refresh();
				Application.DoEvents();
				string sFileName = Path.GetFileName(files[0]);
				string sPDF = Convert.ToBase64String(System.IO.File.ReadAllBytes(files[0]));


				var options = new RestClientOptions("https://ai.gonnect.com.br/")
				{
					//MaxTimeout = -1,
				};
				var client = new RestClient(options);
				//client.Options.Timeout.Value( = -1;
				var request = new RestRequest("/api/extractData2", Method.Post);
				request.AddHeader("Content-Type", "application/json");

				//sPDF = "ola";

				var body = @"{
						""Base64File"": """ + sPDF + @""",
					    ""SecretKey"": ""John Doe"",
						""Queue"": ""Processing"",
						""Priority"": 1
						}";

				request.AddStringBody(body, DataFormat.Json);
				
				

				RestResponse response = client.Execute(request);


				if (response.StatusCode.ToString() == "OK")
				{
					WriteLog("DEBUG", "Returned AI");
					//var data = JsonConvert.DeserializeObject<JsonResult>(response.Content);

					var dataTeste = JsonConvert.DeserializeObject<ApiResponse>(response.Content);

					foreach (var item in dataTeste.Result[0].Prediction)
					{

						string s = item.OCR_Text;

						if (item.Label == "CNPJ_Prest")
						{
							string sCNPJ_Prest = RemoveSpecialCharacters(item.OCR_Text.Replace(" ", "").Replace(".", ""));

							if (sCNPJ_Prest.Length == 14)
								sCNPJ_Prest = Convert.ToUInt64(sCNPJ_Prest).ToString(@"00\.000\.000\/0000\-00");
							if (sCNPJ_Prest.Length == 11)
								sCNPJ_Prest = Convert.ToUInt64(sCNPJ_Prest).ToString(@"000\.000\.000\-00");

							sFieldValue[5] = sCNPJ_Prest;

							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
									{
										sOCRScore[5] = item.Score.Substring(2, 2);
									}
									else
									{
										if (item.Score == "1")
											sOCRScore[5] = "100";
										else
											sOCRScore[5] = item.Score;
									}

								}
								else
									sOCRScore[5] = item.Score;
							}
						}
						if (item.Label == "CNPJ_Tom")
						{
							string sCNPJ_Tom = RemoveSpecialCharacters(item.OCR_Text.Replace(" ", "").Replace(".", ""));
							if (sCNPJ_Tom.Length == 14)
								sCNPJ_Tom = Convert.ToUInt64(sCNPJ_Tom).ToString(@"00\.000\.000\/0000\-00");
							if (sCNPJ_Tom.Length == 11)
								sCNPJ_Tom = Convert.ToUInt64(sCNPJ_Tom).ToString(@"000\.000\.000\-00");

							sFieldValue[10] = sCNPJ_Tom;
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
									{
										sOCRScore[10] = item.Score.Substring(2, 2);
									}
									else
									{
										if (item.Score == "1")
											sOCRScore[10] = "100";
										else
											sOCRScore[10] = item.Score;
									}

								}
								else
									sOCRScore[10] = item.Score;
							}
						}
						if (item.Label == "Numero")
						{
							sFieldValue[1] = RemoveSpecialCharactersNumericOnly(item.OCR_Text);//item.OCR_Text.Replace(" ", "").TrimStart(new Char[] { '0' });
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[1] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[1] = "100";
										else
											sOCRScore[1] = item.Score;
									}

								}
								else
									sOCRScore[1] = item.Score;
							}
						}
						if (item.Label == "RPS")
						{
							//sZone04Value = item.OCR_Text.Replace(" ", "").TrimStart(new Char[] { '0' });
							//if (sZone04Value.Length == 0)
							sFieldValue[4] = "0";
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[4] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[4] = "100";
										else
											sOCRScore[4] = item.Score;
									}

								}
								else
									sOCRScore[4] = item.Score;
							}
						}
						if (item.Label == "Codigo_Servico")
						{
							sFieldValue[26] = item.OCR_Text.Replace(" ", "");
							sFieldValue[26] = RemoveSpecialCharactersNumericOnly(sFieldValue[26]);
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[26] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[26] = "100";
										else
											sOCRScore[26] = item.Score;
									}

								}
								else
									sOCRScore[26] = item.Score;
							}
						}
						if (item.Label == "Data")
						{
							sFieldValue[2] = item.OCR_Text.Replace(" ", "").Replace("-", "/").Replace(".", "/");
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[2] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[2] = "100";
										else
											sOCRScore[2] = item.Score;
									}

								}
								else
									sOCRScore[2] = item.Score;
							}
						}
						if (item.Label == "Pedido")
						{
							sFieldValue[15] = item.OCR_Text.Replace(" ", "");
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[15] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[15] = "100";
										else
											sOCRScore[15] = item.Score;
									}

								}
								else
									sOCRScore[15] = item.Score;
							}
						}
						if (item.Label == "Data_Vencimento")
						{
							sFieldValue[16] = item.OCR_Text.Replace(" ", "");
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[16] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[16] = "100";
										else
											sOCRScore[26] = item.Score;
									}

								}
								else
									sOCRScore[16] = item.Score;
							}
						}
						if (item.Label == "Chave")
						{
							sFieldValue[3] = item.OCR_Text.Replace(" ", "");
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[3] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[3] = "100";
										else
											sOCRScore[3] = item.Score;
									}

								}
								else
									sOCRScore[3] = item.Score;
							}
						}

						if (item.Label == "Valor_Total")
						{
							sFieldValue[17] = RemoveSpecialCharactersAmount(item.OCR_Text);
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[17] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[17] = "100";
										else
											sOCRScore[17] = item.Score;
									}

								}
								else
									sOCRScore[17] = item.Score;
							}

						}
						if (item.Label == "Aliquota")
						{
							sFieldValue[18] = RemoveSpecialCharactersAliquota(item.OCR_Text);
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[18] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[18] = "100";
										else
											sOCRScore[18] = item.Score;
									}

								}
								else
									sOCRScore[18] = item.Score;
							}
						}
						if (item.Label == "Valor_ISS")
						{
							sFieldValue[19] = RemoveSpecialCharactersAmount(item.OCR_Text);
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[19] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[19] = "100";
										else
											sOCRScore[19] = item.Score;
									}

								}
								else
									sOCRScore[19] = item.Score;
							}
						}
						if (item.Label == "PIS")
						{
							sFieldValue[20] = RemoveSpecialCharactersAmount(item.OCR_Text);
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[20] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[20] = "100";
										else
											sOCRScore[20] = item.Score;
									}

								}
								else
									sOCRScore[20] = item.Score;
							}
						}
						if (item.Label == "COFINS")
						{
							sFieldValue[21] = RemoveSpecialCharactersAmount(item.OCR_Text);
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[21] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[21] = "100";
										else
											sOCRScore[21] = item.Score;
									}

								}
								else
									sOCRScore[21] = item.Score;
							}
						}
						if (item.Label == "INSS")
						{
							sFieldValue[22] = RemoveSpecialCharactersAmount(item.OCR_Text);
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[22] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[22] = "100";
										else
											sOCRScore[22] = item.Score;
									}

								}
								else
									sOCRScore[22] = item.Score;
							}
						}
						if (item.Label == "IRRF")
						{
							sFieldValue[23] = RemoveSpecialCharactersAmount(item.OCR_Text);
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[23] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[23] = "100";
										else
											sOCRScore[23] = item.Score;
									}

								}
								else
									sOCRScore[23] = item.Score;
							}
						}
						if (item.Label == "CSLL")
						{
							sFieldValue[24] = RemoveSpecialCharactersAmount(item.OCR_Text);
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[24] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[24] = "100";
										else
											sOCRScore[24] = item.Score;
									}

								}
								else
									sOCRScore[24] = item.Score;
							}
						}
						if (item.Label == "Outras_Retencoes")
						{
							sFieldValue[25] = RemoveSpecialCharactersAmount(item.OCR_Text);
							if (item.Score != null)
							{
								if (item.Score != null)
								{
									if (item.Score.Length > 3)
										sOCRScore[25] = item.Score.Substring(2, 2);
									else
									{
										if (item.Score == "1")
											sOCRScore[25] = "100";
										else
											sOCRScore[25] = item.Score;
									}

								}
								else
									sOCRScore[25] = item.Score;
							}
						}



						if (item.Label == "Email")
						{
							InsertEmail(item.OCR_Text);
						}

						//39
						if (item.Label == "Discriminacao")
						{
							sDiscr = sDiscr + item.OCR_Text;
							sFieldValue[27] = sDiscr;
						}
						//40
						//if (item.Label == "Informacoes_Adicionais")
						//{
						//	sINFO = sINFO + item.OCR_Text;
						//	sFieldValue[40] = sINFO;
						//}
					}




					sFieldValue[1] = RemoveSpecialCharactersNumericOnly(sFieldValue[1]);

					if (sFieldValue[15] == "" || sFieldValue[15] == null)
						sFieldValue[15] = "0";

					if (sFieldValue[2] != null)
					{
						if (sFieldValue[2].Contains("JAN"))
							sFieldValue[2].Replace("JAN", "01");
						if (sFieldValue[2].Contains("FEV"))
							sFieldValue[2].Replace("FEV", "02");
						if (sFieldValue[2].Contains("MAR"))
							sFieldValue[2].Replace("MAR", "03");
						if (sFieldValue[2].Contains("ABR"))
							sFieldValue[2].Replace("ABR", "04");
						if (sFieldValue[2].Contains("MAI"))
							sFieldValue[2].Replace("MAI", "05");
						if (sFieldValue[2].Contains("JUN"))
							sFieldValue[2].Replace("JUN", "06");
						if (sFieldValue[2].Contains("JUL"))
							sFieldValue[2].Replace("JUL", "07");
						if (sFieldValue[2].Contains("AGO"))
							sFieldValue[2].Replace("AGO", "08");
						if (sFieldValue[2].Contains("SET"))
							sFieldValue[2].Replace("SET", "09");
						if (sFieldValue[2].Contains("OUT"))
							sFieldValue[2].Replace("OUT", "10");
						if (sFieldValue[2].Contains("NOV"))
							sFieldValue[2].Replace("NOV", "11");
						if (sFieldValue[2].Contains("DEZ"))
							sFieldValue[2].Replace("DEZ", "12");
					}

					//DT_Vencimento
					if (sFieldValue[16] == "" || sFieldValue[16] == null)
						sFieldValue[16] = "00/00/0000";

					if (sFieldValue[16] != null)
					{
						if (sFieldValue[16].Contains("JAN"))
							sFieldValue[16].Replace("JAN", "01");
						if (sFieldValue[16].Contains("FEV"))
							sFieldValue[16].Replace("FEV", "02");
						if (sFieldValue[16].Contains("MAR"))
							sFieldValue[16].Replace("MAR", "03");
						if (sFieldValue[16].Contains("ABR"))
							sFieldValue[16].Replace("ABR", "04");
						if (sFieldValue[16].Contains("MAI"))
							sFieldValue[16].Replace("MAI", "05");
						if (sFieldValue[16].Contains("JUN"))
							sFieldValue[16].Replace("JUN", "06");
						if (sFieldValue[16].Contains("JUL"))
							sFieldValue[16].Replace("JUL", "07");
						if (sFieldValue[16].Contains("AGO"))
							sFieldValue[16].Replace("AGO", "08");
						if (sFieldValue[16].Contains("SET"))
							sFieldValue[16].Replace("SET", "09");
						if (sFieldValue[16].Contains("OUT"))
							sFieldValue[16].Replace("OUT", "10");
						if (sFieldValue[16].Contains("NOV"))
							sFieldValue[16].Replace("NOV", "11");
						if (sFieldValue[16].Contains("DEZ"))
							sFieldValue[16].Replace("DEZ", "12");
					}

					if (sFieldValue[3] == "" || sFieldValue[3] == null)
						sFieldValue[3] = "0";
					else
						sFieldValue[3] = sFieldValue[3].ToUpper();



					if (sFieldValue[4] == "" || sFieldValue[4] == null)
						sFieldValue[4] = "0";

					if (sFieldValue[18] == "" || sFieldValue[18] == null)
						sFieldValue[18] = "0.00";

					if (sFieldValue[19] == "" || sFieldValue[19] == null)
						sFieldValue[19] = "0.00";

					if (sFieldValue[20] == "" || sFieldValue[20] == null)
						sFieldValue[20] = "0.00";

					if (sFieldValue[21] == "" || sFieldValue[21] == null)
						sFieldValue[21] = "0.00";

					if (sFieldValue[22] == "" || sFieldValue[22] == null)
						sFieldValue[22] = "0.00";

					if (sFieldValue[23] == "" || sFieldValue[23] == null)
						sFieldValue[23] = "0.00";

					if (sFieldValue[24] == "" || sFieldValue[24] == null)
						sFieldValue[24] = "0.00";

					if (sFieldValue[25] == "" || sFieldValue[25] == null)
						sFieldValue[25] = "0.00";



					lblAction.Text = "Finished AI - Fields Retreval";
					this.Refresh();
					Application.DoEvents();

					WebviewerCapture.CaptureServices WSCapture = new WebviewerCapture.CaptureServices();

					

					string sRet = WSCapture.NFSe_GetCNPJ_Prest("", sFieldValue[5]);
					string[] sRetvOCR_1 = sRet.Split(';');
					sFieldValue[6] = sRetvOCR_1[1].ToString();
					sFieldValue[7] = sRetvOCR_1[2].ToString();
					sFieldValue[8] = sRetvOCR_1[3].ToString();
					sFieldValue[9] = sRetvOCR_1[4].ToString();

					string sRet2 = WSCapture.NFSe_GetCNPJ_Tom("", sFieldValue[10]);
					string[] sRetvOCR_12 = sRet2.Split(';');
					sFieldValue[11] = sRetvOCR_12[1].ToString();
					sFieldValue[12] = sRetvOCR_12[2].ToString();
					sFieldValue[13] = sRetvOCR_12[3].ToString();
					sFieldValue[14] = sRetvOCR_12[4].ToString();





					int iRetDMS = CheckDMS(lblBatchDefName.Text, sFieldValue[1], sFieldValue[2], sFieldValue[5], sFieldValue[10]);
					string sBatchMessage = "";


					string sNextQueue = "Validation";

					//score conversion


					for (int i = 1; i <= 26; i++)
					{
						if (sOCRScore[i] != null)
							iScore[i] = Convert.ToInt32(sOCRScore[i]);
						else
							iScore[i] = 0;
					}





					//score conversion


					WriteLog("DEBUG", "Finished AI");


					if (iRetDMS == 1)
					{
						lblAction.Text = "Duplicated Record:Yes";
						this.Refresh();
						Application.DoEvents();
						sNextQueue = "Editor";
						sBatchMessage = "Duplicated Record:Yes";
						//Directory.CreateDirectory(sFile.Replace("vOCR_1", "Editor"));
						Directory.CreateDirectory(sFolder.Replace("vOCR_1", "Editor"));
						File.Move(files[0], files[0].Replace("vOCR_1", "Editor"));
						UpdateBatch("Rejected", lblBatchID.Text, sNextQueue, sBatchMessage, 1);




						try
						{
							sFolder = strSharedFolder + @"\" + "vOCR_1" + @"\" + lblBatchID.Text;
							System.IO.DirectoryInfo di = new DirectoryInfo(sFolder);

							foreach (FileInfo file in di.GetFiles())//for to delete thumbs files (hidden file)
							{
								file.Delete();
							}
							System.IO.Directory.Delete(sFolder, true);
						}
						catch { }

					}
					else
					{
						try
						{

							//if (sFieldValue[1] != "" && sFieldValue[2] != "" && sFieldValue[3] != "" && sFieldValue[4] != "" && sFieldValue[5] != "" && sFieldValue[6] != "" && sFieldValue[7] != "" && sFieldValue[8] != "" && sFieldValue[9] != "" && sFieldValue[10] != "" && sFieldValue[11] != "" && sFieldValue[12] != "" && sFieldValue[13] != "" && sFieldValue[14] != "" && sFieldValue[15] != "" && sFieldValue[16] != "" && sFieldValue[17] != "" && sFieldValue[18] != "" && sFieldValue[19] != "" && sFieldValue[20] != "" && sFieldValue[21] != "" && sFieldValue[22] != "" && sFieldValue[23] != "" && sFieldValue[24] != "" && sFieldValue[25] != "" && sFieldValue[26] != "" && iScore[1] > 80 && iScore[2] > 80 && iScore[3] > 80 && iScore[4] > 80 && iScore[5] > 80 && iScore[10] > 80 && iScore[15] > 80 && iScore[16] > 80 && iScore[17] > 80 && iScore[18] > 80 && iScore[19] > 80 && iScore[20] > 80 && iScore[21] > 80 && iScore[22] > 80 && iScore[23] > 80 && iScore[24] > 80 && iScore[25] > 80 && iScore[26] > 80)

							//if (sFieldValue[1] != "" && sFieldValue[2] != "" && sFieldValue[3] != "" && sFieldValue[4] != "" && sFieldValue[5] != "" && sFieldValue[6] != "" && sFieldValue[7] != "" && sFieldValue[8] != "" && sFieldValue[9] != "" && sFieldValue[10] != "" && sFieldValue[11] != "" && sFieldValue[12] != "" && sFieldValue[13] != "" && sFieldValue[14] != "" && sFieldValue[15] != "" && sFieldValue[16] != "" && sFieldValue[17] != "" && sFieldValue[18] != "" && sFieldValue[19] != "" && sFieldValue[20] != "" && sFieldValue[21] != "" && sFieldValue[22] != "" && sFieldValue[23] != "" && sFieldValue[24] != "" && sFieldValue[25] != "" && sFieldValue[26] != "" && iScore[1] > 80 && iScore[2] > 80 && iScore[5] > 80 && iScore[10] > 80 && iScore[17] > 80 && iScore[18] > 80 && iScore[19] > 80 && iScore[20] > 80 && iScore[21] > 80 && iScore[22] > 80 && iScore[23] > 80 && iScore[24] > 80 && iScore[26] > 80)
							//{

							//	sNextQueue = "Release";
							//	if (sFieldValue[5] == sFieldValue[10])
							//	{
							//		sNextQueue = "Validation";
							//		WriteLog("Warning", "CNPJ Prest: " + sFieldValue[5] + " CNPJ Tom: " + sFieldValue[10]);
							//	}

							//	Directory.CreateDirectory(sFolder.Replace("vOCR_1", sNextQueue));
							//	File.Move(files[0], files[0].Replace("vOCR_1", sNextQueue));
							//	UpdateBatchWPriority("Ready", lblBatchID.Text, sNextQueue, sBatchMessage, 1);

							//	try
							//	{
							//		sFolder = strSharedFolder + @"\" + "vOCR_1" + @"\" + lblBatchID.Text;
							//		System.IO.DirectoryInfo di = new DirectoryInfo(sFolder);

							//		foreach (FileInfo file in di.GetFiles())//for to delete thumbs files (hidden file)
							//		{
							//			file.Delete();
							//		}
							//		System.IO.Directory.Delete(sFolder, true);
							//	}
							//	catch (Exception ex)
							//	{
							//		UpdateBatch("Error", lblBatchID.Text, "OCR", ex.ToString(), 0);
							//	}
							//}
							//else
							//{

							sNextQueue = "Validation";


							if (sFieldValue[5] == sFieldValue[10])
							{
								sNextQueue = "Validation";
								WriteLog("Warining", "CNPJ Prest: " + sFieldValue[5] + " CNPJ Tom: " + sFieldValue[10]);
							}

							Directory.CreateDirectory(sFolder.Replace("vOCR_1", sNextQueue));
							File.Move(files[0], files[0].Replace("vOCR_1", sNextQueue));
							UpdateBatchWPriority("Ready", lblBatchID.Text, sNextQueue, sBatchMessage, 1);

							try
							{
								sFolder = strSharedFolder + @"\" + "vOCR_1" + @"\" + lblBatchID.Text;
								System.IO.DirectoryInfo di = new DirectoryInfo(sFolder);

								foreach (FileInfo file in di.GetFiles())//for to delete thumbs files (hidden file)
								{
									file.Delete();
								}
								System.IO.Directory.Delete(sFolder, true);
							}
							catch (Exception ex)
							{
								UpdateBatch("Error", lblBatchID.Text, "OCR", ex.ToString(), 0);
							}
							//sBatchMessage = "Generating vOCR_1 Full and Checking Rules";

							//File.Move(files[0], svOCR_1In + lblBatchID.Text + ".pdf");
							//UpdateBatch("In Progress", lblBatchID.Text, "vOCR_1", sBatchMessage, 1);






							//}
						}
						catch (Exception ex)
						{
							UpdateBatch("Error", lblBatchID.Text, sNextQueue, ex.ToString(), 0);
							iRet = 1;
						}
					}
					//}









					//



					lblAction.Text = "Numero NF: " + sFieldValue[1] + " Data: " + sFieldValue[2] + " Chave: " + sFieldValue[3] + " CNPJ_Prest: " + sFieldValue[5] + " CNPJ:_Tom: " + sFieldValue[10] + " Codigo_Servico: " + sFieldValue[26];


					this.Refresh();
					Application.DoEvents();


				}
				else
				{
					WriteLog("Error", response.StatusCode.ToString());
				}
			}
			catch (Exception ex)
			{
				WriteLog("Error", ex.ToString());
				lblAction.Text = ex.ToString();
			}


			return iRet;
		}