"""
Configuración de la base de datos con SQLAlchemy.

Carga la URL de conexión desde .env (python-dotenv) y crea:
- Base: clase base para modelos declarativos (create_all, metadata)
- engine: motor de conexión a la base de datos (PostgreSQL u otra compatible)
- SessionLocal: factory para crear sesiones ORM (sessionmaker)

echo=True en create_engine muestra el SQL generado en consola (útil en desarrollo).
autocommit=False y autoflush=False: las transacciones se gestionan explícitamente (commit/rollback).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
