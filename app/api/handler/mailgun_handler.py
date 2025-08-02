# mailgun_handler.py

import os, requests
from requests.exceptions import RequestException
from platform_common.logging.logging import get_logger


class MailgunEmailHandler:
    def __init__(self):
        self.api_key = os.getenv("MAILGUN_SENDING_API_KEY")
        self.domain = os.getenv("MAILGUN_DOMAIN")
        if not self.api_key or not self.domain:
            raise ValueError("MAILGUN_SENDING_API_KEY and MAILGUN_DOMAIN must be set")

        self.url = f"https://api.mailgun.net/v3/{self.domain}/messages"

    def send_email(
        self, to_email: str, from_email: str, subject: str, content: str
    ) -> None:
        try:
            logger = get_logger("mailgun")
            logger.info(f"Sending email via Mailgun to {to_email} from {from_email}")
            resp = requests.post(
                self.url,
                auth=("api", self.api_key),
                data={
                    "from": from_email,
                    "to": to_email,
                    "subject": subject,
                    "text": content,
                },
                timeout=10,
            )
            logger.info(f"Mailgun response: {resp.status_code} - {resp.text}")
            resp.raise_for_status()
        except RequestException as exc:
            # turn *any* network / HTTP error into an exception
            raise RuntimeError(f"Mailgun send failed: {exc}")
        # if we get here, it was a 200 OK
