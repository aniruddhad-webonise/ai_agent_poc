import logging
import sys
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import API_TITLE, API_DESCRIPTION, API_VERSION, LOG_LEVEL, LOG_FORMAT
from api.routes import router
from api.middleware import RequestLoggingMiddleware
from utils.errors import AIBotError

# Configure logging
logging_level = getattr(logging, LOG_LEVEL.upper())
if LOG_FORMAT.lower() == "json":
    # Configure JSON structured logging
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
else:
    # Configure standard logging
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include API routes
app.include_router(router)

# Exception handler
@app.exception_handler(AIBotError)
async def aibot_exception_handler(request: Request, exc: AIBotError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

# Root endpoint
@app.get("/")
async def root():
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "description": API_DESCRIPTION
    }

# Test client endpoint
@app.get("/test", response_class=HTMLResponse)
async def test_client():
    with open(os.path.join(os.path.dirname(__file__), "test_client.html")) as f:
        return f.read()

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {API_TITLE}")

if __name__ == "__main__":
    import uvicorn
    from config.settings import API_HOST, API_PORT
    
    uvicorn.run(
        "app:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )