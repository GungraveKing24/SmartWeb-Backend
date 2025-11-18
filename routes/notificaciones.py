from fastapi import APIRouter, Depends, HTTPException
from model.models import EstadoNotificacion, Notificaciones
from sqlalchemy.orm import Session
from config import SessionLocal
from services.jwt import verify_token

router = APIRouter(prefix="/notifications", tags=["Notificaciones"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------
#  GET: Todas las notificaciones
# ------------------------------
@router.get("/{user_id}")
def get_notifications(
    user_id: int,
    current_user=Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Solo permitir que el usuario vea sus propias notificaciones
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    notifs = (
        db.query(Notificaciones)
        .filter(Notificaciones.usuario_id == user_id)
        .order_by(Notificaciones.hora_envio.desc())
        .all()
    )

    return {"notificaciones": notifs}


# -----------------------------------
#  PUT: Marcar TODAS como leídas
# -----------------------------------
@router.put("/{user_id}/mark_all_read")
def mark_all_read(
    user_id: int,
    current_user=Depends(verify_token),
    db: Session = Depends(get_db)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    db.query(Notificaciones).filter(
        Notificaciones.usuario_id == user_id,
        Notificaciones.status == EstadoNotificacion.PENDIENTE
    ).update({Notificaciones.status: EstadoNotificacion.LEIDO})

    db.commit()

    return {"message": "Todas las notificaciones fueron marcadas como leídas"}


# -----------------------------------
#  PUT: Marcar UNA notificación como leída
# -----------------------------------
@router.put("/{notif_id}/read")
def mark_one_as_read(
    notif_id: int,
    current_user=Depends(verify_token),
    db: Session = Depends(get_db)
):
    notif = db.query(Notificaciones).filter(Notificaciones.id == notif_id).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    if notif.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")

    notif.status = EstadoNotificacion.LEIDO
    db.commit()

    return {"message": "Notificación marcada como leída"}
