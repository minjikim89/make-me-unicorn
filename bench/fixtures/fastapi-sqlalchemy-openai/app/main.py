from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import DEBUG
from app.db import Base, engine
from app.routers import ai, auth, export, notes

app = FastAPI(title="NoteBrain", debug=DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(notes.router, prefix="/notes", tags=["notes"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])
app.include_router(export.router, prefix="/export", tags=["export"])


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    import traceback

    return JSONResponse(status_code=500, content={"error": str(exc), "trace": traceback.format_exc()})


@app.get("/health")
def health():
    return {"ok": True}
