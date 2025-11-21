from datetime import datetime, timedelta, timezone
from config import SessionLocal
from model.models import Cursos, RoleLlamada, Usuarios, Sesiones_Virtuales, Participantes_Sesion_V
from schemas.s_cursos import CursoCreate 
from services.jwt import verify_token
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from utils.time import remove_tz, now_naive

router = APIRouter(tags=["Profesor"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Obtener los cursos de un profesor (activos e inactivos)
@router.get("/courses/active/")
async def get_active_courses(current=Depends(verify_token), db: Session = Depends(get_db)):
    if current.role_name != "Profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    return db.query(Cursos).filter(Cursos.profesor_id == current.id).all()

@router.get("/courses/active/only")
async def get_only_active_courses(current=Depends(verify_token), db: Session = Depends(get_db)):
    if current.role_name != "Profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    return db.query(Cursos).filter(
        (Cursos.profesor_id == current.id) &
        (Cursos.estado_curso == "Activo")
    ).all()

# Obtener la cantidad de cursos activos de 1 profesor
@router.get("/courses/active/number")
async def get_active_courses_number(current=Depends(verify_token), db: Session = Depends(get_db)):
    if current.role_name != "Profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    courses_count = db.query(Cursos).filter(Cursos.profesor_id == current.id).all()

    return len(courses_count)

# Crear curso
@router.post("/create/course")
async def create_course(course: CursoCreate, current_user: Usuarios = Depends(verify_token), db: Session = Depends(get_db)):
    if current_user.role_name != "Profesor":
        raise HTTPException(status_code=403, detail="No tienes los permisos requeridos")

    existing_course = db.query(Cursos).filter(
        (Cursos.profesor_id == current_user.id) & (Cursos.titulo == course.titulo)
    ).first()
    if existing_course:
        raise HTTPException(status_code=400, detail="No se puede repetir nombre de curso")

    cursos_count = db.query(Cursos).filter(Cursos.profesor_id == current_user.id).count()
    
    if cursos_count >= current_user.max_cursos:
        raise HTTPException(
            status_code=400,
            detail=f"No puedes crear más de {current_user.max_cursos} cursos"
        )
    
    new_course = Cursos(
        titulo=course.titulo,
        descripcion=course.descripcion,
        profesor_id=current_user.id,
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)  # 👈 Esto actualiza el objeto con los datos reales en DB

    return {
        "message": "Curso creado exitosamente",
        "curso": {
            "id": new_course.id,
            "titulo": new_course.titulo,
            "descripcion": new_course.descripcion,
            "estado_curso": new_course.estado_curso,
            "profesor_id": new_course.profesor_id,
            "creacion_curso": new_course.creacion_curso
        },
    }

# Desactivar curso
@router.put("/deactivate/course/{course_id}")
async def deactivate_course(course_id: int, current_user: Usuarios = Depends(verify_token), db: Session = Depends(get_db)):
    if current_user.role_name != "Profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    course = db.query(Cursos).filter(Cursos.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    
    course.estado_curso = "Inactivo"
    db.commit()
    
    return {"message": "Curso desactivado exitosamente"}

# Activar curso
@router.put("/activate/course/{course_id}")
async def activate_course(course_id: int, current_user: Usuarios = Depends(verify_token), db: Session = Depends(get_db)):
    if current_user.role_name != "Profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    course = db.query(Cursos).filter(Cursos.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    
    course.estado_curso = "Activo"
    db.commit()
    
    return {"message": "Curso Activado exitosamente"}

# Participantes de la llamada
@router.get("/participants/call/{sesion_id}")
async def participant_call(sesion_id: int, current_user: Usuarios = Depends(verify_token), db: Session = Depends(get_db)):
    if current_user.role_name != "Profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    participantes = (
        db.query(Participantes_Sesion_V)
        .filter(
            Participantes_Sesion_V.id_sesion == sesion_id,
            Participantes_Sesion_V.role_llamada != RoleLlamada.HOST
        )
        .all()
    )

    if not participantes:
        return {"message": "No hay participantes registrados (excepto el HOST) en esta sesión"}

    resultado = []
    for p in participantes:
        usuario = db.query(Usuarios).filter(Usuarios.id == p.id_usuario).first()
        if usuario:
            resultado.append({
                "id_usuario": usuario.id,
                "nombre": f"{usuario.nombre} {usuario.apellido}",
                "email": usuario.email
            })
    
    return {"participantes": resultado}

