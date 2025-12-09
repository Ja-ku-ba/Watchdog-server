from pydantic import BaseModel, EmailStr, validator


class BaseUser(BaseModel):
    email: EmailStr
    username: str

    @validator('email', pre=True)
    def clean_email(cls, v):
        return str(v).strip().lower()
    
    @validator('username', pre=True)  
    def clean_username(cls, v):
        return str(v).replace(' ', '').lower()


class UserCreate(BaseUser):
    password: str

    @validator('password', pre=True)
    def clean_password(cls, v):
        return str(v).strip()


# class UserWithJwtToken(BaseUser):
#     access_token: str | None
#     refresh_token: str


class UserToken(BaseModel):
    access_token: str | None
    refresh_token: str


class UserRefreshToken(BaseModel):
    refresh_token: str | None


class UserAccessToken(BaseModel):
    access_token: str | None


class UserNotificationToken(BaseModel):
    notification_token: str



class UserAuthenticate(BaseModel):
    email: str
    password: str

    @validator('email', pre=True)
    def clean_email(cls, v):
        return str(v).strip().lower()
    
    @validator('password', pre=True)
    def clean_password(cls, v):
        return str(v).strip()


class UserDataFromToken(BaseModel):
    email: str = None
    scopes: list[str] = []


class UserNotificationSettings(BaseModel):
    notification_new_video: bool
    notification_intruder: bool
    notification_friend: bool



class VerifiedUsers(BaseModel):
    name: str
    files_counter: int
    image_hashes: list[str] = []


class AddVerifiedUser(BaseModel):
    name: str
