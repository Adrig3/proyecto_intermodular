"""
Modelos SQLAlchemy para la base de datos del inventario.

Cada clase hereda de Base (declarative_base) y define las tablas
correspondientes mediante Column con tipos y restricciones.

SQLAlchemy Column: define una columna de la tabla.
- Integer: número entero
- String(n): texto de hasta n caracteres
- Boolean: verdadero/falso
- primary_key=True: clave primaria
- index=True: índice para búsquedas más rápidas
- unique=True: valor único en la tabla
- nullable=False: obligatorio
- default: valor por defecto si no se especifica
"""
from sqlalchemy import Boolean, Column, Integer, String
from database import Base


class Usuario(Base):
    """
    Tabla de usuarios del sistema.

    Almacena credenciales (correo, contraseña hasheada) y rol (esAdmin).
    La contraseña se guarda hasheada con Werkzeug (pbkdf2:sha256).
    """
    __tablename__ = 'usuario'

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(120), unique=True, nullable=False)
    contrasena = Column(String(255), nullable=False)
    esAdmin = Column(Boolean, default=False)


class Producto(Base):
    """
    Tabla de productos del inventario.

    codigo es único para identificar productos sin ambigüedad.
    cantidad y ubicación se actualizan frecuentemente durante la operación del almacén.
    """
    __tablename__ = 'producto'

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    codigo = Column(String(50), unique=True, nullable=False)
    cantidad = Column(Integer, default=0)
    ubicacion = Column(String(100), nullable=True)
