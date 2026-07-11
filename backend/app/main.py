from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import User
from app.routers import analytics, auth, chat, documents
from app.security import hash_password


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if "*" in origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex="https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    
    # Perform database column migrations for ChatSession and Document
    with engine.connect() as conn:
        cursor = conn.execute(text("PRAGMA table_info(chat_sessions)"))
        cols = [row[1] for row in cursor.fetchall()]
        if "pinned" not in cols:
            conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN pinned BOOLEAN DEFAULT 0"))
        if "active_document_id" not in cols:
            conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN active_document_id INTEGER"))
        if "active_source" not in cols:
            conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN active_source VARCHAR(80)"))
            
        cursor_doc = conn.execute(text("PRAGMA table_info(documents)"))
        cols_doc = [row[1] for row in cursor_doc.fetchall()]
        if "enabled" not in cols_doc:
            conn.execute(text("ALTER TABLE documents ADD COLUMN enabled BOOLEAN DEFAULT 1"))
        if "summary" not in cols_doc:
            conn.execute(text("ALTER TABLE documents ADD COLUMN summary TEXT"))
        conn.commit()

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        if (
            settings.bootstrap_admin_email
            and settings.bootstrap_admin_password
            and not db.query(User).filter(User.email == settings.bootstrap_admin_email.lower()).first()
        ):
            db.add(
                User(
                    email=settings.bootstrap_admin_email.lower(),
                    full_name="ONGC Administrator",
                    hashed_password=hash_password(settings.bootstrap_admin_password),
                    role="admin",
                )
            )
            db.commit()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
