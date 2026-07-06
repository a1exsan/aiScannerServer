from nicegui import app, ui
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from src.ai.recognition.ticket.easyOCR_model import easyOCRreader
from src.orm.models import engine
from sqlmodel import Session
from src.orm.db_search import materialsService
import json
from datetime import datetime

fastapi_app = FastAPI()
app.mount('/api', fastapi_app)
ai_reader = easyOCRreader()

@fastapi_app.post('/upload')
async def upload_file(request: Request):
    try:
        image_data = await request.body()
    except Exception as e:
        return JSONResponse(content={'status': 'next', 'message': 'Обрыв связи'})

    if len(image_data) == 0:
        return JSONResponse(content={'status': 'next', 'message': 'Пустой кадр'})

    result = await run_in_threadpool(ai_reader.recognise, image_data)

    with Session(engine) as session:
        service = materialsService(session)
        rowdata = service.advanced_fuzzy_search(result.get('text', ''), treshold=50.0, limit=5)
        if rowdata:
            result['rowdata'] = rowdata
            result['text'] = f"[{rowdata[0]['id']}] {rowdata[0]['name']}"
        else:
            #result['text'] = f'Совпадений в базе не найдено'
            pass

    return JSONResponse(result)


@fastapi_app.post('/quantity')  # или @app.post в зависимости от роутинга NiceGUI
async def get_quantity(request: Request):
    try:
        # 1. Получаем сырые байты тела запроса
        body_bytes = await request.body()

        # 2. Декодируем байты в строку и парсим JSON в Python-словарь
        data = json.loads(body_bytes.decode('utf-8'))

        # 3. Достаем значение по ключу 'id' и принудительно переводим в int
        raw_id = data.get('id')
        if raw_id is None:
            return JSONResponse(content={'status': 'error', 'message': 'ID не передан'})

        item_id = int(raw_id)
        print(f"🎯 [Python] Успешно получен ID в виде int: {item_id} (тип: {type(item_id)})")

        with Session(engine) as session:
            service = materialsService(session)
            q_string = service.get_reagent_quantity(item_id)

        return JSONResponse(content={'quantity': q_string})

    except ValueError:
        return JSONResponse(content={'status': 'error', 'message': 'ID не является числом'})
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return JSONResponse(content={'status': 'next', 'message': 'Обрыв связи'})


@fastapi_app.post('/write_off')  # или @app.post для NiceGUI
async def write_off_material(request: Request):
    try:
        body_bytes = await request.body()
        data = json.loads(body_bytes.decode('utf-8'))
        item_id = int(data['id'])
        amount_to_remove = float(data['amount'])

        with Session(engine) as session:
            service = materialsService(session)
            remaining = service.consume_reagent_auto(item_id, amount_to_remove, comment='mobile write_off')
            if remaining == 0:
                q_string = service.get_reagent_quantity(item_id)
                return JSONResponse(content={'status': 'success', 'new_quantity': q_string})
            else:
                return JSONResponse(content={'status': 'no reagent', 'new_quantity': 0})

    except Exception as e:
        print(f"❌ Ошибка списания: {e}")
        return JSONResponse(content={'status': 'error', 'message': str(e)})


@fastapi_app.post('/income')  # или @app.post для NiceGUI
async def income_material(request: Request):
    try:
        body_bytes = await request.body()
        data = json.loads(body_bytes.decode('utf-8'))
        item_id = int(data['id'])
        amount_to_add = float(data['amount'])
        lot_number = data.get('lot_number')

        expiry = datetime.now()

        lot_data = {
            "lot_number": lot_number,
            "initial_stock": amount_to_add,
            "expiry_date": expiry
        }

        with Session(engine) as session:
            service = materialsService(session)
            r_lot = service.create_lot(item_id, lot_data)
            if r_lot:
                q_string = service.get_reagent_quantity(item_id)
                return JSONResponse(content={'status': 'success', 'new_quantity': q_string})
            else:
                return JSONResponse(content={'status': 'no lot creation', 'new_quantity': 0})

    except Exception as e:
        print(f"❌ Ошибка оприходования: {e}")
        return JSONResponse(content={'status': 'error', 'message': str(e)})


ui.run(host='0.0.0.0', port=8085, reload=False)