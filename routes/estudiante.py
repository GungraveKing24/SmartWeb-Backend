from datetime import date, datetime, timedelta
import uuid
from config import SessionLocal
from fastapi import APIRouter, Depends, HTTPException
from model.models import Inscritos_Curso, Cursos, Usuarios, Sesiones_Virtuales, Notificaciones, TipoNotificacion, EstadoNotificacion
from sqlalchemy.orm import Session
from services.jwt import verify_token
from utils.time import remove_tz, now_naive

router = APIRouter(prefix="/students", tags=["Student"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Obtener los cursos inscritos de un estudiante (activos e inactivos)
@router.get("/courses/active")
async def get_active_courses(
    current_user: Usuarios = Depends(verify_token),
    db: Session = Depends(get_db)
):
    if current_user.role_name != "Estudiante":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    # Cursos en los que el usuario está inscrito
    cursos = (
        db.query(
            Cursos.id,
            Cursos.titulo,
            Cursos.descripcion,
            Cursos.creacion_curso,
            Cursos.estado_curso,
            Usuarios.nombre.label("profesor_nombre"),
            Usuarios.apellido.label("profesor_apellido")
        )
        .join(Inscritos_Curso, Cursos.id == Inscritos_Curso.id_curso)
        .join(Usuarios, Cursos.profesor_id == Usuarios.id)
        .filter(Inscritos_Curso.id_estudiante == current_user.id)
        .all()
    )

    if not cursos:
        return []  # Devolvemos lista vacía en vez de error

    # Combinar el nombre completo del profesor
    result = [
        {
            "id": c.id,
            "titulo": c.titulo,
            "descripcion": c.descripcion,
            "estado_curso": c.estado_curso,
            "creacion_curso": c.creacion_curso,
            "profesor_id": f"{c.profesor_nombre} {c.profesor_apellido}"
        }
        for c in cursos
    ]

    return result

# Obtener los detalles de un curso
@router.get("/courses/details/{course_id}")
async def get_course_details(course_id: int, current_user: Usuarios = Depends(verify_token), db: Session = Depends(get_db)):
    if current_user.role_name != "Estudiante":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    # Obtener los detalles del curso    
    curso = db.query(Cursos).filter(Cursos.id == course_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    
    # Obtener los estudiantes inscritos si los hay
    inscritos = db.query(Inscritos_Curso).filter(Inscritos_Curso.id_curso == course_id).all()
    if not inscritos:
        raise HTTPException(status_code=404, detail="No se encontraron estudiantes inscritos")

    # Obtener el profesor del curso
    profesor = db.query(Usuarios).filter(Usuarios.id == curso.profesor_id).first()
    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    
    return {"curso": curso, "estudiantes": inscritos, "profesor": profesor}

# Inscribirse en un curso (con código de curso)
@router.post("/courses/enroll/{course_code}")
async def enroll_in_course(course_code: int, current_user: Usuarios = Depends(verify_token), db: Session = Depends(get_db)):
    if current_user.role_name != "Estudiante":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    # Verificar si el estudiante ya está inscrito en el curso
    inscripcion_existente = db.query(Inscritos_Curso).filter(
        Inscritos_Curso.id_curso == course_code,
        Inscritos_Curso.id_estudiante == current_user.id
    ).first()
    if inscripcion_existente:
        raise HTTPException(status_code=400, detail="Ya estás inscrito en este curso")

    # Verificar si el curso existe
    curso = db.query(Cursos).filter(Cursos.id == course_code).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Obtener profesor dueño del curso
    profesor_propietario = db.query(Usuarios).filter(Usuarios.id == curso.profesor_id).first()
    if not profesor_propietario:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    
    # Crear notificación para el profesor
    notificacion = Notificaciones(
        usuario_id=profesor_propietario.id,
        titulo="Nuevo estudiante inscrito",
        mensaje=f"El estudiante {current_user.nombre} {current_user.apellido} se ha inscrito en tu curso: {curso.titulo}.",
        tipo=TipoNotificacion.EN_APP,
        status=EstadoNotificacion.PENDIENTE
    )

    enlace = uuid.uuid4()

    nueva_inscripcion = Inscritos_Curso(
        id_curso=course_code,
        id_estudiante=current_user.id,
        estado_invitacion="Aceptada",
        enlace_unico=enlace 
    )
    
    db.add(nueva_inscripcion)
    db.commit()
    db.refresh(nueva_inscripcion)

    return {"message": "Registro exitoso. Verifique su correo si aplica."}

from datetime import datetime, timedelta, timezone

# Ver el calendario de conferencias
@router.get("/calendar/student/{student_id}")
async def get_calendar(student_id: int, current=Depends(verify_token), db: Session = Depends(get_db)):
    if current.role_name != "Estudiante":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    inscripciones = db.query(Inscritos_Curso).filter(
        Inscritos_Curso.id_estudiante == student_id,
        Inscritos_Curso.estado_invitacion == "Aceptada"
    ).all()

    if not inscripciones:
        raise HTTPException(status_code=404, detail="No está inscrito en ningún curso")

    # Obtener IDs de los cursos
    cursos_ids = [i.id_curso for i in inscripciones]

    # 🗓 Calcular inicio y fin de la semana actual (en UTC para comparar con BD)
    today_utc = datetime.utcnow().replace(tzinfo=None)
    start_of_week_utc = today_utc - timedelta(days=today_utc.weekday())
    end_of_week_utc = start_of_week_utc + timedelta(days=6)

    print(f"🗓 Semana actual (UTC): {start_of_week_utc} - {end_of_week_utc}")
    print(f"📅 Hoy (UTC): {today_utc}")
    
    # Buscar todas las sesiones virtuales de esos cursos
    sesiones = db.query(Sesiones_Virtuales).filter(
        Sesiones_Virtuales.id_curso.in_(cursos_ids),
        Sesiones_Virtuales.hora_inicio <= end_of_week_utc,
        Sesiones_Virtuales.hora_fin >= start_of_week_utc
    ).order_by(Sesiones_Virtuales.hora_inicio.asc()).all()

    if not sesiones:
        return {"message": "No hay sesiones programadas"}

    calendario = []
    
    # Hora actual en El Salvador (UTC-6)
    now_el_salvador = datetime.now(timezone(timedelta(hours=-6))).replace(tzinfo=None)
    print(f"⏰ Hora actual en El Salvador: {now_el_salvador}")

    for sesion in sesiones:
        curso = db.query(Cursos).filter(Cursos.id == sesion.id_curso).first()
        profesor = db.query(Usuarios).filter(Usuarios.id == curso.profesor_id).first()

        # Convertir UTC a hora de El Salvador (UTC-6)
        if sesion.hora_inicio and sesion.hora_fin:
            # Asumir que las fechas en BD están en UTC y convertirlas a El Salvador
            inicio_el_salvador = sesion.hora_inicio.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-6))).replace(tzinfo=None)
            fin_el_salvador = sesion.hora_fin.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-6))).replace(tzinfo=None)
        else:
            inicio_el_salvador = None
            fin_el_salvador = None

        print(f"\n📋 Sesión: {sesion.titulo}")
        print(f"   Inicio (UTC): {sesion.hora_inicio}")
        print(f"   Fin (UTC): {sesion.hora_fin}")
        print(f"   Inicio (El Salvador): {inicio_el_salvador}")
        print(f"   Fin (El Salvador): {fin_el_salvador}")
        print(f"   Ahora (El Salvador): {now_el_salvador}")

        # 🕒 Determinar estado de la llamada usando hora de El Salvador
        if fin_el_salvador and fin_el_salvador < now_el_salvador:
            estado = "concluida"
            print(f"   🔴 ESTADO: CONCLUIDA")
        elif inicio_el_salvador and inicio_el_salvador <= now_el_salvador <= fin_el_salvador:
            estado = "en_curso"
            print(f"   🟢 ESTADO: EN CURSO")
        else:
            estado = "futura"
            print(f"   🔵 ESTADO: FUTURA")

        calendario.append({
            "curso": curso.titulo,
            "sesion": sesion.titulo,
            "descripcion": sesion.descripcion,
            "hora_inicio": inicio_el_salvador,  # ← Enviar hora de El Salvador al frontend
            "hora_fin": fin_el_salvador,        # ← Enviar hora de El Salvador al frontend
            "enlace_llamada": sesion.enlace_llamada,
            "profesor": f"{profesor.nombre} {profesor.apellido}",
            "estado": estado
        })

    return {
        "calendario": calendario, 
        "total": len(calendario), 
        "start_week": start_of_week_utc, 
        "end_of_week": end_of_week_utc, 
        "now": now_el_salvador  # ← Devolver hora de El Salvador
    }