# Calendario de conferencias
@router.get("/calendar/{professor_id}")
async def get_calendar(professor_id: int, current=Depends(verify_token), db: Session = Depends(get_db)):
    if current.role_name != "Profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    # Verificar que el profesor logueado sea el mismo del parámetro
    if current.id != professor_id:
        raise HTTPException(status_code=403, detail="No puedes ver el calendario de otro profesor")

    # Obtener los cursos dictados por el profesor
    cursos = db.query(Cursos).filter(Cursos.profesor_id == professor_id).all()
    if not cursos:
        raise HTTPException(status_code=404, detail="No tienes cursos asignados")

    cursos_ids = [c.id for c in cursos]

    # 🗓 Calcular el rango de la semana actual (lunes a domingo)
    today = datetime.now().replace(tzinfo=None)
    start_of_week = today - timedelta(days=today.weekday())  # lunes
    end_of_week = start_of_week + timedelta(days=6)          # domingo

    # Buscar sesiones usando fechas sin timezone
    sesiones = db.query(Sesiones_Virtuales).filter(
        Sesiones_Virtuales.id_curso.in_(cursos_ids),
        Sesiones_Virtuales.hora_inicio <= end_of_week,    # ← Usar fechas sin timezone
        Sesiones_Virtuales.hora_fin >= start_of_week      # ← Usar fechas sin timezone
    ).order_by(Sesiones_Virtuales.hora_inicio.asc()).all()

    if not sesiones:
        return {"message": "No hay sesiones programadas"}

    calendario = []
    
    now = now_naive()

    for sesion in sesiones:
        # Contar participantes (si existen)
        participantes_count = db.query(Participantes_Sesion_V).filter(
            (Participantes_Sesion_V.id_sesion == sesion.id_sesion) &
            (Participantes_Sesion_V.role_llamada == RoleLlamada.PARTICIPANTE)
        ).count()

        # Buscar título del curso
        curso = db.query(Cursos).filter(Cursos.id == sesion.id_curso).first()

        # 🕒 Determinar estado de la sesión
        if sesion.hora_fin < now:
            estado = "concluida"
        elif sesion.hora_inicio <= now <= sesion.hora_fin:
            estado = "en_curso"
        else:
            estado = "futura"
            
        calendario.append({
            "curso": curso.titulo,
            "sesion": sesion.titulo,
            "descripcion": sesion.descripcion,
            "hora_inicio": remove_tz(sesion.hora_inicio),
            "hora_fin": remove_tz(sesion.hora_fin),
            "enlace_llamada": sesion.enlace_llamada,
            "calidad_video": sesion.calidad_video.value if sesion.calidad_video else None,
            "participantes": participantes_count,
            "sesion_id": sesion.id_sesion,
            "estado": estado
        })

    return {
        "profesor": current.nombre, 
        "total_sesiones": len(calendario), 
        "calendario": calendario, 
        "start_week": start_of_week, 
        "end_of_week": end_of_week,
        "now": today  # ← Ya sin UTC
    }

@router.get("/courses/{course_id}/sessions")
async def get_course_sessions(course_id: int, current=Depends(verify_token), db: Session = Depends(get_db)):
    # Validar si el curso existe
    curso = db.query(Cursos).filter(Cursos.id == course_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Verificar permisos (solo Profesor o Estudiante del curso)
    if current.role_name not in ["Profesor", "Estudiante"]:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    # Si es estudiante, verificar que esté inscrito
    if current.role_name == "Estudiante":
        inscripcion = db.query(Cursos).join(Cursos.inscritos).filter(
            Cursos.id == course_id,
            Cursos.inscritos.any(id_estudiante=current.id)
        ).first()
        if not inscripcion:
            raise HTTPException(status_code=403, detail="No estás inscrito en este curso")

    # Obtener todas las sesiones del curso
    sesiones = db.query(Sesiones_Virtuales).filter(
        Sesiones_Virtuales.id_curso == course_id
    ).order_by(Sesiones_Virtuales.hora_inicio.asc()).all()

    if not sesiones:
        return {"message": "No hay sesiones programadas para este curso"}

    now = now_naive()
    sesiones_data = []

    for sesion in sesiones:
        # Calcular estado actual
        if sesion.hora_fin and sesion.hora_fin < now:
            estado = "concluida"
        elif sesion.hora_inicio <= now <= sesion.hora_fin:
            estado = "en_curso"
        else:
            estado = "futura"

        # Contar participantes (solo PARTICIPANTES, no HOST)
        participantes_count = db.query(Participantes_Sesion_V).filter(
            (Participantes_Sesion_V.id_sesion == sesion.id_sesion) &
            (Participantes_Sesion_V.role_llamada == RoleLlamada.PARTICIPANTE)
        ).count()

        sesiones_data.append({
            "sesion_id": sesion.id_sesion,
            "titulo": sesion.titulo,
            "descripcion": sesion.descripcion,
            "hora_inicio": remove_tz(sesion.hora_inicio),
            "hora_fin": remove_tz(sesion.hora_fin),
            "enlace_llamada": sesion.enlace_llamada,
            "calidad_video": sesion.calidad_video.value if sesion.calidad_video else None,
            "estado": estado,
            "participantes": participantes_count
        })

    return {
        "curso": curso.titulo,
        "profesor": f"{curso.profesor.nombre} {curso.profesor.apellido}",
        "total_sesiones": len(sesiones_data),
        "sesiones": sesiones_data
    }
