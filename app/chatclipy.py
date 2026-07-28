import requests


class ChatclipyClient:
    def __init__(self, base_url: str, api_token: str):
        self._base_url = base_url
        self._api_token = api_token

    def send_template(
        self,
        *,
        whatsapp_id: int,
        template_name: str,
        language_code: str,
        parameters: list[str],
        contact_name: str,
        contact_number: str,
        contact_email: str | None = None,
    ) -> dict:
        contact: dict[str, str] = {"name": contact_name, "number": contact_number}
        if contact_email:
            contact["email"] = contact_email

        payload = {
            "whatsappId": whatsapp_id,
            "templateName": template_name,
            "languageCode": language_code,
            "parameters": parameters,
            "contact": contact,
        }

        response = requests.post(
            f"{self._base_url}/public-api/templates/send",
            json=payload,
            headers={"Authorization": f"Bearer {self._api_token}"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
