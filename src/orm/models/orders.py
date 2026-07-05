from typing import List, Optional, Dict, Any, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship, Column, JSON, func, DateTime, Integer, ForeignKey
from sqlmodel import Session
from sqlalchemy import event, select
from enum import Enum
from datetime import datetime, timezone
from .oligomaps import mapRow

if TYPE_CHECKING:
    from .user import User

class OligoStatus(str, Enum):
    NEW = "new"
    QUEUE = "queue"
    SYNTH = "synth"
    PURIF = "purif"
    DRYED = "dryed"
    CLICK = "click"
    REMAKE = "remake"
    COMPLETED = 'completed'
    SENT = "sent"


class OligoHistory(SQLModel, table=True):
    __tablename__ = "oligos_history"
    id: Optional[int] = Field(default=None, primary_key=True)
    oligo_id: int = Field(
        foreign_key="oligos.id",
        ondelete="CASCADE",
        index=True,
        title=''
    )
    status: OligoStatus = Field(
        default=OligoStatus.NEW,
        title='Статус'
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        ), title='Время события')

    oligo: "Oligo" = Relationship(back_populates="history")


class Oligo(SQLModel, table=True):
    __tablename__ = "oligos"
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(
        foreign_key="orders.id",
        ondelete="CASCADE",
        index=True,
        title='Заказ'
    )
    name: str = Field(index=True, title='Название')
    seq: str = Field(default=None, title='Последовательность')
    end5: str = Field(default=None, title="5'-мод.")
    end3: str = Field(default=None, title="3'-мод.")
    scale: str = Field(default=None, title="Масштаб")
    purification: str = Field(default=None, title="Тип очистки")
    status: OligoStatus = Field(
        default=OligoStatus.NEW,
        index=True, title='Статус'
    )

    order: "Order" = Relationship(back_populates="oligos")
    history: List["OligoHistory"] = Relationship(
        back_populates="oligo",
        cascade_delete=True
    )
    map_entries: List["mapRow"] = Relationship(back_populates="oligo")


class Client(SQLModel, table=True):
    __tablename__ = "clients"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, title='Название организации')
    address: Optional[str] = Field(default=None, title='Адрес')
    phone: Optional[str] = Field(default=None, title='Телефон')
    email: Optional[str] = Field(default=None, title='Почта')
    contact_name: Optional[str] = Field(default=None, title='Контактное имя')
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        ),
        title='Дата создания')
    data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title='Дополнительные данные'
    )

    orders: List["Order"] = Relationship(back_populates="client", cascade_delete=True)


class OrderStatus(str, Enum):
    NEW = "new"
    NOTIFIED = "notified"
    PROCESSING = "processing"
    COMPLETED = "completed"
    SENT = "sent"
    CANCELLED = "cancelled"

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, title='Название')
    client_id: int = Field(
        foreign_key="clients.id",
        ondelete="CASCADE",
        index=True,
        title='Заказчик'
    )
    status: OrderStatus = Field(
        default=OrderStatus.NEW,
        index=True, title='Статус'
    )
    creator_id: Optional[int] = Field(
        default=None,
        foreign_key="user.id",  # ОБЯЗАТЕЛЬНО
        title='Автор заказа'
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        ),
        title='Дата создания'
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=True,
            index=True  # Теперь индекс внутри колонки
        ),
        title='Дата завершения'
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        title='Дополнительные данные'
    )
    #если вы удалите заказ, SQLModel сама удалит все связанные с ним олиго, чтобы в базе не оставалось "сирот".
    oligos: List["Oligo"] = Relationship(back_populates="order", cascade_delete=True)
    client: "Client" = Relationship(back_populates="orders")
    creator: Optional["User"] = Relationship(back_populates="orders")



@event.listens_for(Oligo.status, "set")
def receive_status_change(target, value, oldvalue, initiator):
    """
    Автоматически создает запись в OligoHistory при изменении статуса в объекте Oligo.
    """
    if value != oldvalue:  # Логируем только если статус действительно изменился
        # Проверяем, есть ли уже сессия, чтобы добавить запись истории
        session = Session.object_session(target)
        if session:
            new_history = OligoHistory(oligo_id=target.id, status=value)
            session.add(new_history)


