from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth, candidate, recruiter, admin
from app.api.routers import api_v1

app = FastAPI(title='FRAUMATCH API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth")
app.include_router(candidate.router, prefix="/candidate")
app.include_router(recruiter.router, prefix="/recruiter")
app.include_router(admin.router, prefix="/admin")
app.include_router(api_v1.router)

@app.get("/")
def root():
    return {"app": "FRAUMATCH API", "status": "ok"}
