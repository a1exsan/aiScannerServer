from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, func, DateTime, Integer, ForeignKey
from enum import Enum
from datetime import datetime, timezone
from .oligomaps import MapEquipmentLink

if TYPE_CHECKING:
    from .oligomaps import oligoMap, MapConsumption


class EquipmentProtocolLink(SQLModel, table=True):
    __tablename__ = 'equipment_protocol_link'
    equipment_id: int = Field(foreign_key="equipment.id", primary_key=True)
    protocol_id: int = Field(foreign_key="protocols.id", primary_key=True)

class equipmentStatus(str, Enum):
    IDLE = 'idle'              # Свободен, ждет задачу
    RUNNING = 'running'        # В работе (выполняет карту/замер)
    MAINTENANCE = 'maintenance'# Обслуживание (замена фильтров/колонки)
    CALIBRATION = 'calibration'# Поверка/Калибровка
    ERROR = 'error'            # Технический сбой/Ошибка
    OFFLINE = 'offline'        # Выключен/Законсервирован

class equipmentType(str, Enum):
    SYNTH = 'oligo synthesizer'
    CHROM = 'chromatograph'
    OTHER = 'other'

class Equipment(SQLModel, table=True):
    __tablename__ = 'equipment'  # Исправлено
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, title='Название')
    model_name: Optional[str] = Field(default=None, title='Модель/Тип')  # Например, "ASM-800"
    serial_number: Optional[str] = Field(default=None, title='Серийный номер')

    status: equipmentStatus = Field(
        default=equipmentStatus.IDLE,
        title='Статус'
    )

    config: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title='Конфигурация'  # Количество линий, объемы шприцов и т.д.
    )

    last_service: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        title='Дата последнего ТО'
    )

    next_service: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        title='Дата следующего ТО'
    )

    protocols: List["Protocol"] = Relationship(
        back_populates="equipments",
        link_model=EquipmentProtocolLink
    )

    maps: List["oligoMap"] = Relationship(
        back_populates="equipments",
        link_model=MapEquipmentLink
    )


class protocolType(str, Enum):
    SYNTH = 'synth'
    PURIF = 'purif'
    DRYING = 'drying'
    PREP = 'prep'


class Protocol(SQLModel, table=True):
    __tablename__ = 'protocols'
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, title='Название')
    type: protocolType = Field(default=protocolType.SYNTH, title='Тип протокола')

    # Версия протокола (важно для контроля качества)
    version: str = Field(default='1.0', title='Версия')
    is_active: bool = Field(default=True, title='Актуален')

    # Само содержание протокола
    content: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title='Параметры протокола'
    )  # Здесь: времена циклов, концентрации, температуры, расходники

    description: Optional[str] = Field(default=None, title='Описание/Примечание')

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),  # Решение для Python/Pydantic
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),  # Решение для уровня БД
            nullable=False
        ),
        title='Дата создания'
    )

    equipments: List["Equipment"] = Relationship(
        back_populates="protocols",
        link_model=EquipmentProtocolLink
    )
    consumptions: List["MapConsumption"] = Relationship(back_populates="protocol")
