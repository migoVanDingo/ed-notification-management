from fastapi import APIRouter, Depends, Request
from app.api.handler.mailgun_handler import MailgunEmailHandler
from platform_common.logging.logging import get_logger
from platform_common.utils.service_response import ServiceResponse
from app.api.handler.email_handler import EmailHandler
from pydantic import BaseModel, EmailStr

router = APIRouter()
logger = get_logger("notification")


class Email(BaseModel):
    to_email: EmailStr
    from_email: EmailStr
    subject: str
    content: str


@router.post("/")
async def send_notification(
    payload: Email,
    handler: EmailHandler = Depends(EmailHandler),
) -> ServiceResponse:
    # payload is a validated Email instance
    return handler.send_email(
        to_email=payload.to_email,
        from_email=payload.from_email,
        subject=payload.subject,
        content=payload.content,
    )
    # return a ServiceResponse (make sure ServiceResponse is a BaseModel!)


@router.post("/mailgun")
async def send_via_mailgun(
    payload: Email,
    handler: MailgunEmailHandler = Depends(MailgunEmailHandler),
) -> ServiceResponse:
    try:
        handler.send_email(
            to_email=payload.to_email,
            from_email=payload.from_email,
            subject=payload.subject,
            content=payload.content,
        )
        # success path → default ServiceResponse is HTTP 200
        return ServiceResponse(message="Email sent via Mailgun")
    except Exception as e:
        # failure path → still HTTP 200, but success=False in JSON
        return ServiceResponse(success=False, message=str(e))
