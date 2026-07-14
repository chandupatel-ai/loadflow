from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import (
    auth_router,
    roles_router,
    loads_router,
    compliance_router,
    rates_router,
    pod_router,
    dashboard_router,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LoadFlow API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the deployed frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(roles_router.router)
app.include_router(loads_router.router)
app.include_router(compliance_router.router)
app.include_router(rates_router.router)
app.include_router(pod_router.router)
app.include_router(dashboard_router.router)


@app.get("/")
def root():
    return {"service": "LoadFlow API", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}
