from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from platform_common.middleware.request_id_middleware import RequestIDMiddleware
from platform_common.exception_handling.handlers import add_exception_handlers
from app.api.router.health_check import router as health_router
from app.api.router.notification_router import router as notification_router
from strawberry.fastapi import GraphQLRouter

app = FastAPI(title="Notification Management API", version="1.0.0")


origins = [
    "http://ed-user-management:5003",
    "http://localhost:5173",  # common React dev port
    "http://127.0.0.1:5173",
    # "https://my-production-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # <-- your list here
    allow_credentials=True,  # <-- whether to expose cookies/auth headers
    allow_methods=["*"],  # <-- GET, POST, PUT, DELETE, etc
    allow_headers=["*"],  # <-- allow all headers (Authorization, Content-Type…)
)

app.add_middleware(RequestIDMiddleware)
add_exception_handlers(app)

# REST endpoints
app.include_router(health_router, prefix="/api/health", tags=["Health"])
app.include_router(
    notification_router, prefix="/api/notification", tags=["Notification"]
)
