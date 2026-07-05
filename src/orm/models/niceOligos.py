from typing import List, Optional, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, DateTime, UniqueConstraint
from enum import Enum
from datetime import datetime, timezone
from pydantic import field_validator


class transactionType(str, Enum):
    INCOMING = 'incoming'     # Приход (новая партия)
    CONSUMPTION = 'consumption' # Расход на синтез (автоматически из MapConsumption)
    WASTE = 'waste'           # Брак / Пролив
    EXPIRED = 'expired'       # Списание по сроку годности
    ADJUSTMENT = 'adjustment' # Корректировка после инвентаризации


class reagentUnits(str, Enum):
    ml = 'ml'
    L = 'liter'
    g = 'g'
    kg = 'kg'
    ul = 'ul'
    bottle = 'bottle'
    pkg = 'pkg'


class ReagentTransaction(SQLModel, table=True):
    __tablename__ = 'reagent_transactions'
    id: Optional[int] = Field(default=None, primary_key=True)
    lot_id: int = Field(
        foreign_key="reagent_lots.id",
        index=True,
        ondelete="CASCADE"
    )
    type: transactionType = Field(title='Тип операции')
    amount: float = Field(title='Количество')
    user_id: Optional[int] = Field(foreign_key="user.id", default=None)
    map_id: Optional[int] = Field(foreign_key="oligomaps.id", default=None)
    comment: Optional[str] = Field(default=None, title='Примечание')
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    lot: "ReagentLot" = Relationship(back_populates="transactions")
    user: Optional["User"] = Relationship(back_populates="transactions")

    @field_validator('created_at', mode='before')
    @classmethod
    def ensure_utc_timezone(cls, v):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
        elif isinstance(v, str) and v.strip() != '':
            # Если из Excel/API пришла строка, парсим её и вешаем UTC
            try:
                dt_obj = datetime.fromisoformat(v.replace('Z', '+00:00'))
                if dt_obj.tzinfo is None:
                    return dt_obj.replace(tzinfo=timezone.utc)
                return dt_obj
            except ValueError:
                pass
        return v

class ReagentGroup(SQLModel, table=True):
    __tablename__ = 'reagent_groups'
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, title='Название группы')
    description: Optional[str] = Field(default=None, title='Описание')

    reagents: List["Reagent"] = Relationship(back_populates="group")

class ReagentType(str, Enum):
    CHEMICAL = 'chemical'
    MATERIAL = 'material'
    SOLUTION = 'solution'

class SolutionModel(SQLModel, table=False):
    id: int = Field(default=0, title='#')
    name: str = Field(default='', title='Компонент')
    percent: float = Field(default=0, title='Объемная доля')

class Reagent(SQLModel, table=True):
    __tablename__ = 'reagents'
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, title='Название')
    catalog_number: Optional[str] = Field(default=None, title='Артикул')
    manufacturer: Optional[str] = Field(default=None, title='Производитель')
    supplier: Optional[str] = Field(default=None, title='Поставщик')
    unit: str = Field(default='ml', title='Ед. изм.')
    cost_per_unit: float = Field(default=0.0, title='Цена за ед.')
    treshold: float = Field(default=0.0, title='Лимит')
    group_id: Optional[int] = Field(default=None, foreign_key="reagent_groups.id")
    data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title='дополнительные данные'
    )

    # Связь с конкретными партиями на складе
    lots: List["ReagentLot"] = Relationship(
        back_populates="reagent",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",  # Физически удаляет лоты при удалении реактива
            "passive_deletes": True  # Запрещает ORM прописывать NULL в reagent_id
        }
    )
    prices: List["OligoPrice"] = Relationship(back_populates="reagent")
    modifications: List["Modification"] = Relationship(back_populates="reagent")
    group: Optional[ReagentGroup] = Relationship(back_populates="reagents")
    consumptions: List["MapConsumption"] = Relationship(back_populates="reagent")


class ReagentLot(SQLModel, table=True):
    __tablename__ = 'reagent_lots'
    __table_args__ = (
        UniqueConstraint("reagent_id", "lot_number", name="unique_lot_per_reagent"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    reagent_id: int = Field(
        foreign_key="reagents.id",
        index=True,
        ondelete="CASCADE"
    )

    lot_number: str = Field(index=True, title='Номер лота/партии')
    expiry_date: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True)),
        title='Срок годности'
    )
    current_stock: float = Field(default=0.0, title='Текущий остаток лота')
    initial_stock: float = Field(default=0.0, title='Приход (изначально)')

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        title='Дата поступления'
    )

    reagent: "Reagent" = Relationship(back_populates="lots")
    # Связь с расходом в картах (чтобы знать, какой лот ушел в синтез)
    transactions: List["ReagentTransaction"] = Relationship(
        back_populates="lot",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",  # Физически удаляет транзакции при удалении лота
            "passive_deletes": True  # Запрещает выставлять NULL в lot_id зависимой таблицы
        }
    )