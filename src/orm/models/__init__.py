from pathlib import Path
from sqlmodel import SQLModel, create_engine
from.niceOligos import (Reagent, ReagentLot, ReagentTransaction, transactionType, ReagentGroup, reagentUnits, ReagentType,
                       SolutionModel)

# DB engene creation
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "niceoligos.db"
sqlite_url = f"sqlite:///{DB_PATH}"
engine = create_engine(sqlite_url, echo=False)

__all__ = ['engine', 'Reagent', 'ReagentLot', 'ReagentTransaction', 'transactionType', 'ReagentGroup', 'reagentUnits',
           'ReagentType', 'SolutionModel']