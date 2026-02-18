from sqlalchemy import Boolean, Column, Integer, String
from database import Base

class Usuario(Base):
    __tablename__ = 'usuario'

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(120), unique=True, nullable=False)
    contrasena = Column(String(255), nullable=False)
    esAdmin = Column(Boolean, default=False)

class Producto(Base):
    __tablename__ = 'producto'

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    codigo = Column(String(50), unique=True, nullable=False)
    cantidad = Column(Integer, default=0)
    ubicacion = Column(String(100), nullable=True)