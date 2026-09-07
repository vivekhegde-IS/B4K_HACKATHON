from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.exchanges import router as exchanges_router
from .api.inventory import router as inventory_router
from .api.orders import router as orders_router
from .api.products import router as products_router
from .api.returns import router as returns_router
from .database.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="RetailMate Backend",
    version="0.1.0",
    lifespan=lifespan,
)


def error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {"code": code, "message": message},
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    payload = exc.detail if isinstance(exc.detail, dict) else None
    if not payload or payload.get("success") is not False or "error" not in payload:
        payload = {
            "success": False,
            "error": {"code": "HTTP_ERROR", "message": str(exc.detail)},
        }
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_response(
        "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
        str(exc.detail),
        exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    fields = "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
        for error in exc.errors()
    )
    return error_response("VALIDATION_ERROR", fields, status.HTTP_422_UNPROCESSABLE_CONTENT)


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    return error_response(
        "INTERNAL_SERVER_ERROR",
        "An unexpected server error occurred.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DATABASE
# =========================================================

# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
    }


# =========================================================
# API ROUTERS
# =========================================================

app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(orders_router)
app.include_router(returns_router)
app.include_router(exchanges_router)