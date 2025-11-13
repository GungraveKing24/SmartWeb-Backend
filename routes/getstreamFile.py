from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from getstream import Stream
from getstream.models import UserRequest
from config import STREAM_API_KEY, STREAM_API_SECRET, STREAM_BASE_URL
from datetime import datetime
import uuid

router = APIRouter(prefix="/getstream", tags=["getstream"])

client = Stream(api_key=STREAM_API_KEY, api_secret=STREAM_API_SECRET, base_url=STREAM_BASE_URL)

# Modelos Pydantic
class CreateCallRequest(BaseModel):
    user_id: str

class JoinCallRequest(BaseModel):
    user_id: str
    call_id: str

active_calls = {}

@router.post("/create/call")
async def create_call(request: CreateCallRequest):
    try:
        user_id = request.user_id
        print(f"Creando llamada para usuario: {user_id}")
        
        # ✅ USAR EL MÉTODO OFICIAL DEL SDK PARA GENERAR TOKENS
        user_token = client.create_token(user_id)
        print(f"Token generado por SDK: {user_token[:50]}...")
        
        # Crear usuario en GetStream
        client.upsert_users(UserRequest(id=user_id, name=user_id))

        # Generar ID único para la llamada
        call_id = str(uuid.uuid4())
        print(f"Call ID: {call_id}")
        
        # Crear la llamada
        call = client.video.call("default", call_id)
        call.get_or_create(data={
            "created_by_id": user_id, 
            "members": [{"user_id": user_id, "role": "user"}]
        })

        # Guardar llamada activa
        active_calls[call_id] = {
            "created_by": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "participants": [user_id]
        }

        return {
            "call_id": call_id,
            "user_id": user_id,
            "token": user_token,
            "action": "created"
        }

    except Exception as e:
        print(f"Error en create_call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creando llamada: {str(e)}")

@router.post("/join/call")
async def join_call(request: JoinCallRequest):
    try:
        user_id = request.user_id
        call_id = request.call_id
        
        print(f"Uniendo {user_id} a {call_id}")
        
        # Verificar si la llamada existe
        call = client.video.call("default", call_id)
        try:
            call.get()
        except Exception:
            raise HTTPException(status_code=404, detail="Llamada no encontrada")

        # ✅ USAR EL MÉTODO OFICIAL DEL SDK PARA GENERAR TOKENS
        user_token = client.create_token(user_id)
        
        # Crear usuario
        client.upsert_users(UserRequest(id=user_id, name=user_id))

        # Actualizar participantes
        if call_id in active_calls:
            if user_id not in active_calls[call_id]["participants"]:
                active_calls[call_id]["participants"].append(user_id)
        else:
            active_calls[call_id] = {
                "created_by": "unknown",
                "created_at": datetime.utcnow().isoformat(),
                "participants": [user_id]
            }

        return {
            "user_id": user_id,
            "call_id": call_id,
            "token": user_token,
            "action": "joined"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en join_call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uniéndose: {str(e)}")

@router.get("/active/calls")
async def get_active_calls():
    return active_calls

@router.get("/health")
async def health_check():
    return {
        "status": "ok", 
        "timestamp": datetime.utcnow().isoformat(),
        "active_calls": len(active_calls)
    }