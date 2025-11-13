
from datetime import datetime
from pydantic import BaseModel

class CursoCreate(BaseModel):
    titulo: str
    descripcion: str

class CursoResponse(BaseModel):
    id: int
    titulo: str
    descripcion: str
    profesor_id: int
    creacion_curso: datetime

    class Config:
        from_attributes = True

