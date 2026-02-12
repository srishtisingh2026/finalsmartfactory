from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --------------------------------------------------
# Correct absolute imports (AFTER app import)
# --------------------------------------------------
from routers.traces import router as traces_router
from routers.evaluations import router as evaluations_router
from routers.evaluators import router as evaluators_router
from routers.templates import router as templates_router
from routers.sessions import router as sessions_router
from routers.metrics import router as metrics_router
from routers.audit import router as audit_router

# --------------------------------------------------
# App initialization
# --------------------------------------------------
app = FastAPI(
    title="Smart Factory AI Backend",
    version="1.0.0",
)

# --------------------------------------------------
# CORS
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Register Routers
# --------------------------------------------------
app.include_router(traces_router, prefix="/traces", tags=["Traces"])
app.include_router(evaluations_router, prefix="/evaluations", tags=["Evaluations"])
app.include_router(evaluators_router, prefix="/evaluators", tags=["Evaluators"])
app.include_router(templates_router, prefix="/templates", tags=["Templates"])
app.include_router(sessions_router, prefix="/sessions", tags=["Sessions"])
app.include_router(metrics_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(audit_router)

# --------------------------------------------------
# Root endpoint
# --------------------------------------------------
@app.get("/")
def root():
    return {"message": "Smart Factory AI Backend Running!"}


# --------------------------------------------------
# Uvicorn entry for local debugging
# (IMPORTANT: put this at the BOTTOM)
# --------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
