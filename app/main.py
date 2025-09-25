from fastapi import FastAPI
from app.routers import content
from app.routers import frequency
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        msg = detail.get("message", "Error")
        page = detail.get("page")
        limit = detail.get("limit")
        total = detail.get("total")
    else:
        msg = str(detail)
        page = None
        limit = None
        total = None

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "message": "Failure",
            "data": None,
            "error": True,
            "error_message": msg,
            "page": page,
            "limit": limit,
            "total": total
        }
    )

app.include_router(content.router)
app.include_router(frequency.router)

@app.get("/")
def root():
    return {"message": "Hello World!"}
