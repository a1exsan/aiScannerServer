from sqlmodel import Session, select
from src.orm.models import Reagent
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
                scorer=fuzz.token_set_ratio,
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