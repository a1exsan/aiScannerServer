from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, func, DateTime, Integer, ForeignKey
from sqlmodel import Session
from sqlalchemy import event, select
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from .orders import Oligo, OligoStatus, OligoHistory
    from .equipment import Protocol, Equipment
    from .materials import Reagent, ReagentLot
    from .user import User

class mapStatus(str, Enum):
    NEW = 'new'
    INPROGRESS = 'inprogress'
    COMPLETED = 'completed'
    CLOSED = 'closed'

class rowStatus(str, Enum):
    NEW = 'new'
    QUEUE = "queue"
    SYNTH = "synth"
    PURIF = "purif"
    DRYED = "dryed"
    CLICK = "click"
    REJECTED = 'rejected'
    COMPLETED = 'completed'


class MapEquipmentLink(SQLModel, table=True):
    __tablename__ = 'map_equipment_link'

    # Добавляем ondelete="CASCADE" для обеих сторон
    map_id: int = Field(
        foreign_key="oligomaps.id",
        primary_key=True,
        ondelete="CASCADE"
    )
    equipment_id: int = Field(
        foreign_key="equipment.id",
        primary_key=True,
        ondelete="CASCADE"
    )

class oligoMap(SQLModel, table=True):
    __tablename__ = 'oligomaps'
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default=None, title='Название')
    syn_number: Optional[str] = Field(default=None, title='Номер синтеза')
    status: mapStatus = Field(
        default=mapStatus.NEW,
        title='Статус'
    )
    operator_id: Optional[int] = Field(
        default=None,
        foreign_key="user.id",  # Добавьте это, если забыли
        title='Оператор'
    )
    created_at: datetime = Field(
            sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        ),
        title='Дата создания')
    closed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        title='Дата завершения'
    )

    operator: Optional["User"] = Relationship(back_populates="maps")

    rows: List["mapRow"] = Relationship(
        back_populates="map",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    consumptions: List["MapConsumption"] = Relationship(
        back_populates="map",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    equipments: List["Equipment"] = Relationship(
        back_populates="maps",
        link_model=MapEquipmentLink,
        sa_relationship_kwargs={"cascade": "all, delete"}
    )


class mapRow(SQLModel, table=True):
    __tablename__ = 'maprows'
    id: Optional[int] = Field(default=None, primary_key=True)
    map_id: int = Field(
        foreign_key="oligomaps.id",
        ondelete="CASCADE",
        index=True,
        title=''
    )
    oligo_id: int = Field(
        foreign_key="oligos.id",
        ondelete="CASCADE",
        index=True,
        title=''
    )
    status: rowStatus = Field(
        default=rowStatus.NEW,
        title='Статус'
    )
    chain: str = Field(
        default=None,
        title='Цепочка сборки'
    )
    synt_sequence: str = Field(
        default=None,
        title='Последовательность синтеза'
    )
    current_chain_pos: int = Field(
        default=None,
        title='Этап синтеза'
    )
    position: str = Field(
        default=None,
        title='Номер колонки'
    )
    support_type: Optional[str] = Field(
        default=None,
        title='Тип носителя'
    )
    support_amount: Optional[float] = Field(
        default=0,
        title='Количество носителя'
    )
    DMT_on: Optional[bool] = Field(
        default=True,
        title='DMT_on'
    )

    map: "oligoMap" = Relationship(back_populates="rows")
    oligo: "Oligo" = Relationship(back_populates="map_entries")

    od_measurements: List["opticalDens"] = Relationship(
        back_populates="row_map",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    lcms_measurements: List["lcmsData"] = Relationship(
        back_populates="row_map",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    chrom_measurements: List["chromData"] = Relationship(
        back_populates="row_map",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class measurementType(str, Enum):
    FINAL = 'final'
    TEST = 'test'
    ALKINE = 'alkine'
    ESTER = 'ester'
    CHROM = 'chrom'

class inputODmodel(SQLModel, table=False):
    id: Optional[int] = Field(
        default=None,
        title='Номер колонки'
    )
    well: Optional[str] = Field(
        default=None,
        title='Номер колонки'
    )
    od: Optional[float] = Field(
        default=0.0,
        title='Оптическая плотность, OE/ml'
    )
    volume: Optional[float] = Field(
        default=1.0,
        title='Объем, мл'
    )



class opticalDens(SQLModel, table=True):
    __tablename__ = 'opticaldensity'
    id: Optional[int] = Field(default=None, primary_key=True)
    rowmap_id: int = Field(
        foreign_key="maprows.id",
        ondelete="CASCADE",
        index=True,
        title=''
    )
    type: measurementType = Field(
        default=measurementType.FINAL,
        title='Тип измерения'
    )
    od: float = Field(
        default=0.0,
        title='Оптическая плотность, OE/ml'
    )
    volume: float = Field(
        default=1.0,
        title='Объем, мл'
    )
    data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title='дополнительные данные'
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        ),
        title='Дата создания')

    row_map: "mapRow" = Relationship(back_populates="od_measurements")


class lcmsData(SQLModel, table=True):
    __tablename__ = 'lcmsdata'
    id: Optional[int] = Field(default=None, primary_key=True)
    rowmap_id: int = Field(
        foreign_key="maprows.id",
        ondelete="CASCADE",
        index=True,
        title=''
    )
    type: measurementType = Field(
        default=measurementType.FINAL,
        title='Тип измерения'
    )
    lcms_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title='данные LCMS'
    )

    file_path: Optional[str] = Field(default=None, index=True, title='Путь к файлу архива')

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        ),
        title='Дата создания')

    row_map: "mapRow" = Relationship(back_populates="lcms_measurements")


