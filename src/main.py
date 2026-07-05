from nicegui import app, ui
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool

fastapi_app = FastAPI()
app.mount('/api', fastapi_app)

@fastapi_app.post('/upload')
async def upload_file(request: Request):
    try:
        image_data = await request.body()
    except Exception as e:
        return JSONResponse(content={'status': 'next', 'message': 'Обрыв связи'})

    if len(image_data) == 0:
        return JSONResponse(content={'status': 'next', 'message': 'Пустой кадр'})