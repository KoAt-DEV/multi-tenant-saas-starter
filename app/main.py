from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, tenant, permission_check
from app.middleware.tenant_middleware import TenantMiddleware  

app = FastAPI(title="Full SaaS Project")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # in production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TenantMiddleware)


app.include_router(auth.router)
app.include_router(tenant.router)
app.include_router(permission_check.router) 


@app.get("/")
async def root(): 
    return {"status": "ok", "message": "API is running"}