class chromData(SQLModel, table=True):
    __tablename__ = 'chromdata'
    id: Optional[int] = Field(default=None, primary_key=True)
    rowmap_id: int = Field(
        foreign_key="maprows.id",
        ondelete="CASCADE",
        index=True,
        title=''
    )
    type: measurementType = Field(
        default=measurementType.FINAL,
        title='Тип измерения'
    )
    chrom_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title='данные хроматографии'
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        ),
        title='Дата создания')

    row_map: "mapRow" = Relationship(back_populates="chrom_measurements")


class synthScheme(SQLModel, table=True):
    __tablename__ = 'synthscheme'
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(title='Название схемы/протокола')
    active: Optional[bool] = Field(
        default=False,
        title='Актуальность'
    )
    rules: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title='Схема производства'
    )

class MapConsumption(SQLModel, table=True):
    __tablename__ = 'mapconsumption'
    id: Optional[int] = Field(default=None, primary_key=True)
    map_id: int = Field(foreign_key="oligomaps.id", ondelete="CASCADE")
    reagent_id: Optional[int] = Field(foreign_key="reagents.id")
    protocol_id: Optional[int] = Field(foreign_key="protocols.id")

    key: Optional[str] = Field(default=None, title='Позиция в синтезаторе')
    name: Optional[str] = Field(default=None, title='Модификация')
    volume: Optional[str] = Field(default=None, title='Расход / шаг')
    concentration: Optional[str] = Field(default=None, title='Концентрация')
    count: Optional[int] = Field(default=0, title='Количество шагов')
    reagent_amount_g: Optional[float] = Field(default=0.0, title='Количество реагента, г')
    reagent_amount_ml: Optional[float] = Field(default=0.0, title='Количество реагента, мл')

    estimated_amount: float = Field(
        default=0.0,
        title='Расчетный расход (План)'
    )

    actual_amount: Optional[float] = Field(
        default=0.0,
        title='Фактический расход (Факт)'
    )
    # Для ИИ-ассистента и лаборанта
    comment: Optional[str] = Field(default=None, title='Причина отклонения')

    map: "oligoMap" = Relationship(back_populates="consumptions")
    reagent: "Reagent" = Relationship(back_populates="consumptions")
    protocol: "Protocol" = Relationship()

    @property
    def deviation(self) -> float:
        """Разница между планом и фактом"""
        return self.actual_amount - self.estimated_amount
