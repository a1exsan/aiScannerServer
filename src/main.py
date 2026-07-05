from nicegui import app, ui
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from src.ai.recognition.ticket.easyOCR_model import easyOCRreader
from src.orm.models import engine
from sqlmodel import Session
from src.orm.db_search import materialsService

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
        print(result.get('text', ''))
        rowdata = service.advanced_fuzzy_search(result.get('text', ''), treshold=65.0, limit=3)
        for row in rowdata:
            print(row)
        if rowdata:
            result['text'] = rowdata[0]['name']

    return JSONResponse(result)

ui.run(host='0.0.0.0', port=8080, reload=True)