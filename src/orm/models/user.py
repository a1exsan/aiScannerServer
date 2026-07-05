from typing import List, Optional, Dict, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from src.orm.models.permissions import LAB_INTERFACE

if TYPE_CHECKING:
    from .orders import Order
    from .oligomaps import oligoMap
    from .materials import ReagentTransaction


class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, title='Название')
    instruction: Optional[str] = Field(default="# Регламент\n1. Проверить реагенты...")

    permissions: Dict = Field(
        sa_column=Column(JSON),
        default_factory=lambda: LAB_INTERFACE.copy()
    )
    users: List["User"] = Relationship(back_populates="role")




class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, title='Логин')
    hashed_password: str
    email: Optional[str] = Field(default=None, title='Почта')
    phone: Optional[str] = Field(default=None, title='Телефон')
    full_name: str = Field(default=None, title='ФИО')
    job_title: str = Field(default=None, title='Должность')
    is_active: bool = Field(default=True, title='Статус')
    role_id: Optional[int] = Field(default=None, foreign_key="role.id")

    role: Optional["Role"] = Relationship(back_populates="users")
    orders: List["Order"] = Relationship(back_populates="creator")
    maps: List["oligoMap"] = Relationship(back_populates="operator")
    transactions: List["ReagentTransaction"] = Relationship(back_populates="user")