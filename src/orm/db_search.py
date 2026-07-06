from typing import Optional, Dict, Any
from sqlmodel import Session, select
from src.orm.models import Reagent, ReagentLot, transactionType, ReagentTransaction
from rapidfuzz import process, fuzz


class materialsService:
    def __init__(self, session: Session):
        # Сервис просто сохраняет ссылку на сессию, созданную FastAPI
        self.session = session

    def advanced_fuzzy_search(self, query_text: str, limit: int = 3, treshold: float = 65.0):
        query = query_text.lower().replace("\n", " ").strip()
        if not query:
            return []

        try:
            # 1. Сверхбыстрая выгрузка легких данных
            raw_products = self.session.exec(
                select(Reagent.id, Reagent.name)
                .where(Reagent.group_id != None)
            ).all()
            if not raw_products:
                return []

            # 2. Карта соответствия имен и ID
            id_map = {p.name.lower(): p.id for p in raw_products if p.name}
            choices = list(id_map.keys())

            # 3. Движок RapidFuzz
            fuzzy_results = process.extract(
                query,
                choices,
                #scorer=fuzz.token_set_ratio,
                scorer=fuzz.WRatio,
                limit=limit,
                score_cutoff=treshold
            )

            if not fuzzy_results:
                return []

            # 4. Собираем ID победителей
            matched_ids = [id_map[matched_name] for matched_name, score, index in fuzzy_results]

            # 5. Вытаскиваем полные объекты SQLModel одним запросом IN
            statement = select(Reagent).where(Reagent.id.in_(matched_ids))
            db_products = self.session.exec(statement).all()

            db_products_dict = {p.id: p for p in db_products}

            # 6. Восстанавливаем порядок сортировки по релевантности
            ordered_results = []
            for matched_name, score, index in fuzzy_results:
                p_id = id_map[matched_name]
                if p_id in db_products_dict:
                    product = db_products_dict[p_id]
                    product_dict = product.model_dump()
                    product_dict["fuzzy_score"] = round(score, 1)
                    ordered_results.append(product_dict)

            return ordered_results

        except Exception as e:
            print(f"❌ [Ошибка Сервиса БД]: {str(e)}", flush=True)
            return []

    def get_reagent_quantity(self, id):
        statement = select(Reagent).where(Reagent.id == id)
        reagent = self.session.exec(statement).unique().first()
        if reagent:
            q = sum(lot.current_stock for lot in reagent.lots)
            formatted_q = f"{round(q, 4):g}"
            return f'{formatted_q} {reagent.unit}'
        else:
            return '0 units'

    def consume_reagent_auto(self, reagent_id: int, total_amount: float, comment: str = None):
        """Списание реагента по всем доступным лотам (FIFO)"""
        statement = select(ReagentLot).where(
            ReagentLot.reagent_id == reagent_id,
            ReagentLot.current_stock > 0
        ).order_by(ReagentLot.created_at)

        lots = self.session.exec(statement).all()
        remaining = abs(total_amount)

        for lot in lots:
            if remaining <= 0:
                break

            can_take = min(lot.current_stock, remaining)

            self.add_transaction(
                lot_id=lot.id,
                t_type=transactionType.CONSUMPTION,
                amount=-can_take,
                comment=f"{comment}"
            )
            remaining -= can_take
        return remaining

    def add_transaction(
            self,
            lot_id: int,
            t_type: transactionType,
            amount: float,
            user_id: Optional[int] = None,
            map_id: Optional[int] = None,
            comment: Optional[str] = None
    ) -> ReagentTransaction:
        """Регистрирует движение и обновляет текущий остаток лота"""
        db_lot = self.session.get(ReagentLot, lot_id)
        if not db_lot:
            raise ValueError(f"Партия ID {lot_id} не найдена")

        user_id = 1

        transaction = ReagentTransaction(
            lot_id=lot_id,
            type=t_type,
            amount=amount,
            user_id=user_id,
            map_id=map_id,
            comment=comment
        )

        db_lot.current_stock += amount

        self.session.add(transaction)
        self.session.add(db_lot)
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    def create_lot(self, reagent_id: int, lot_data: Dict[str, Any]) -> ReagentLot:
        user_id = 1

        # СОЗДАНИЕ НОВОГО ЛОТА
        db_lot = ReagentLot(**lot_data, reagent_id=reagent_id)
        # Ставим 0, так как add_transaction прибавит количество к текущему остатку
        db_lot.current_stock = 0

        self.session.add(db_lot)
        self.session.flush()

        self.add_transaction(
            lot_id=db_lot.id,
            t_type=transactionType.INCOMING,
            amount=db_lot.initial_stock,
            comment="mobile incoming",
            user_id=user_id
        )

        self.session.commit()
        self.session.refresh(db_lot)
        return db_lot