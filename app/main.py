import logging
import secrets

import requests as requests_lib
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .admin_page import render_admin_page
from .chatclipy import ChatclipyClient
from .config import load_settings
from .phone import normalize_br_phone
from .state import SentStore
from .template_config import AVAILABLE_FIELDS, TemplateConfigStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sheet_webhook")

settings = load_settings()
chatclipy_client = ChatclipyClient(settings.chatclipy_base_url, settings.chatclipy_api_token)
sent_store = SentStore(settings.state_db_path)
template_config_store = TemplateConfigStore(
    settings.state_db_path, settings.chatclipy_template_name, ["nome"]
)

app = FastAPI(title="Sheets -> Chatclipy template webhook")
security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    valid_user = secrets.compare_digest(credentials.username, settings.admin_username)
    valid_password = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (valid_user and valid_password):
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(_: None = Depends(require_admin)) -> HTMLResponse:
    template_name, parameters = template_config_store.get()
    return HTMLResponse(render_admin_page(template_name, parameters))


@app.post("/admin", response_class=HTMLResponse)
async def admin_save(request: Request, _: None = Depends(require_admin)) -> HTMLResponse:
    form = await request.form()
    template_name = (form.get("template_name") or "").strip()
    parameters = [value for value in form.getlist("parameters") if value in AVAILABLE_FIELDS]

    if not template_name:
        existing_template_name, existing_parameters = template_config_store.get()
        return HTMLResponse(
            render_admin_page(
                existing_template_name,
                existing_parameters,
                message="Nome do template é obrigatório.",
                is_error=True,
            ),
            status_code=400,
        )

    template_config_store.save(template_name, parameters)
    return HTMLResponse(
        render_admin_page(template_name, parameters, message="Configuração salva com sucesso.")
    )


@app.post("/sheet-webhook")
async def sheet_webhook(
    request: Request, x_webhook_secret: str = Header(default="")
) -> dict:
    if x_webhook_secret != settings.webhook_shared_secret:
        raise HTTPException(status_code=401, detail="invalid webhook secret")

    body = await request.json()
    row_number = body.get("row")
    fields = {
        key: (body.get(key) or "").strip() for key in AVAILABLE_FIELDS
    }
    nome = fields["nome"]
    whatsapp_raw = fields["whatsapp"]

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

    template_name, parameter_fields = template_config_store.get()
    parameters = [fields.get(key, "") for key in parameter_fields]

    try:
        result = chatclipy_client.send_template(
            whatsapp_id=settings.chatclipy_whatsapp_id,
            template_name=template_name,
            language_code=settings.chatclipy_language_code,
            parameters=parameters,
            contact_name=nome,
            contact_number=phone,
            contact_email=fields["email"] or None,
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
