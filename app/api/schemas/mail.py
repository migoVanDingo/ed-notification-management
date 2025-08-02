# app/api/schemas.py
from pydantic import BaseModel, EmailStr


class EmailRequest(BaseModel):
    to_email: EmailStr
    from_email: EmailStr
    subject: str
    content: str
