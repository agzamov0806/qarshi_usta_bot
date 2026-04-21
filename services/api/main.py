"""
REST API — botdan alohida ishlaydi (keyingi bosqich: buyurtmalar, auth).

Ishga tushirish:
  uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI

app = FastAPI(
    title="Usta xizmatlari API",
    version="0.1.0",
    description="Telegram bot bilan bir xil ma'lumotlar bazasidan keyinroq foydalaniladi.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "usta-api", "docs": "/docs"}
