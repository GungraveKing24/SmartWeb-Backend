from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UsuarioCreate(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    password: str
    role: str  # e.g., "Estudiante", "Profesor"
    motivacion: Optional[str] = None
    profesor_institucion: Optional[str] = None
    profesor_cedula: Optional[int] = None

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class UsuarioResponse(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    role: str
    creacion_cuenta: datetime

    class Config:
        from_attributes = True

