from pydantic import BaseModel, EmailStr, validator


class Device(BaseModel):
    device_ip: str
    device_name: str


class RegisterDevice(BaseModel):
    device_name: str
    email: EmailStr

    @validator('email', pre=True)
    def clean_email(cls, v):
        return str(v).strip().lower()
