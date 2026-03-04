from sqlalchemy import Column, String, JSON, DateTime, Integer, ForeignKey, UUID, Boolean, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List
import uuid

# --- BASE DECLARATIVA ---
class Base(DeclarativeBase):
    pass

# --- MODELO PARA LA TABLA DE USUARIOS ---
class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_usuario: Mapped[str] = mapped_column(String(100), nullable=False)
    tokn_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relación con Lotes (un usuario puede tener varios lotes)
    lotes: Mapped[List["Lote"]] = relationship(back_populates="usuario")


# --- MODELO PARA LA TABLA LOTES ---
class Lote(Base):
    __tablename__ = "lotes"

    id_lote: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    token_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=True)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False)
    status_lote: Mapped[str] = mapped_column(String(20), default='PROCESANDO') # PROCESANDO, FINALIZADO, ERROR_GENERAL
    expires_on: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now()) # Añadido update_at

    # Relación con usuario
    usuario: Mapped["Usuario"] = relationship(back_populates="lotes")

    # Relación con Items_Rifs (un lote tiene muchos items)
    items: Mapped[List["ItemRif"]] = relationship(back_populates="lote")


# --- MODELO PARA LA TABLA ITEMS_RIFS ---
class ItemRif(Base):
    __tablename__ = "items_rifs"

    id_item: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    id_lote: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("lotes.id_lote"), nullable=False, index=True)
    
    # --- Campos de entrada ---
    rif_original: Mapped[str] = mapped_column(String(50))
    global_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # Asumiendo que global_id es lo que me pasaste como global_id

    # --- Campos de validación matemática ---
    rif_corregido: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    v_error_antes_tipo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # Adaptado de TEXT
    v_error_antes_det: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Adaptado de TEXT
    v_error_despues_tipo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # Adaptado de TEXT
    v_error_despues_det: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Adaptado de TEXT
    rif_coincide: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # --- Campos de extracción SENIAT ---
    captcha: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    rif_limpio: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # Adaptado de VARCHAR(20)
    rif_parsed: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    nombre: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Adaptado de TEXT
    firma_personal: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Adaptado de TEXT
    actividad_economica: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Adaptado de TEXT
    condicion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # Adaptado de TEXT
    
    # --- Campos de error/estado ---
    error_extraccion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Adaptado de TEXT
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    status_item: Mapped[str] = mapped_column(String(20), default='PENDIENTE') # PENDIENTE, COMPLETADO, ERROR
    
    update_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relación con Lote (un item pertenece a un solo lote)
    lote: Mapped["Lote"] = relationship(back_populates="items")
