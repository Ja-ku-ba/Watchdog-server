# ===================================================================
# KOMPLETNA IMPLEMENTACJA OAuth2PasswordBearer
# ===================================================================

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
import os

app = FastAPI(title="OAuth2 Authentication Example")

# ===================================================================
# KONFIGURACJA
# ===================================================================

SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme - to jest KLUCZOWE!
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",  # URL gdzie klienci mogą pobrać token
    scopes={
        "read": "Read access",
        "write": "Write access", 
        "admin": "Admin access"
    }
)

# ===================================================================
# MODELE PYDANTIC
# ===================================================================

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str = None
    scopes: list[str] = []

class User(BaseModel):
    id: int
    username: str
    email: str
    active: bool = True
    scopes: list[str] = []

class UserInDB(User):
    hashed_password: str

# ===================================================================
# FAKE DATABASE (w rzeczywistości użyj SQLAlchemy)
# ===================================================================

fake_users_db = {
    "admin": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "active": True,
        "scopes": ["read", "write", "admin"]
    },
    "user": {
        "id": 2,
        "username": "user",
        "email": "user@example.com", 
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "active": True,
        "scopes": ["read"]
    }
}

# ===================================================================
# UTILITY FUNCTIONS
# ===================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Weryfikuj hasło"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Zahashuj hasło"""
    return pwd_context.hash(password)

def get_user(username: str) -> UserInDB:
    """Pobierz użytkownika z bazy"""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)

def authenticate_user(username: str, password: str) -> UserInDB:
    """Uwierzytelnij użytkownika"""
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Utwórz JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ===================================================================
# GŁÓWNA DEPENDENCY - get_current_user
# ===================================================================

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    KLUCZOWA DEPENDENCY!
    
    oauth2_scheme automatycznie:
    1. Wyciąga token z nagłówka "Authorization: Bearer <token>"
    2. Przekazuje go jako string (nie obiekt!)
    3. Jeśli brak tokenu → HTTP 401
    """
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Dekoduj JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
            
        # Pobierz scopes z tokenu (opcjonalnie)
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise credentials_exception
    
    # Pobierz użytkownika z bazy
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    return User(
        id=user.id,
        username=user.username,
        email=user.email,
        active=user.active,
        scopes=user.scopes
    )

# ===================================================================
# DEPENDENCY DLA AKTYWNYCH UŻYTKOWNIKÓW
# ===================================================================

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency dla aktywnych użytkowników"""
    if not current_user.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user

# ===================================================================
# DEPENDENCY DLA ADMINÓW
# ===================================================================

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Dependency dla adminów"""
    if "admin" not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

# ===================================================================
# DEPENDENCY Z SCOPE CHECKING
# ===================================================================

from fastapi.security.utils import get_authorization_scheme_param
from fastapi import Security

async def get_current_user_with_scopes(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme)
) -> User:
    """Dependency ze sprawdzaniem scopes"""
    
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, username=username)
    except jwt.InvalidTokenError:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    # Sprawdź czy user ma wymagane scopes
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    
    return User(
        id=user.id,
        username=user.username, 
        email=user.email,
        active=user.active,
        scopes=user.scopes
    )

# ===================================================================
# ENDPOINT DO LOGOWANIA (WYMAGANY!)
# ===================================================================

@app.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    KLUCZOWY ENDPOINT!
    
    OAuth2PasswordRequestForm automatycznie parsuje:
    - username
    - password
    - scopes (opcjonalnie)
    
    Content-Type: application/x-www-form-urlencoded
    """
    
    # Uwierzytelnij użytkownika
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Sprawdź wymagane scopes
    user_scopes = user.scopes
    requested_scopes = form_data.scopes
    
    # Użytkownik może otrzymać tylko scopes które ma
    granted_scopes = [scope for scope in requested_scopes if scope in user_scopes]
    
    # Utwórz token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": granted_scopes},
        expires_delta=access_token_expires,
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# ===================================================================
# ENDPOINTY Z RÓŻNYMI POZIOMAMI DOSTĘPU
# ===================================================================

@app.get("/")
async def read_root():
    """Publiczny endpoint - bez dependency"""
    return {"message": "Hello World - dostępne dla wszystkich"}

@app.get("/users/me", response_model=User)
async def read_user_me(current_user: User = Depends(get_current_active_user)):
    """Endpoint dla zalogowanych użytkowników"""
    return current_user

@app.get("/users/me/items")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    """Zwróć elementy aktualnego użytkownika"""
    return [
        {"item_id": "Foo", "owner": current_user.username},
        {"item_id": "Bar", "owner": current_user.username}
    ]

@app.get("/admin/users")
async def list_all_users(admin_user: User = Depends(get_current_admin_user)):
    """Endpoint tylko dla adminów"""
    return {"users": list(fake_users_db.keys()), "admin": admin_user.username}

# ===================================================================
# ENDPOINTY Z SCOPE CHECKING
# ===================================================================

from fastapi import Security
from fastapi.security.utils import SecurityScopes

@app.get("/items/")
async def read_items(current_user: User = Security(get_current_user_with_scopes, scopes=["read"])):
    """Wymaga scope 'read'"""
    return [{"item_id": "Foo", "owner": "Alice"}, {"item_id": "Bar", "owner": "Bob"}]

@app.post("/items/")
async def create_item(
    item: dict,
    current_user: User = Security(get_current_user_with_scopes, scopes=["write"])
):
    """Wymaga scope 'write'"""
    return {"item": item, "created_by": current_user.username}

@app.delete("/admin/reset")
async def admin_reset(
    current_user: User = Security(get_current_user_with_scopes, scopes=["admin"])
):
    """Wymaga scope 'admin'"""
    return {"message": "System reset", "by": current_user.username}

# ===================================================================
# PRZYKŁAD Z PRAWDZIWĄ BAZĄ DANYCH
# ===================================================================

"""
# dependencies/auth.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.connector import get_session
from models.user import User as UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user_from_db(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
    
    # Pobierz z prawdziwej bazy
    result = await session.execute(
        select(UserModel).filter(UserModel.username == username)
    )
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    return user

# Użycie w endpoincie:
@app.get("/profile")
async def get_profile(current_user: UserModel = Depends(get_current_user_from_db)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email
    }
"""

# ===================================================================
# JAK TESTOWAĆ W SWAGGER UI
# ===================================================================

"""
1. Idź do http://localhost:8000/docs
2. Kliknij przycisk "Authorize" (zielona ikona kłódki)
3. Wpisz:
   - username: admin
   - password: secret
   - scopes: read write admin (opcjonalnie)
4. Kliknij "Authorize"
5. Teraz wszystkie chronione endpointy będą działać!

Swagger automatycznie:
- Wysyła POST do /auth/token
- Otrzymuje access_token
- Dodaje "Authorization: Bearer <token>" do wszystkich requestów
"""

# ===================================================================
# JAK TESTOWAĆ Z CURL/POSTMAN
# ===================================================================

"""
1. Pobierz token:
curl -X POST "http://localhost:8000/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=secret&scope=read write admin"

2. Użyj tokenu:
curl -X GET "http://localhost:8000/users/me" \
     -H "Authorization: Bearer <twój_token_tutaj>"
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)