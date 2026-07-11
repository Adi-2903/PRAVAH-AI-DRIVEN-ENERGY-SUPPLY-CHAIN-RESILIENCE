FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The agent imports the frozen contracts from the repo-root `shared` package.
# When deploying, build with the repo root as context and copy shared/ in, or
# mount it, so `from shared.schemas...` resolves (see main.py sys.path note).

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
