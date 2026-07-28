from google.oauth2 import service_account
from googleapiclient.discovery import build

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Índices das colunas na planilha (A=0, B=1, ...)
COL_NOME = 1
COL_EMAIL = 2
COL_WHATSAPP = 3


class SheetsClient:
    def __init__(self, service_account_json_path: str, spreadsheet_id: str):
        credentials = service_account.Credentials.from_service_account_file(
            service_account_json_path, scopes=_SCOPES
        )
        self._service = build(
            "sheets", "v4", credentials=credentials, cache_discovery=False
        )
        self._spreadsheet_id = spreadsheet_id

    def get_row(self, sheet_name: str, row_number: int) -> list[str]:
        """Relê a linha diretamente da API do Sheets — nunca confia no payload
        do webhook como fonte de verdade, pra evitar condições de corrida com
        edições parciais."""
        range_ = f"{sheet_name}!A{row_number}:G{row_number}"
        result = (
            self._service.spreadsheets()
            .values()
            .get(spreadsheetId=self._spreadsheet_id, range=range_)
            .execute()
        )
        values = result.get("values", [])
        return values[0] if values else []
