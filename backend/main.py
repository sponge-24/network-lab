# backend/main.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import our new modules
from api import routes as api_routes
from core import state_manager, config

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events.
    """
    # On startup
    print("Starting up...")
    os.makedirs(config.OVERLAY_DIR, exist_ok=True) # Ensure overlay dir exists
    state_manager.load_state() # Load and prune state from file
    yield
    # On shutdown
    print("Shutting down...")
    state_manager.save_state() # Save state to file

# Create the FastAPI app instance
app = FastAPI(
    title="Network Lab API",
    lifespan=lifespan
)

# --- Add CORS Middleware ---
# This allows your React app (on localhost:3000)
# to talk to your backend (on localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], 
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods
    allow_headers=["*"], # Allow all headers
)

# --- Include API Routes ---
# All routes from api/routes.py will be included here
app.include_router(api_routes.router)

# --- Main entry point for Uvicorn ---
if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server...")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True # Enable reload for development
    )