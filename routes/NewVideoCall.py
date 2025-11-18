from functools import cached_property
from os import name
from typing import ChainMap
from fastapi import APIRouter, Depends, HTTPException
from model.models import CalidadVideo, Cursos, Inscritos_Curso, Notificaciones, Participantes_Sesion_V, RoleLlamada, Roles, Sesiones_Virtuales, TipoNotificacion, Usuarios
from pydantic import BaseModel
from getstream import Stream
from getstream.models import UserRequest
from getstream.models import CallRequest
from config import STREAM_API_KEY, STREAM_API_SECRET, STREAM_BASE_URL, SessionLocal
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

from services.jwt import verify_token

router = APIRouter(prefix="/hope", tags=["hope"])

client = Stream(api_key=STREAM_API_KEY, api_secret=STREAM_API_SECRET)

class CallCreate(BaseModel):
    curso_id: int
    titulo: str
    descripcion: str
    hora_inicio: datetime
    hora_fin: datetime
    origen: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/createCall")
async def create_call(Info: CallCreate, current=Depends(verify_token), db:Session = Depends(get_db)):
    if current.role_name != "Profesor":
        raise HTTPException(status_code=403, detail="No tienes permisos para crear llamadas")

# 🔍 Verificar si el profesor tiene sesiones que se cruzan
    conflicto = db.query(Sesiones_Virtuales).filter(
        Sesiones_Virtuales.id_curso.in_(
            db.query(Cursos.id).filter(Cursos.profesor_id == current.id)
        ),
        Sesiones_Virtuales.hora_inicio < Info.hora_fin,
        Sesiones_Virtuales.hora_fin > Info.hora_inicio
    ).first()

    if conflicto:
        raise HTTPException(
            status_code=400,
            detail=f"Ya tienes una sesión en ese horario: {conflicto.titulo} "
                   f"({conflicto.hora_inicio} → {conflicto.hora_fin})"
        )

    integrantes = db.query(Inscritos_Curso).filter(
        Inscritos_Curso.id_curso == Info.curso_id,
        Inscritos_Curso.estado_invitacion == "Aceptada"
    ).all()

    members = [{"user_id": str(current.id), "role": "admin"}]
    for ins in integrantes:
        members.append({"user_id": str(ins.id_estudiante), "role": "user"})

    # Registrar usuarios en GetStream
    for m in members:
        db_user = db.query(Usuarios).filter(Usuarios.id == int(m["user_id"])).first()
        if db_user:
            client.upsert_users(UserRequest(id=str(db_user.id), name=f"{db_user.nombre} {db_user.apellido}"))

    enlace = uuid.uuid4()

    call = client.video.call("default", enlace)
    call.create(
        data=CallRequest(
            created_by_id=str(current.id),
            members=members
        )
    )

    hora_inicio_naive = Info.hora_inicio.replace(tzinfo=None) if Info.hora_inicio.tzinfo else Info.hora_inicio
    hora_fin_naive = Info.hora_fin.replace(tzinfo=None) if Info.hora_fin.tzinfo else Info.hora_fin

    new_session=Sesiones_Virtuales(
        id_curso=Info.curso_id,
        titulo=Info.titulo,
        descripcion=Info.descripcion,
        hora_inicio=hora_inicio_naive,
        hora_fin=hora_fin_naive,
        enlace_llamada=f"{Info.origen}/call/{enlace}/{Info.curso_id}",
        calidad_video=CalidadVideo.p4K,
        grabacion_url=Info.origen,
    )

    db.add(new_session)
    db.commit()
    db.refresh(new_session)  # 👈 Esto actualiza el objeto con los datos reales en DB

    # 🔥 Registrar a todos los participantes en la tabla Participantes_Sesion_V
    participantes = []
    notificaciones = []

    # Agregar al profesor como HOST
    participantes.append(
        Participantes_Sesion_V(
            id_sesion=new_session.id_sesion,
            id_usuario=current.id,
            hora_unido=datetime.now().replace(tzinfo=None),
            role_llamada=RoleLlamada.HOST
        )
    )

    # Agregar a todos los alumnos inscritos
    for ins in integrantes:
        participante = Participantes_Sesion_V(
            id_sesion=new_session.id_sesion,
            id_usuario=ins.id_estudiante,
            hora_unido=None,  # Se actualizará cuando realmente se unan
            role_llamada=RoleLlamada.PARTICIPANTE
        )
        participantes.append(participante)

    db.add_all(participantes)
    db.commit()

    for ins in integrantes:
        if ins.id_estudiante != current.id: #evitamos enviar notificacion al profesor
            new_notif = Notificaciones(
                usuario_id=ins.id_estudiante,
                titulo="Nueva sesión",
                mensaje=f"Tu profesor: {current.nombre} {current.apellido} ha creado una nueva sesión",
                tipo=TipoNotificacion.EN_APP
            )
            notificaciones.append(new_notif)

    db.add_all(notificaciones)
    db.commit()

    return {
        "message": "Sesión creada exitosamente",
        "enlace_llamada": new_session.enlace_llamada,
        "miembros": [
            {
                "nombre": f"{db.query(Usuarios).get(p.id_usuario).nombre} {db.query(Usuarios).get(p.id_usuario).apellido}"
            }
            for p in participantes
        ]
    }

@router.post("/joinCall")
async def join_call(curso_id: int, current=Depends(verify_token), db:Session = Depends(get_db)):
    miembro = db.query(Inscritos_Curso).filter(
        Inscritos_Curso.id_curso == curso_id,
        Inscritos_Curso.id_estudiante == current.id
    ).first()

    profesor = (
        db.query(Usuarios)
        .join(Roles)
        .filter(Usuarios.id == current.id, Roles.nombre_rol == "Profesor")
        .first()
    )

    if not miembro and not profesor:
        raise HTTPException(status_code=403, detail="No perteneces a este curso")

     # Crear el token de GetStream
    client.upsert_users(UserRequest(id=str(current.id), name=f"{current.nombre} {current.apellido}"))
    user_token = client.create_token(user_id=str(current.id))

    return {
        "authorized": True,
        "getStreamToken": user_token
    }
