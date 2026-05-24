# ── Local development image ────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source — in dev the volume mount overlays this, enabling hot-reload
COPY . .

EXPOSE 8000

# --reload watches for source changes inside the container
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
