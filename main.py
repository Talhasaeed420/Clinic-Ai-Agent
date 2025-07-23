from fastapi import FastAPI
from routers import clinic, call_center
from database import lifespan

app = FastAPI(lifespan=lifespan)

app.include_router(clinic.router, prefix="/api", tags=["Clinic"])
app.include_router(call_center.router, tags=["Call Center"])
