import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


class EmailHandler:
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY environment variable is not set")
        # instantiate once
        self.client = SendGridAPIClient(self.api_key)

    def send_email(
        self, to_email: str, from_email: str, subject: str, content: str
    ) -> None:
        """
        Synchronously send an email via SendGrid.
        Raises on failure.
        """
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=content,
        )
        try:
            response = self.client.send(message)
            # Optional: log or inspect the response if needed
            print(f"[SendGrid] {response.status_code}")
        except Exception as err:
            # You could wrap this in a custom exception if you like
            raise RuntimeError(f"SendGrid send failed: {err}")
