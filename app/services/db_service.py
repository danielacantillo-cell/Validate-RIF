import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings, logger
from app.models.rif import Base, Lote, ItemRif

# 1. Configuración del Motor Asíncrono
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

# 2. Fábrica de Sesiones
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False,
    autoflush=False
)

class DBService:
    
    async def init_db(self):
        """Crea las tablas en la base de datos si no existen."""
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Tablas de base de datos verificadas/creadas.")
        except Exception as e:
            logger.error(f"❌ Error inicializando la DB: {e}")

    # --- OPERACIONES DE LOTE ---

    async def crear_lote_inicial(self, id_lote: uuid.UUID, items: List[Any], retention_hours: int = 24):
        """Paso 1: Crea el registro del Lote y prepara todos los items como PENDIENTE."""
        async with AsyncSessionLocal() as session:
            try:
                nuevo_lote = Lote(
                    id_lote=id_lote,
                    total_records=len(items),
                    status_lote='PROCESANDO',
                    expires_on=datetime.now() + timedelta(hours=retention_hours),
                    created_at=datetime.now()
                )
                session.add(nuevo_lote)

                objetos_items = [
                    ItemRif(
                        id_item=uuid.uuid4(),
                        id_lote=id_lote,
                        rif_original=item.rif,
                        global_id=item.global_id,
                        status_item='PENDIENTE'
                    )
                    for item in items
                ]
                session.add_all(objetos_items)
                
                await session.commit()
                logger.info(f"💾 Lote {id_lote} registrado con {len(items)} items.")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Error al crear lote inicial: {e}")
                raise e

    async def finalizar_lote(self, id_lote: uuid.UUID):
        """Marca un lote como FINALIZADO."""
        async with AsyncSessionLocal() as session:
            stmt = update(Lote).where(Lote.id_lote == id_lote).values(status_lote='FINALIZADO')
            await session.execute(stmt)
            await session.commit()

    # --- OPERACIONES INCREMENTALES ---

    async def actualizar_item_rif(
        self, 
        id_lote: uuid.UUID, 
        rif_original: str, 
        estatus: str, 
        datos: Optional[Dict] = None, 
        error_msg: Optional[str] = None
    ):
        """Paso 2: Persistencia incremental (uno por uno)."""
        async with AsyncSessionLocal() as session:
            try:
                update_values = {
                    "status_item": estatus,
                    "update_at": datetime.now(),
                    "error_extraccion": error_msg
                }

                if datos:
                    update_values.update({
                        "rif_limpio": datos.get("rif_limpio"),
                        "rif_corregido": datos.get("rif_normalizado"),
                        "rif_parsed": datos.get("rif_parsed"),
                        "nombre": datos.get("nombre"),
                        "firma_personal": datos.get("firma_personal"),
                        "actividad_economica": datos.get("actividad_economica"),
                        "condicion": datos.get("condicion"),
                        "captcha": datos.get("captcha_usado"),
                        "rif_coincide": datos.get("coincide_con_seniat", True),
                        "v_error_antes_tipo": datos.get("TIPO_DE_ERROR_ANTES"),
                        "v_error_despues_tipo": datos.get("TIPO_DE_ERROR_DESPUES")
                    })

                stmt = (
                    update(ItemRif)
                    .where(ItemRif.id_lote == id_lote, ItemRif.rif_original == rif_original)
                    .values(**update_values)
                )
                
                await session.execute(stmt)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Error incremental en item {rif_original}: {e}")

    # --- MÉTRICAS Y REPORTES ---

    async def obtener_estatus_lote(self, id_lote: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Paso 3: Obtiene métricas en tiempo real."""
        async with AsyncSessionLocal() as session:
            res_lote = await session.execute(
                select(Lote.status_lote, Lote.total_records).where(Lote.id_lote == id_lote)
            )
            lote_data = res_lote.first()
            if not lote_data: return None

            res_items = await session.execute(
                select(ItemRif.status_item, func.count(ItemRif.id_item))
                .where(ItemRif.id_lote == id_lote)
                .group_by(ItemRif.status_item)
            )
            
            conteos = {row[0]: row[1] for row in res_items.all()}
            
            completados = conteos.get('COMPLETADO', 0)
            errores = conteos.get('ERROR', 0)
            procesados = completados + errores

            return {
                "id_lote": id_lote,
                "status_general": lote_data.status_lote,
                "total": lote_data.total_records,
                "procesados": procesados,
                "detalle": {
                    "completados": completados,
                    "fallidos": errores,
                    "pendientes": conteos.get('PENDIENTE', 0)
                },
                "progreso_porcentaje": round((procesados / lote_data.total_records) * 100, 2)
            }

    async def obtener_reporte_fallidos(self, id_lote: uuid.UUID) -> List[Dict]:
        """Devuelve registros con error."""
        async with AsyncSessionLocal() as session:
            stmt = select(ItemRif).where(
                ItemRif.id_lote == id_lote, 
                ItemRif.status_item == 'ERROR'
            )
            result = await session.execute(stmt)
            return [
                {
                    "rif_original": i.rif_original,
                    "global_id": i.global_id,
                    "error": i.error_extraccion,
                    "fecha": i.update_at
                } for i in result.scalars().all()
            ]

db_service = DBService()
