from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config import SessionLocal
from model.models import Usuarios, Roles, Cursos, Inscritos_Curso
from services.jwt import verify_token
from services.email import send_email

router = APIRouter(prefix="/administrador", tags=["Administrador"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 

from services.jwt import verify_token

# Obtener todos los usuarios menos los administradores
@router.get("/users")
async def get_users(current=Depends(verify_token), db: Session = Depends(get_db)):
    if current.role_name != "Administrador":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    usuarios = db.query(Usuarios).join(Roles).filter(Roles.nombre_rol != "Administrador").all()

    return [
        {
            "id": u.id,
            "nombre": f"{u.nombre} {u.apellido}",
            "email": u.email,
            "rol": u.rol.nombre_rol,
            "status": u.status.value
        }
        for u in usuarios
    ]

# Obtener los profesores no aceptados
@router.get("/profesores")
async def get_profesores(current=Depends(verify_token), db: Session = Depends(get_db)):
    if current.role_name != "Administrador":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    profesores = db.query(Usuarios).join(Roles).filter(Roles.nombre_rol == "Profesor", Usuarios.confirmado == False).all()

    return [
        {
            "id": p.id,
            "nombre": f"{p.nombre} {p.apellido}",
            "email": p.email,
            "rol": p.rol.nombre_rol,
            "status": p.status.value,
            "cedula": p.profesor_cedula,
            "instituto": p.profesor_institucion,
            "fecha": p.creacion_cuenta,
            "motivacion": p.motivacion
        }
        for p in profesores
    ]

# Aprobar profesores pendientes
@router.put("/approve-profesor/{user_id}")
async def approve_profesor(
    user_id: int,
    current=Depends(verify_token),
    db: Session = Depends(get_db)
):
    if current.role_name != "Administrador":
        raise HTTPException(status_code=403, detail="Solo los administradores pueden aprobar profesores")

    profesor = db.query(Usuarios).join(Roles).filter(
        Usuarios.id == user_id, Roles.nombre_rol == "Profesor"
    ).first()

    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    profesor.confirmado = True
    profesor.status = "Activo"
    profesor.token_activacion = None
    db.commit()

    # Enviar correo al profesor
    await send_email(
        to=profesor.email,
        subject="Cuenta aprobada",
        body=f"Hola {profesor.nombre}, tu cuenta de profesor ha sido aprobada."
    )

    return {"message": "Profesor aprobado y notificado"}

# Denegar profesores pendientes
@router.put("/deny-profesor/{user_id}")
async def deny_profesor(
    user_id: int,
    current=Depends(verify_token),
    db: Session = Depends(get_db)
):
    if current.role_name != "Administrador":
        raise HTTPException(status_code=403, detail="Solo los administradores pueden denegar profesores")

    profesor = db.query(Usuarios).join(Roles).filter(
        Usuarios.id == user_id, Roles.nombre_rol == "Profesor"
    ).first()

    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    profesor.confirmado = False
    profesor.status = "Inactivo"
    profesor.token_activacion = None
    db.commit()

    # Enviar correo al profesor
    await send_email(
        to=profesor.email,
        subject="Cuenta denegada",
        body=f"Hola {profesor.nombre}, tu cuenta de profesor ha sido denegada."
)

# Cambiar el rol de un usuario
@router.put("/users/{user_id}/role")
async def change_user_role(user_id: int, new_role: str, current=Depends(verify_token), db: Session = Depends(get_db)):
    if current.role_name != "Administrador":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    if not new_role:
        raise HTTPException(status_code=400, detail="Rol requerido")
    
    user = db.query(Usuarios).filter(Usuarios.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    role = db.query(Roles).filter(Roles.nombre_rol == new_role).first()
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    user.role = role.id
    db.commit()
    return {"message": "Rol cambiado correctamente"}

# Desactivar un usuario
@router.post("/users/{user_id}")
async def deactivate_user(
        user_id: int,
        current=Depends(verify_token),
        db: Session = Depends(get_db)
    ):
    if current.role_name != "Administrador":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    user = db.query(Usuarios).filter(Usuarios.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.status = "Inactivo"
    db.commit()
    
    return {"message": "Usuario eliminado correctamente"}

# Obtener todos los cursos con información detallada
@router.get("/all/cursos")
async def get_courses(current=Depends(verify_token), db: Session = Depends(get_db)):
    if current.role_name != "Administrador":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    cursos = db.query(Cursos).all()
    if not cursos:
        return []

    data = []
    for curso in cursos:
        profesor = db.query(Usuarios).filter(Usuarios.id == curso.profesor_id).first()

        # Contar estudiantes inscritos con invitación aceptada
        inscritos_count = (
            db.query(Inscritos_Curso)
            .filter(
                Inscritos_Curso.id_curso == curso.id,
                Inscritos_Curso.estado_invitacion == "Aceptada"
            )
            .count()
        )

        data.append({
            "id": curso.id,
            "titulo": curso.titulo,
            "descripcion": curso.descripcion,
            "creacion_curso": curso.creacion_curso,
            "estado_curso": curso.estado_curso.value if curso.estado_curso else None,
            "profesor": f"{profesor.nombre} {profesor.apellido}" if profesor else "—",
            "estudiantes": inscritos_count
        })

    return data
