import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import (staff, customers, bookings, services, checkout, reports,
                     auth, inventory, portal, products, coupons, payments, commissions,
                     hair_records)
from ws_manager import manager

Base.metadata.create_all(bind=engine)

app = FastAPI(title="美業 POS API", version="1.0.0")

logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "https://beauty-pos-peach.vercel.app",
    ],
    allow_origin_regex=r"^https://beauty-pos.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in [auth, staff, customers, bookings, services, checkout,
               reports, inventory, portal, products, coupons, payments, commissions,
               hair_records]:
    app.include_router(router.router, prefix="/api/v1")


@app.websocket("/ws/bookings")
async def ws_bookings(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "meta": {"errors": exc.errors()},
            }
        },
    )
