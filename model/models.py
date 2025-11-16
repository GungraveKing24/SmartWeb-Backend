from config import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Boolean,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

# --- ENUMS ---

class EstadoUsuario(enum.Enum):
    Activo = "Activo"
    Inactivo = "Inactivo"

class EstadoCurso(enum.Enum):
    Activo = "Activo"
    Inactivo = "Inactivo"
    Archivado = "Archivado"

class EstadoInvitacion(enum.Enum):
    Pendiente = "Pendiente"
    Aceptada = "Aceptada"
    Expirada = "Expirada"

class CalidadVideo(enum.Enum):
    p360 = "360p"
    p480 = "480p"
    p720 = "720p"
    p1080 = "1080p"
    p4K = "4K"

class RoleLlamada(enum.Enum):
    HOST = "HOST"
    PARTICIPANTE = "PARTICIPANTE"

class TipoNotificacion(enum.Enum):
    EMAIL = "EMAIL"
    EN_APP = "EN_APP"

class EstadoNotificacion(enum.Enum):
    PENDIENTE = "PENDIENTE"
    ENVIADO = "ENVIADO"
    LEIDO = "LEIDO"

# --- TABLAS ---

class Roles(Base):
    __tablename__ = "Roles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre_rol = Column(String, unique=True, nullable=False)

    usuarios = relationship("Usuarios", back_populates="rol")


class Usuarios(Base):
    __tablename__ = "Usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    apellido = Column(String)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String)
    role = Column(Integer, ForeignKey("Roles.id"), nullable=False)
    creacion_cuenta = Column(DateTime(timezone=False), server_default=func.now())
    ultimo_login = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())
    status = Column(Enum(EstadoUsuario), default=EstadoUsuario.Activo)
    confirmado = Column(Boolean, default=False)
    token_activacion = Column(String, nullable=True)
    profesor_institucion = Column(String, nullable=True, default="")
    profesor_cedula = Column(Integer, nullable=True, default=None)
    motivacion = Column(String, nullable=True, default="")

    rol = relationship("Roles", back_populates="usuarios")
    cursos_dictados = relationship("Cursos", back_populates="profesor")
    notificaciones = relationship("Notificaciones", back_populates="usuario")


class Cursos(Base):
    __tablename__ = "Cursos"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String)
    descripcion = Column(String)
    profesor_id = Column(Integer, ForeignKey("Usuarios.id"), nullable=False)
    creacion_curso = Column(DateTime(timezone=False), server_default=func.now())
    estado_curso = Column(Enum(EstadoCurso), default=EstadoCurso.Activo)

    profesor = relationship("Usuarios", back_populates="cursos_dictados")
    inscritos = relationship("Inscritos_Curso", back_populates="curso")
    sesiones = relationship("Sesiones_Virtuales", back_populates="curso")
    contenidos = relationship("Contenido", back_populates="curso")


class Inscritos_Curso(Base):
    __tablename__ = "Inscritos_Curso"

    id_inscripcion = Column(Integer, primary_key=True, index=True)
    id_curso = Column(Integer, ForeignKey("Cursos.id"))
    id_estudiante = Column(Integer, ForeignKey("Usuarios.id"))
    fecha_inscripcion = Column(DateTime(timezone=False), server_default=func.now())
    estado_invitacion = Column(Enum(EstadoInvitacion), default=EstadoInvitacion.Pendiente)
    enlace_unico = Column(String, unique=True)

    curso = relationship("Cursos", back_populates="inscritos")
    estudiante = relationship("Usuarios")


class Sesiones_Virtuales(Base):
    __tablename__ = "Sesiones_Virtuales"

    id_sesion = Column(Integer, primary_key=True, index=True)
    id_curso = Column(Integer, ForeignKey("Cursos.id"))
    titulo = Column(String)
    descripcion = Column(String)
    hora_inicio = Column(DateTime)
    hora_fin = Column(DateTime)
    enlace_llamada = Column(String)
    calidad_video = Column(Enum(CalidadVideo))
    grabacion_url = Column(String)
    creacion_llamada = Column(DateTime(timezone=False), server_default=func.now())

    curso = relationship("Cursos", back_populates="sesiones")
    participantes = relationship("Participantes_Sesion_V", back_populates="sesion")


class Participantes_Sesion_V(Base):
    __tablename__ = "Participantes_Sesion_V"

    id = Column(Integer, primary_key=True, index=True)
    id_sesion = Column(Integer, ForeignKey("Sesiones_Virtuales.id_sesion"))
    id_usuario = Column(Integer, ForeignKey("Usuarios.id"))
    hora_unido = Column(DateTime)
    role_llamada = Column(Enum(RoleLlamada), default=RoleLlamada.PARTICIPANTE)

    sesion = relationship("Sesiones_Virtuales", back_populates="participantes")
    usuario = relationship("Usuarios")


class Contenido(Base):
    __tablename__ = "Contenido"

    id = Column(Integer, primary_key=True, index=True)
    id_curso = Column(Integer, ForeignKey("Cursos.id"))
    texto_contenido = Column(String)
    urls = Column(String)
    creacion = Column(DateTime(timezone=False), server_default=func.now())
    hora_visible = Column(DateTime)
    hora_no_visible = Column(DateTime)

    curso = relationship("Cursos", back_populates="contenidos")


class Notificaciones(Base):
    __tablename__ = "Notificaciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("Usuarios.id"))
    titulo = Column(String)
    mensaje = Column(String)
    tipo = Column(Enum(TipoNotificacion))
    status = Column(Enum(EstadoNotificacion), default=EstadoNotificacion.PENDIENTE)
    hora_envio = Column(DateTime(timezone=False), server_default=func.now())

    usuario = relationship("Usuarios", back_populates="notificaciones")


class AuthToken(Base):
    __tablename__ = "auth_token"

    token_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("Usuarios.id"))
    jwt_token = Column(String)
    expiracion = Column(DateTime)
    creacion = Column(DateTime(timezone=False), server_default=func.now())
    revocado = Column(Boolean, default=False)

    usuario = relationship("Usuarios")
