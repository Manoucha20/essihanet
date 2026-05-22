from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import os
from routes.analyze import router as analyze_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# static folder
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# routes
app.include_router(analyze_router)

if __name__ == "__main__":
    import uvicorn
    
    server_port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=server_port)
