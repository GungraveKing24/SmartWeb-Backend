from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from config import SessionLocal, Base, engine
from routes import NewVideoCall, auth, ejemplo, estudiante, getstreamFile, profesores, administrador
from model.models import Roles, Usuarios
from services.cifrar import hash_password

app = FastAPI()

#app.mount("/static", StaticFiles(directory="static"), name="static")

Base.metadata.create_all(bind=engine)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexion a base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Insertar roles defaults si no existen
def seed_roles():
    db = SessionLocal(bind=engine)
    roles_default = [
        {"id": 1, "nombre_rol": "Estudiante"},
        {"id": 2, "nombre_rol": "Profesor"},
        {"id": 3, "nombre_rol": "Administrador"},
    ]

    for rol_data in roles_default:
        existente = db.query(Roles).filter_by(id=rol_data["id"]).first()
        if not existente:
            # Si no existe con esa ID, verificar si existe por nombre (por si se cambió el ID)
            mismo_nombre = db.query(Roles).filter_by(nombre_rol=rol_data["nombre_rol"]).first()
            if mismo_nombre:
                # Si existe con nombre pero ID diferente → ajustar ID
                mismo_nombre.id = rol_data["id"]
            else:
                # Crear nuevo rol con ID fijo
                nuevo_rol = Roles(id=rol_data["id"], nombre_rol=rol_data["nombre_rol"])
                db.add(nuevo_rol)

    db.commit()
    db.close()

def seed_admin():
    db = SessionLocal()
    password = "admin123"  # O usa os.getenv("ADMIN_PASSWORD")
    
    existing_admin = db.query(Usuarios).filter(Usuarios.email == "admin@admin.com").first()
    if existing_admin:
        db.close()
        return  # Ya existe, no se crea de nuevo
    
    admin_role = db.query(Roles).filter(Roles.nombre_rol == "Administrador").first()
    if not admin_role:
        raise Exception("El rol 'Administrador' no existe. Ejecuta seed_roles primero.")
    
    nuevo_admin = Usuarios(
        nombre="Admin",
        apellido="Principal",
        email="admin@admin.com",
        password_hash=hash_password(password),
        role=admin_role.id,
        confirmado=True,
        status="Activo"
    )
    
    db.add(nuevo_admin)
    db.commit()
    db.close()

# Ejemplo basico de ruta
@app.get("/")
def read_root():
    return {"message": "API is running"}

# Importar rutas
app.include_router(ejemplo.router)
app.include_router(auth.router)
app.include_router(getstreamFile.router)
app.include_router(profesores.router)
app.include_router(administrador.router)
app.include_router(estudiante.router)
app.include_router(NewVideoCall.router)

seed_roles()
seed_admin()