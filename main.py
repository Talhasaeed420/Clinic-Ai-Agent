from fastapi import FastAPI
from routers import clinic, callcenter
from database import lifespan

app = FastAPI(lifespan=lifespan)

app.include_router(clinic.router, prefix="/api", tags=["Clinic"])
app.include_router(callcenter.router, tags=["Call Center"])
