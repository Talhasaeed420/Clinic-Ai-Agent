from log_config.logging_config import setup_logging
setup_logging()
from fastapi import FastAPI
from routers import clinic, call_center, bot_clinic, doctors_data, bot_tools, vapi_chat,vapi_metric
from database import lifespan
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict later e.g. ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(clinic.router, tags=["Clinic"])
app.include_router(bot_clinic.router, tags=["Bot Configs"])
app.include_router(doctors_data.router, tags=["Doctors Data"])
# app.include_router(call_center.router, tags=["Call Center"])
app.include_router(bot_tools.router, tags=["Bot Tools"])
app.include_router(vapi_chat.router, tags=["VAPI Chat"])
app.include_router(vapi_metric.router, tags=["VAPI Metrics"])
