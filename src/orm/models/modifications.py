from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, func, DateTime, Integer, ForeignKey
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from .materials import Reagent


class modificationType(str, Enum):
    CHEMICAL = 'chemical'
    PROCESS = 'process'
    AMIDITE = 'amidite'
    AZIDE = 'azide'
    ESTER = 'NHS'
    CPG = 'cpg'
    CHROM = 'chrom'
    CART = 'cart'
    REPLACE = 'replace'
    STOP_CHAIN = 'stop_chain'


class Modification(SQLModel, table=True):
    __tablename__ = 'modifications'
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(
        default=None,
        title='Название',
        unique=True
    )
    type: Optional[str] = Field(
        default=modificationType.CHEMICAL,
        title='Тип модификации'
    )
    unicode: Optional[str] = Field(
        default=None,
        title='юникод'
    )
    reagent_id: Optional[int] = Field(foreign_key="reagents.id", index=True)
    smiles: Optional[str] = Field(
        default=None,
        title='Структурная формула'
    )
    data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title='дополнительные данные'
    )
    reagent: Optional["Reagent"] = Relationship(back_populates="modifications")


class Reaction(SQLModel, table=True):
    __tablename__ = 'reactions'
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(
        default=None,
        title='Название',
        unique=True
    )
    smarts: Optional[str] = Field(
        default=None,
        title='Структурная формула'
    )
    data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title='дополнительные данные'
    )