from fastapi import APIRouter, Depends, HTTPException

routes = APIRouter()

# notificar inicio de sesion de usuario
@routes.post("/notifications/login")
async def notify_login(user_id: int):
    return {"message": "Notificación de inicio de sesión enviada", "user_id": user_id}

# notificar nuevo mensaje
@routes.post("/notifications/new_message")
async def notify_new_message(user_id: int, message: str):
    return {"message": "Notificación de nuevo mensaje enviada", "user_id": user_id, "message_content": message}

# notificacion de inscripcion a curso
@routes.post("/notifications/course_enrollment")
async def notify_course_enrollment(user_id: int, course_id: int):
    return {"message": "Notificación de inscripción a curso enviada", "user_id": user_id, "course_id": course_id}