import logging

import requests as requests_lib
from fastapi import FastAPI, Header, HTTPException, Request

from .chatclipy import ChatclipyClient
from .config import load_settings
from .phone import normalize_br_phone
from .state import SentStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sheet_webhook")

settings = load_settings()
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
    row_number = body.get("row")
    nome = (body.get("nome") or "").strip()
    email = (body.get("email") or "").strip()
    whatsapp_raw = (body.get("whatsapp") or "").strip()

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

    sent_store.mark_sent(phone, str(row_number), result.get("messageId"))
    logger.info("Template enviado para %s (linha %s): %s", phone, row_number, result)
    return {"status": "sent", "result": result}
