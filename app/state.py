import sqlite3
from pathlib import Path


class SentStore:
    """Guarda quais números já receberam o template, pra não duplicar o envio
    quando a mesma linha é editada de novo ou o número se repete em outra linha."""

    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sent_templates (
                    phone TEXT PRIMARY KEY,
                    sheet_name TEXT NOT NULL,
                    row_number INTEGER NOT NULL,
                    message_id TEXT,
                    sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def already_sent(self, phone: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM sent_templates WHERE phone = ?", (phone,)
            ).fetchone()
            return row is not None

    def mark_sent(
        self,
        phone: str,
        sheet_name: str,
        row_number: int,
        message_id: str | None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sent_templates (phone, sheet_name, row_number, message_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(phone) DO NOTHING
                """,
                (phone, sheet_name, row_number, message_id),
            )
