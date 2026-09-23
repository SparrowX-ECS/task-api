FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TASK_API_DATABASE_URL=sqlite:////data/task.db
WORKDIR /app
RUN useradd --create-home --uid 10001 appuser && mkdir /data && chown appuser:appuser /data
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py __init__.py ./
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
