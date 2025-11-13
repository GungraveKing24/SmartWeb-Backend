from fastapi import Depends, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from config import SessionLocal
from datetime import datetime, timedelta, timezone
from model.models import Usuarios, AuthToken
from config import SECRET_KEY

import jwt

security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 

from datetime import datetime, timedelta
import jwt
from config import SECRET_KEY

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=2)):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token_str = credentials.credentials

    try:
        payload = jwt.decode(token_str, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        user_name = payload.get("name")
        user_role = payload.get("rol")

        if user_id is None or user_role is None:
            raise HTTPException(status_code=401, detail="Token inválido")

        # ✅ Verificar si el token existe y no está revocado
        token_db = db.query(AuthToken).filter(
            AuthToken.jwt_token == token_str,
            AuthToken.revocado == False
        ).first()

        if not token_db:
            raise HTTPException(status_code=401, detail="Token revocado o no válido")

        # Buscar usuario
        user = db.query(Usuarios).filter(Usuarios.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")

        user.role_name = user_role
        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    
def verify_token_ws(token: str):
    if not token:
        raise jwt.PyJWTError("Missing token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms="HS256")
        return type("User", (), {"id": payload.get("sub")})
    except jwt.PyJWTError:
        raise