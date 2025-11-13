from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

# Base de datos SQLite como ejemplo de configuración
DATABASE_URL = os.getenv("DATABASE_URL", None)

# Secreto de usuario
SECRET_KEY = os.getenv("SECRET_KEY", None)

# GetStream API credentials
STREAM_API_KEY = os.getenv("STREAM_API_KEY", None)
STREAM_API_SECRET = os.getenv("STREAM_API_SECRET", None)
STREAM_BASE_URL = os.getenv("STREAM_BASE_URL", None)

# Configuración de SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()