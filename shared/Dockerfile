FROM python:3.10-slim

WORKDIR /app

COPY shared/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared

EXPOSE 8000
CMD ["uvicorn", "shared.main:app", "--host", "0.0.0.0", "--port", "8000"]
