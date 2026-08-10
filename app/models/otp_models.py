from pydantic import BaseModel

class OTPRequest(BaseModel):
    email: str


class OTPResponse(BaseModel):
    message: str
    email: str
