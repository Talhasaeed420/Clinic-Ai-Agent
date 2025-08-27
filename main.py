from log_config.logging_config import setup_logging
setup_logging()
from fastapi import FastAPI
from routers import clinic, call_center, bot_clinic
from database import lifespan


app = FastAPI(lifespan=lifespan)

app.include_router(clinic.router, tags=["Clinic"])
app.include_router(bot_clinic.router, tags=["Bot Configs"])
app.include_router(call_center.router, tags=["Call Center"])
