import logging

import requests as requests_lib
from fastapi import FastAPI, Header, HTTPException, Request

from .chatclipy import ChatclipyClient
from .config import load_settings
from .phone import normalize_br_phone
from .sheets import COL_EMAIL, COL_NOME, COL_WHATSAPP, SheetsClient
from .state import SentStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sheet_webhook")

settings = load_settings()
sheets_client = SheetsClient(settings.google_service_account_json, settings.spreadsheet_id)
chatclipy_client = ChatclipyClient(settings.chatclipy_base_url, settings.chatclipy_api_token)
sent_store = SentStore(settings.state_db_path)

app = FastAPI(title="Sheets -> Chatclipy template webhook")


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.post("/sheet-webhook")
async def sheet_webhook(
    request: Request, x_webhook_secret: str = Header(default="")
) -> dict:
    if x_webhook_secret != settings.webhook_shared_secret:
        raise HTTPException(status_code=401, detail="invalid webhook secret")

    body = await request.json()
    sheet_name = body.get("sheetName")
    row_number = body.get("row")
    if not sheet_name or not row_number:
        raise HTTPException(status_code=400, detail="sheetName and row are required")

    row = sheets_client.get_row(sheet_name, int(row_number))
    nome = (row[COL_NOME] if len(row) > COL_NOME else "").strip()
    email = (row[COL_EMAIL] if len(row) > COL_EMAIL else "").strip()
    whatsapp_raw = (row[COL_WHATSAPP] if len(row) > COL_WHATSAPP else "").strip()

    if not nome or not whatsapp_raw:
        logger.info(
            "Linha %s incompleta, ignorando (nome=%r, whatsapp=%r)",
            row_number,
            nome,
            whatsapp_raw,
        )
        return {"status": "skipped", "reason": "incomplete_row"}

    phone = normalize_br_phone(whatsapp_raw)
    if not phone:
        logger.warning("Linha %s com telefone inválido: %r", row_number, whatsapp_raw)
        return {"status": "skipped", "reason": "invalid_phone"}

    if sent_store.already_sent(phone):
        logger.info(
            "Telefone %s já recebeu o template, ignorando linha %s", phone, row_number
        )
        return {"status": "skipped", "reason": "already_sent"}

    try:
        result = chatclipy_client.send_template(
            whatsapp_id=settings.chatclipy_whatsapp_id,
            template_name=settings.chatclipy_template_name,
            language_code=settings.chatclipy_language_code,
            parameters=[nome],
            contact_name=nome,
            contact_number=phone,
            contact_email=email or None,
        )
    except requests_lib.HTTPError as exc:
        response_text = exc.response.text if exc.response is not None else str(exc)
        logger.error(
            "Falha ao enviar template para %s (linha %s): %s",
            phone,
            row_number,
            response_text,
        )
        raise HTTPException(status_code=502, detail="chatclipy_send_failed") from exc

    sent_store.mark_sent(phone, sheet_name, int(row_number), result.get("messageId"))
    logger.info("Template enviado para %s (linha %s): %s", phone, row_number, result)
    return {"status": "sent", "result": result}
