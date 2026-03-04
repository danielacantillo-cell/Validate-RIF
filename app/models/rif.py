from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import uuid

# Esquema de Entrada (Request)

class RifInput(BaseModel):
    """
    Representa un ítem individual de RIF dentro de un lote.
    """
    rif: str = Field(
        default=...,  # Especificamos explícitamente que es obligatorio
        examples=["V123456789"], 
        description="RIF del contribuyente. Se permiten guiones, espacios o puntos; el sistema los limpiará automáticamente."
    )
    global_id: Optional[str] = Field(
        default=None, 
        examples=["FACTURA_001"], 
        description="ID opcional del cliente para vinculación interna."
    )

    @field_validator('rif')
    @classmethod
    def limpiar_rif(cls, v: str) -> str:
        # Limpieza profunda
        v_limpio = v.replace("-", "").replace(" ", "").replace(".", "").strip().upper()
        
        # Validar alfanumérico
        if not v_limpio.isalnum():
            raise ValueError("El RIF contiene caracteres inválidos. Solo se permiten letras y números.")
            
        # Validar longitud
        if len(v_limpio) < 5:
            raise ValueError("El RIF es demasiado corto.")
        
        return v_limpio
class BatchRequest(BaseModel):
    """
    Contrato para la carga masiva de RIFs.
    """
    items: List[RifInput] = Field(
        ..., 
        min_length=1, 
        max_length=5000, # Aumentado para mayor flexibilidad en lotes grandes
        description="Lista de RIFs a procesar."
    )
    retention_hours: int = Field(
        24, 
        ge=1, 
        le=168, 
        description="Horas de persistencia de los datos en el sistema (1h hasta 168h/7 días)."
    )

    @field_validator('retention_hours')
    @classmethod
    def check_max_retention(cls, v: int):
        if v > 168:
            raise ValueError("El tiempo de persistencia no puede exceder las 168 horas.")
        return v

# Esquema de Salida (Response Models)

class BatchResponse(BaseModel):
    """
    Respuesta inmediata tras recibir un lote exitosamente.
    """
    id_lote: uuid.UUID
    status: str = "PROCESANDO"
    total_records: int
    expires_on: str = Field(..., description="Fecha estimada de expiración en formato ISO 8601.")
    mensaje: str = "Lote recibido correctamente. Use el id_lote para consultar el progreso."

class ErrorResponse(BaseModel):
    """
    Estructura estándar para respuestas de error (400, 401, 403, 500).
    """
    code: str
    message: str
    detail: Optional[str] = None
