from typing import List, Optional, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, func, DateTime, Integer, ForeignKey
from datetime import datetime
from .materials import Reagent

class OligoPrice(SQLModel, table=True):
    __tablename__ = 'oligo_price'
    id: Optional[int] = Field(default=None, primary_key=True)
    reagent_id: Optional[int] = Field(default=None, foreign_key="reagents.id", index=True)
    mod_symbol: Optional[str] = Field(default=None, index=True, title='Модификация')
    scale: Optional[str] = Field(default=None, index=True, title='Масштаб синтеза')
    type: Optional[str] = Field(default=None,  title='Тип модификации')
    unicode: Optional[str] = Field(default=None, title='Код на складе')
    price: Optional[float] = Field(default=None, title='Цена/шаг')
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        ), title='Время события')

    reagent: Optional["Reagent"] = Relationship()