@router.get("/available")
async def get_available_courses(
    current_user: Usuarios = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Obtener IDs de cursos en los que el usuario está inscrito
    enrolled_course_ids = (
        db.query(Inscritos_Curso.id_curso)
        .filter(Inscritos_Curso.id_estudiante == current_user.id)
        .all()
    )

    # Convertir resultados [(1,), (2,), ...] → [1, 2, ...]
    enrolled_course_ids = [c[0] for c in enrolled_course_ids]

    # Consulta base: solo cursos activos
    query = (
        db.query(Cursos, Usuarios)
        .join(Usuarios, Cursos.profesor_id == Usuarios.id)
        .filter(Cursos.estado_curso == "Activo")
    )

    # Si el usuario tiene cursos inscritos, los excluimos
    if enrolled_course_ids:
        query = query.filter(~Cursos.id.in_(enrolled_course_ids))

    # Ejecutar consulta
    available_courses = query.all()

    # Formatear respuesta
    cursos_response = [
        {
            "id": curso.id,
            "titulo": curso.titulo,
            "descripcion": curso.descripcion,
            "profesor": f"{profesor.nombre} {profesor.apellido}",
            "status": curso.estado_curso,
        }
        for curso, profesor in available_courses
    ]

    return {
        "message": "Cursos disponibles encontrados",
        "cursos": cursos_response
    }