from nicegui import app, ui
from fastapi import Request, FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from src.ai.recognition.ticket.easyOCR_model import easyOCRreader
from src.orm.models import engine
from sqlmodel import Session
from src.orm.db_search import materialsService
import json
import os
from datetime import datetime

fastapi_app = FastAPI()
app.mount('/api', fastapi_app)
ai_reader = easyOCRreader()


API_SECRET_KEY = os.getenv("API_SECRET_KEY", "fallback_secure_token_default")

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized client")
    return x_api_key

fastapi_app.dependencies = [Depends(verify_api_key)]


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


@fastapi_app.post('/materials_query')
async def materials_query(request: Request):
    result = {'rowdata': [], 'text': ''}

    try:
        body_bytes = await request.body()
        data = json.loads(body_bytes.decode('utf-8'))
    except Exception as e:
        return JSONResponse(content={'status': 'next', 'message': 'Обрыв связи'}, status_code=400)

    with Session(engine) as session:
        service = materialsService(session)
        db_rows = service.advanced_fuzzy_search(data.get('query', ''), treshold=60.0, limit=5)

        if db_rows:
            for row in db_rows:
                row_dict = {
                        'id': row.get('id', ''),
                        'name': row.get('name', ''),
                        'unit': row.get('unit', ''),
                        'total_stock': row.get('total_stock', ''),
                    }

                # Добавляем в общий массив — ТЕПЕРЬ ПЕРЕДАЕТСЯ ВЕСЬ СПИСОК
                result['rowdata'].append(row_dict)

            # В служебный текст пишем, сколько всего совпадений мы передаем на телефон
            result['text'] = f"Найдено совпадений: {len(result['rowdata'])}"
        else:
            result['text'] = 'Совпадений в базе не найдено'

    # Отправляем на телефон полный JSON-объект со ВСЕМ списком материалов
    return JSONResponse(content=result)


@fastapi_app.post('/materials_group_content')
async def materials_group_content(request: Request):
    result = {'rowdata': [], 'text': ''}

    try:
        body_bytes = await request.body()
        data = json.loads(body_bytes.decode('utf-8'))
    except Exception as e:
        return JSONResponse(content={'status': 'next', 'message': 'Обрыв связи'}, status_code=400)

    if data:
        with Session(engine) as session:
            service = materialsService(session)
            rowdata = service.get_all_groups()
            out = [{'id': -1, 'group': 'Все материалы'}]
            if rowdata:
                out.extend([{'id': row['id'], 'group': row['name']} for row in rowdata])
            g_mapping = {i: row['id'] for i, row in enumerate(out)}

            rowdata = service.get_reagent_data(g_mapping[data.get('group_id', 0)])
            result['rowdata'] = rowdata
    return JSONResponse(content=result)



@fastapi_app.get('/materials_groups')  # Автоматический префикс /api добавится сервером
async def materials_groups(request: Request):

    with Session(engine) as session:
        service = materialsService(session)
        rowdata = service.get_all_groups()

    out = [{'id': -1, 'group': 'Все материалы'}]
    if rowdata:
        out.extend([{'id': row['id'], 'group': row['name']} for row in rowdata])
    return JSONResponse(content={'groups': out})



ui.run(host='0.0.0.0', port=8085, reload=True)