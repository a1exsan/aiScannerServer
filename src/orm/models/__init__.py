from sqlalchemy import event
from pathlib import Path
from sqlmodel import SQLModel, create_engine, inspect, text, Session
from .user import User, Role
from .orders import Order, Oligo, OligoHistory, OligoStatus, OrderStatus, Client
from .price import OligoPrice
from .oligomaps import (mapStatus, mapRow, oligoMap, measurementType, synthScheme, rowStatus,
                        lcmsData, chromData, opticalDens, MapEquipmentLink, MapConsumption, inputODmodel)
from .equipment import Equipment, EquipmentProtocolLink, Protocol, equipmentStatus, protocolType, equipmentType
from.materials import (Reagent, ReagentLot, ReagentTransaction, transactionType, ReagentGroup, reagentUnits, ReagentType,
                       SolutionModel)
from .modifications import Modification, Reaction, modificationType

# Находим корень проекта: это папка, где лежит папка 'src'
# __file__ — это NiceOligos/src/models/__init__.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "niceoligos.db"

# Создаем папку, если её нет (Linux friendly)
DB_DIR.mkdir(parents=True, exist_ok=True)

def show_tables():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("Таблицы в базе данных:")
    for table in tables:
        print(f" - {table}")

# Формируем абсолютный путь для SQLite
# Для Linux: sqlite:////home/user/project/data/niceoligos.db
sqlite_url = f"sqlite:///{DB_PATH}"

engine = create_engine(sqlite_url, echo=False) # echo=True покажет SQL в консоли
#show_tables()

# --- 1. ВКЛЮЧЕНИЕ КАСКАДНОГО УДАЛЕНИЯ (PRAGMA) ---
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")

    cursor.execute("PRAGMA journal_mode=DELETE;")
    #cursor.execute("PRAGMA journal_mode=WAL;")

    cursor.execute("PRAGMA synchronous=FULL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    #cursor.execute("PRAGMA busy_timeout=10000;")
    # 4. СИНХРОНИЗАЦИЯ С ДИСКОМ (Оптимальный баланс надежности и скорости)
    cursor.execute("PRAGMA synchronous=NORMAL;")

    cursor.close()

def _migrate_lcms_table():
    """Проверяет физическую структуру lcmsdata и добавляет file_path, если её нет."""
    with Session(engine) as session:
        try:
            # Тестовый холостой запрос к новой колонке
            session.execute(text("SELECT file_path FROM lcmsdata LIMIT 1;"))
        except Exception:
            # Если запрос упал — значит в sqlite-файле этой колонки ещё нет, накатываем
            print("===> [Инициализация СУБД]: Колонка 'file_path' не найдена. Обновляем таблицу lcmsdata...")
            try:
                # Изменяем структуру таблицы, добавляя поле
                session.connection().exec_driver_sql("ALTER TABLE lcmsdata ADD COLUMN file_path TEXT;")
                # Накатываем индекс для быстрого поиска архивов на диске
                session.connection().exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_lcmsdata_file_path ON lcmsdata (file_path);")
                session.commit()
                print("===> [Инициализация СУБД]: Структура lcmsdata успешно синхронизирована с Python-моделью!")
            except Exception as e:
                print(f"!!! Ошибка автоматической миграции lcmsdata: {e}")


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _migrate_lcms_table()


__all__ = ['User', 'Role', 'engine', 'create_db_and_tables', 'Order', 'SQLModel',
           'Oligo', 'OligoHistory', 'OligoStatus', 'OrderStatus', 'Client', 'OligoPrice',
           'mapStatus', 'mapRow', 'oligoMap', 'measurementType', 'synthScheme', 'rowStatus',
                        'lcmsData', 'chromData', 'opticalDens',
            'Equipment', 'EquipmentProtocolLink', 'Protocol', 'equipmentStatus', 'protocolType',
            'Reagent', 'ReagentLot', 'Modification', 'Reaction', 'modificationType',
            'ReagentTransaction', 'transactionType', 'MapEquipmentLink', 'ReagentGroup', 'reagentUnits', 'ReagentType',
           'equipmentType', 'MapConsumption', 'inputODmodel', 'SolutionModel'
           ]
