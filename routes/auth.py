from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from model.models import Usuarios, AuthToken, Roles
from services.cifrar import hash_password
from schemas.s_usuarios import UsuarioLogin, UsuarioCreate
from services.cifrar import verify_password
from config import SessionLocal, DOMINIO_VERIFICACION
from services.jwt import create_access_token, verify_token
from services.email import send_email
from uuid import uuid4
from utils.time import utcnow 

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register")
async def register_user(user: UsuarioCreate, db: Session = Depends(get_db)):
    existing_user = db.query(Usuarios).filter(Usuarios.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    default_role = db.query(Roles).filter(Roles.nombre_rol == user.role).first()
    if not default_role:
        raise HTTPException(status_code=400, detail="Rol no válido")

    hashed_password = hash_password(user.password)
    activation_token = str(uuid4())

    nuevo_usuario = Usuarios(
        nombre=user.nombre,
        apellido=user.apellido,
        email=user.email,
        password_hash=hashed_password,
        role=default_role.id,
        token_activacion=activation_token,
        confirmado=False,
        status="Inactivo",
        motivacion=user.motivacion, 
        profesor_institucion=user.profesor_institucion,
        profesor_cedula=user.profesor_cedula
    )

    if default_role.nombre_rol == "Estudiante":
        # Enviar email directo
        activation_link = f"{DOMINIO_VERIFICACION}/auth/activate/{activation_token}"
        
        html_message = f"""
        <h2>Hola {user.nombre} 👋</h2>
        <p>Gracias por registrarte. Para activar tu cuenta, haz clic en el siguiente enlace:</p>
            <a href="{activation_link}" 
            style="padding: 10px 15px; background: #4f46e5; color: white; text-decoration:none; border-radius: 6px;">
            Activar mi cuenta
        </a>
        <br><br>
        <p>Si no solicitaste esta cuenta, ignora este mensaje.</p>
        """

        await send_email(
            to=user.email,
            subject="Activa tu cuenta - Plataforma Educativa",
            html_body=html_message
        )
        
    elif default_role.nombre_rol == "Profesor":
        html_admin = f"""
        <h2>Nuevo profesor pendiente de aprobación</h2>
        <p>Nombre: {user.nombre} {user.apellido}</p>
        <p>Email: {user.email}</p>
        <p>Cédula: {user.profesor_cedula}</p>
        <p>Institución: {user.profesor_institucion}</p>
        """

        await send_email(
            to="gungraveheat123@gmail.com",
            subject="Nuevo profesor esperando aprobación",
            html_body=html_admin
        )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return {"message": "Registro exitoso. Verifique su correo si aplica."}

# Login manual
@router.post("/login")
async def login_user(user_data: UsuarioLogin, db: Session = Depends(get_db)):
    user = db.query(Usuarios).filter(Usuarios.email == user_data.email).first()

    if not user:
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")
    
    if not user.confirmado:
        raise HTTPException(status_code=403, detail="Cuenta no confirmada")

    # Control de múltiples sesiones
    existing_token = db.query(AuthToken).filter(
        AuthToken.user_id == user.id,
        AuthToken.revocado == False
    ).first()

    # 🔥 Nueva lógica: si el token existe pero ya expiró, lo revocamos
    if existing_token:
        now = utcnow()
        if existing_token.expiracion < now:
            existing_token.revocado = True
            db.commit()
        else:
            raise HTTPException(status_code=403, detail="Ya hay una sesión activa")

    role = db.query(Roles).filter(Roles.id == user.role).first()
    if not role:
        raise HTTPException(status_code=500, detail="Rol del usuario no encontrado")

    # Generar token JWT (con expiración corta, p.ej. 2 minutos para pruebas)
    access_token = create_access_token(
        {"sub": str(user.id), "name": user.nombre, "rol": str(role.nombre_rol)},
        expires_delta=timedelta(minutes=30)
    )

    # Guardar token en la base de datos
    expiracion = utcnow() + timedelta(minutes=30)
    new_token = AuthToken(
        user_id=user.id,
        jwt_token=access_token,
        expiracion=expiracion,
        revocado=False,
    )
    db.add(new_token)

    # Marcar usuario como activo
    user.status = "Activo"
    db.commit()

    return {"access_token": access_token, "token_type": "bearer", "name": user.nombre, "role": role.nombre_rol}

@router.post("/logout")
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token_str = credentials.credentials

    # Buscar el token exacto
    token_db = db.query(AuthToken).filter(
        AuthToken.jwt_token == token_str,
        AuthToken.revocado == False
    ).first()
    
    if not token_db:
        raise HTTPException(status_code=400, detail="No hay sesión activa")

    # Marcar token como revocado
    token_db.revocado = True

    # Marcar usuario como inactivo
    user = db.query(Usuarios).filter(Usuarios.id == token_db.user_id).first()
    if user:
        user.status = "Inactivo"

    db.commit()

    return {"message": "Sesión cerrada correctamente"}

@router.get("/activate/{token}")
async def activate_account(token: str, db: Session = Depends(get_db)):
    user = db.query(Usuarios).filter(Usuarios.token_activacion == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Token inválido")

    user.confirmado = True
    user.status = "Activo"
    user.token_activacion = None
    db.commit()
    return {"message": "Cuenta activada correctamente"}

@router.get("/verify-token")
async def verify_user_token(current = Depends(verify_token)):
    return {
        "valid": True,
        "user_id": current.id,
        "nombre": current.nombre,
        "rol": current.role_name.lower(),
    }