@event.listens_for(Session, "before_commit")
def check_order_completion(session):
    """
    Срабатывает один раз перед коммитом.
    Проверяет все затронутые заказы и пересчитывает их статусы на основе олигонуклеотидов.
    """
    updated_order_ids = set()

    # Собираем все order_id, у которых изменились олигонуклеотиды
    for obj in list(session.dirty) + list(session.new):
        if isinstance(obj, Oligo):
            updated_order_ids.add(obj.order_id)

    for order_id in updated_order_ids:
        if order_id is None:
            continue

        # Получаем сам заказ, чтобы проверить его текущие намерения
        order = session.get(Order, order_id)
        if not order:
            continue

        # КРИТИЧЕСКИЙ ФИКС: Если заказ принудительно отменен, триггер не должен его пересчитывать
        if order.status == OrderStatus.CANCELLED:
            continue

        # Считаем количество олигонуклеотидов в разных технологических статусах
        total_count = session.scalar(
            select(func.count(Oligo.id))
            .where(Oligo.order_id == order_id)
        ) or 0

        completed_count = session.scalar(
            select(func.count(Oligo.id))
            .where(Oligo.order_id == order_id)
            .where(Oligo.status == OligoStatus.COMPLETED)
        ) or 0

        sent_count = session.scalar(
            select(func.count(Oligo.id))
            .where(Oligo.order_id == order_id)
            .where(Oligo.status == OligoStatus.SENT)
        ) or 0

        new_count = session.scalar(
            select(func.count(Oligo.id))
            .where(Oligo.order_id == order_id)
            .where(Oligo.status == OligoStatus.NEW)
        ) or 0

        # --- ЛОГИКА ОПРЕДЕЛЕНИЯ СТАТУСА ЗАКАЗА ---

        # 1. Если ВСЕ олигонуклеотиды отправлены (или смесь отправленных и завершенных)
        # и менеджер переводит заказ в SENT, триггер подтверждает этот статус
        if sent_count == total_count or (
                sent_count + completed_count == total_count and order.status == OrderStatus.SENT):
            order.status = OrderStatus.SENT

        # 2. Если все позиции физически готовы в лаборатории (COMPLETED)
        elif completed_count == total_count:
            order.status = OrderStatus.COMPLETED
            if not order.completed_at:
                order.completed_at = datetime.now(timezone.utc)

        # 3. Если абсолютно все позиции новые (производство еще не началось)
        elif new_count == total_count:
            order.status = OrderStatus.NEW
            order.completed_at = None

        # 4. Во всех остальных случаях (часть в синтезе, часть сушится, часть готова)
        else:
            order.status = OrderStatus.PROCESSING
            order.completed_at = None


def check_order_completion_(session):
    """
    Срабатывает один раз перед коммитом.
    Проверяет все затронутые заказы и закрывает их, если все олиго FIN.
    """
    updated_order_ids = set()
    for obj in list(session.dirty) + list(session.new):
        if isinstance(obj, Oligo):
            updated_order_ids.add(obj.order_id)

    for order_id in updated_order_ids:
        if order_id is None: continue

        not_finished = session.scalar(
            select(func.count(Oligo.id))
            .where(Oligo.order_id == order_id)
            .where(Oligo.status != OligoStatus.COMPLETED)
        )
        new_count = session.scalar(
            select(func.count(Oligo.id))
            .where(Oligo.order_id == order_id)
            .where(Oligo.status == OligoStatus.NEW)
        )
        total_count = session.scalar(
            select(func.count(Oligo.id))
            .where(Oligo.order_id == order_id)
        )

        if not_finished == 0:
            order = session.get(Order, order_id)
            if order:
                order.status = OrderStatus.COMPLETED
                order.completed_at = datetime.now(timezone.utc)
        elif new_count == total_count:
            order = session.get(Order, order_id)
            if order:
                order.status = OrderStatus.NEW
        else:
            order = session.get(Order, order_id)
            if order:
                order.status = OrderStatus.PROCESSING
