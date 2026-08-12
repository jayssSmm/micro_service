from pydantic import BaseModel


class OTPRequest(BaseModel):
    email: str


class OTPResponse(BaseModel):
    message: str
    email: str


class VerifyOTPRequest(BaseModel):
    email: str
    otp: str


class VerifyOTPResponse(BaseModel):
    message: str
    email: str