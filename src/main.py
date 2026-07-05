from nicegui import app, ui
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from src.ai.recognition.ticket.easyOCR_model import easyOCRreader
from src.orm.models import engine

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
    return JSONResponse(result)

ui.run(host='0.0.0.0', port=8080, reload=True)