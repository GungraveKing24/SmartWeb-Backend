from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from services.email import send_email
from model.models import Usuarios, Notificaciones, TipoNotificacion, EstadoNotificacion
from typing import Dict
from config import SessionLocal

router = APIRouter(prefix="/notifications", tags=["Notifications"])
active_connections: Dict[int, WebSocket] = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.websocket("/ws/notifications/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: int):
    """Conecta a un usuario a su canal de notificaciones."""
    await websocket.accept()
    active_connections[user_id] = websocket
    try:
        while True:
            await websocket.receive_text()  # mantener la conexión viva
    except WebSocketDisconnect:
        del active_connections[user_id]
        print(f"🔌 Usuario {user_id} desconectado")
        
def notify_user_ws(user_id: int, title: str, message: str):
    """Envía un mensaje en tiempo real al usuario si está conectado."""
    import json, asyncio
    if user_id in active_connections:
        data = json.dumps({"title": title, "message": message})
        asyncio.create_task(active_connections[user_id].send_text(data))
        
# Ejemplo de uso para el endpoint
@router.post("/{user_id}")
def create_notification(user_id: int, titulo: str, mensaje: str, db: Session = Depends(get_db)):
    """Crea una notificación, la guarda, la envía por WS y por email."""
    user = db.query(Usuarios).filter(Usuarios.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    notif = Notificaciones(
        usuario_id=user_id,
        titulo=titulo,
        mensaje=mensaje,
        tipo=TipoNotificacion.EN_APP,
        status=EstadoNotificacion.PENDIENTE
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # --- Enviar correo ---
    try:
        send_email(user.email, titulo, mensaje)
        notif.tipo = TipoNotificacion.EMAIL
        notif.status = EstadoNotificacion.ENVIADO
        db.commit()
    except Exception as e:
        print("⚠️ Error enviando correo:", e)

    # --- Enviar en tiempo real (WebSocket) ---
    notify_user_ws(user_id, titulo, mensaje)

    return {"message": "Notificación enviada", "data": {
        "titulo": titulo,
        "mensaje": mensaje,
        "usuario": user.email
    }}