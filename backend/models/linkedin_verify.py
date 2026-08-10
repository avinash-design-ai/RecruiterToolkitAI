from pydantic import BaseModel


class LinkedInVerifyRequest(BaseModel):
    session_id: str
    verification_code: str
