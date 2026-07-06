FROM python:3.12-slim

# Синхронизируем порт с ui.run(port=8085)
EXPOSE 8085

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Novosibirsk

# Папки кэша для ИИ-моделей (чтобы веса нейросетей не качались заново при каждом рестарте докера)
ENV EASYOCR_MODULE_DATA_DIR=/app/.cache/easyocr \
    PADDLEOCR_CONFIG_DIR=/app/.cache/paddleocr

WORKDIR /app

# УСТАНОВКА СИСТЕМНЫХ ЗАВИСИМОСТЕЙ ДЛЯ OPENCV, PADDLE, EASYOCR И ONNX
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Базовые библиотеки для компиляции некоторых python-пакетов из исходников:
    build-essential \
    gcc \
    # Жизненно важные библиотеки для работы OpenCV:
    libgl1 \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libsm6 \
    libexpat1 \
    # Библиотека OpenMP (критически важна для работы PaddlePaddle и ONNXRuntime на CPU):
    libgomp1 \
    # Дополнительные системные библиотеки:
    curl \
    && rm -rf /var/lib/apt/lists/*

# ШАГ КЭШИРОВАНИЯ PIP: Копируем и устанавливаем зависимости отдельно
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# КОПИРОВАНИЕ ИСХОДНОГО КОДА ПРОЕКТА
COPY . .

# Создаем директории для кэша моделей
RUN mkdir -p /app/.cache/easyocr /app/.cache/paddleocr

# ЗАПУСК СЕРВЕРА
CMD ["python", "-m", "src.main"]