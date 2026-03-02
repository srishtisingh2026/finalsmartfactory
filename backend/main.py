from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.traces import router as traces_router
from routers.evaluations import router as evaluations_router
from routers.evaluators import router as evaluators_router
from routers.templates import router as templates_router
from routers.sessions import router as sessions_router
from routers.metrics import router as metrics_router
from routers.audit import router as audit_router
from routers.prompts import router as prompts_router
from routers.rca import router as rca_router
app = FastAPI(
    title="Smart Factory AI Backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gentle-mud-0f818720f.1.azurestaticapps.net"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(traces_router, prefix="/traces")
app.include_router(evaluations_router, prefix="/evaluations")
app.include_router(evaluators_router, prefix="/evaluators")
app.include_router(templates_router, prefix="/templates")
app.include_router(sessions_router, prefix="/sessions")
app.include_router(metrics_router, prefix="/dashboard")
app.include_router(audit_router)
app.include_router(prompts_router)
app.include_router(rca_router, prefix="/rca")

@app.get("/")
def root():
    return {"message": "Smart Factory AI Backend is running 🚀"}