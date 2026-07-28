import json
import sqlite3
from pathlib import Path

# Campos disponíveis na planilha que podem virar parâmetro do template
# ({{1}}, {{2}}, ...). Chave = nome enviado pelo Apps Script no webhook.
AVAILABLE_FIELDS = {
    "nome": "Nome",
    "email": "E-mail",
    "whatsapp": "WhatsApp",
    "faturamento": "Faturamento",
    "perfil": "Perfil",
    "decisao": "Decisão",
}


class TemplateConfigStore:
    """Guarda o nome do template e quais campos viram parâmetros, editável
    via /admin sem precisar reiniciar o container."""

    def __init__(
        self,
        db_path: str,
        default_template_name: str,
        default_parameters: list[str],
    ):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._default_template_name = default_template_name
        self._default_parameters = default_parameters
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS template_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    template_name TEXT NOT NULL,
                    parameters TEXT NOT NULL
                )
                """
            )

    def get(self) -> tuple[str, list[str]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT template_name, parameters FROM template_config WHERE id = 1"
            ).fetchone()
        if row is None:
            return self._default_template_name, list(self._default_parameters)
        template_name, parameters_json = row
        return template_name, json.loads(parameters_json)

    def save(self, template_name: str, parameters: list[str]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO template_config (id, template_name, parameters)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    template_name = excluded.template_name,
                    parameters = excluded.parameters
                """,
                (template_name, json.dumps(parameters)),
            )
