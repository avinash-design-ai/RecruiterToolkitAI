from pydantic import BaseModel


class LinkedInRequest(BaseModel):

    company: str

    location: str

    max_profiles: int = 250
