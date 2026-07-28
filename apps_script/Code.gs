/**
 * Este é o `doPost` que já existe na planilha (recebe o POST do sistema
 * externo e grava a linha). A única mudança é a chamada a
 * `sendToWebhook_(data)` logo depois do `appendRow` — dispara o envio do
 * template de forma síncrona ao mesmo tempo que a linha é gravada, sem
 * depender de nenhum gatilho (onEdit/onChange/onFormSubmit), que não
 * disparam de forma confiável quando a escrita vem de fora via API.
 *
 * Configure em Configurações do projeto > Propriedades do script:
 *   WEBHOOK_URL    -> URL pública do serviço (ex: https://seu-dominio/sheet-webhook)
 *   WEBHOOK_SECRET -> mesmo valor de WEBHOOK_SHARED_SECRET no .env do container
 */
function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);
  sheet.appendRow([
    data.data_envio,
    data.nome,
    data.email,
    data.whatsapp,
    data.faturamento,
    data.perfil,
    data.decisao
  ]);

  sendToWebhook_(data, sheet.getLastRow());

  return ContentService.createTextOutput(JSON.stringify({status: "ok"}))
    .setMimeType(ContentService.MimeType.JSON);
}

function sendToWebhook_(data, rowNumber) {
  var props = PropertiesService.getScriptProperties();
  var webhookUrl = props.getProperty('WEBHOOK_URL');
  var webhookSecret = props.getProperty('WEBHOOK_SECRET');

  if (!webhookUrl || !webhookSecret) {
    Logger.log('WEBHOOK_URL ou WEBHOOK_SECRET não configurados em Script Properties.');
    return;
  }

  var payload = {
    row: rowNumber,
    nome: data.nome,
    email: data.email,
    whatsapp: data.whatsapp,
    faturamento: data.faturamento,
    perfil: data.perfil,
    decisao: data.decisao
  };

  var options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    headers: {
      'X-Webhook-Secret': webhookSecret
    },
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch(webhookUrl, options);
    Logger.log(
      'Webhook chamado para linha %s: HTTP %s - %s',
      rowNumber,
      response.getResponseCode(),
      response.getContentText()
    );
  } catch (err) {
    // Não deixamos uma falha no webhook derrubar o doPost original —
    // a linha já foi gravada na planilha independente disso.
    Logger.log('Erro ao chamar o webhook: %s', err);
  }
}
