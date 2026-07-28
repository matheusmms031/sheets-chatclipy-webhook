/**
 * Instale este script vinculado à planilha (Extensões > Apps Script).
 *
 * Antes de usar, configure em Project Settings > Script Properties:
 *   WEBHOOK_URL    -> URL pública do serviço (ex: https://seu-dominio/sheet-webhook)
 *   WEBHOOK_SECRET -> mesmo valor de WEBHOOK_SHARED_SECRET no .env do container
 *
 * Depois, em Triggers (relógio na lateral), adicione um gatilho instalável:
 *   Function: onFormSubmit | Event source: From spreadsheet | Event type: On form submit
 *
 * Isso dispara sempre que uma resposta do Forms cria uma linha nova.
 */
function onFormSubmit(e) {
  var props = PropertiesService.getScriptProperties();
  var webhookUrl = props.getProperty('WEBHOOK_URL');
  var webhookSecret = props.getProperty('WEBHOOK_SECRET');

  if (!webhookUrl || !webhookSecret) {
    Logger.log('WEBHOOK_URL ou WEBHOOK_SECRET não configurados em Script Properties.');
    return;
  }

  var range = e.range;
  var sheet = range.getSheet();

  var payload = {
    sheetName: sheet.getName(),
    row: range.getRow()
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

  var response = UrlFetchApp.fetch(webhookUrl, options);
  Logger.log(
    'Webhook chamado para linha %s: HTTP %s - %s',
    range.getRow(),
    response.getResponseCode(),
    response.getContentText()
  );
}
