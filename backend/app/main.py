from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import Document, User
from app.routers import analytics, auth, chat, documents
from app.security import hash_password

import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
# Squash chatty third parties
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
log = logging.getLogger("ongc.main")


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
        if settings.database_url.startswith("sqlite"):
            conn.execute(text("PRAGMA journal_mode=WAL"))
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
        if "is_kb" not in cols_doc:
            conn.execute(text("ALTER TABLE documents ADD COLUMN is_kb BOOLEAN DEFAULT 0"))
        if "summary" not in cols_doc:
            conn.execute(text("ALTER TABLE documents ADD COLUMN summary TEXT"))
        conn.commit()

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.knowledge_base_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_db_dir.mkdir(parents=True, exist_ok=True)
    log.info(
        "Storage ready: DB=%s uploads=%s kb=%s vectors=%s",
        settings.database_url,
        settings.upload_dir,
        settings.knowledge_base_dir,
        settings.vector_db_dir,
    )

    with SessionLocal() as db:
        # Enforce the single-account deployment policy without dropping any
        # persisted reports or conversation history.
        from app.models import ChatSession, AuditLog as AuditLogModel, Feedback
        required_admin_email = (settings.bootstrap_admin_email or "admin@ongc.com").lower()
        required_admin_password = settings.bootstrap_admin_password or "Admin@12345"
        required_admin = db.query(User).filter(User.email == required_admin_email).first()
        if required_admin is None:
            required_admin = User(
                email=required_admin_email,
                full_name="ONGC Administrator",
                hashed_password=hash_password(required_admin_password),
                role="admin",
                is_active=True,
            )
            db.add(required_admin)
            db.flush()
        else:
            required_admin.full_name = "ONGC Administrator"
            required_admin.role = "admin"
            required_admin.is_active = True
            required_admin.hashed_password = hash_password(required_admin_password)

        accounts_to_remove = db.query(User).filter(User.id != required_admin.id).all()
        reassigned_user_ids = [account.id for account in accounts_to_remove]
        if reassigned_user_ids:
            db.query(Document).filter(Document.uploaded_by_id.in_(reassigned_user_ids)).update(
                {Document.uploaded_by_id: required_admin.id}, synchronize_session=False
            )
            db.query(ChatSession).filter(ChatSession.user_id.in_(reassigned_user_ids)).update(
                {ChatSession.user_id: required_admin.id}, synchronize_session=False
            )
            db.query(AuditLogModel).filter(AuditLogModel.user_id.in_(reassigned_user_ids)).update(
                {AuditLogModel.user_id: required_admin.id}, synchronize_session=False
            )
            db.query(Feedback).filter(Feedback.user_id.in_(reassigned_user_ids)).update(
                {Feedback.user_id: required_admin.id}, synchronize_session=False
            )
            for account in accounts_to_remove:
                db.delete(account)
            log.info("Account cleanup removed %s non-required account(s).", len(accounts_to_remove))
        db.commit()

        # ---- Step 1: Ensure admin account exists ----
        admin_user = None
        if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
            admin_user = (
                db.query(User)
                .filter(User.email == settings.bootstrap_admin_email.lower())
                .first()
            )
            if not admin_user:
                admin_user = User(
                    email=settings.bootstrap_admin_email.lower(),
                    full_name="ONGC Administrator",
                    hashed_password=hash_password(settings.bootstrap_admin_password),
                    role="admin",
                )
                db.add(admin_user)
                db.commit()
                db.refresh(admin_user)
                log.info("Bootstrapped admin user %s", settings.bootstrap_admin_email.lower())

        # ---- Step 2: If we have ANY other admin user, pick one as fallback owner ----
        if admin_user is None:
            admin_user = db.query(User).filter(User.role == "admin").order_by(User.id.asc()).first()

        # ---- Step 2.5: Delete all non-admin users (Issue 1 — admin-only system) ----
        if admin_user is not None:
            from app.models import ChatSession, ChatMessage, AuditLog as AuditLogModel, Feedback, RevokedToken
            non_admin_users = db.query(User).filter(User.role != "admin").all()
            if non_admin_users:
                non_admin_ids = [u.id for u in non_admin_users]
                # Reassign any documents from non-admin users to admin
                reassigned = (
                    db.query(Document)
                    .filter(Document.uploaded_by_id.in_(non_admin_ids))
                    .update({Document.uploaded_by_id: admin_user.id}, synchronize_session=False)
                )
                if reassigned:
                    log.info("Reassigned %s documents from non-admin users to admin_id=%s", reassigned, admin_user.id)
                # Delete feedback, messages, sessions, audit logs for non-admin users
                for uid in non_admin_ids:
                    user_sessions = db.query(ChatSession).filter(ChatSession.user_id == uid).all()
                    for sess in user_sessions:
                        db.query(Feedback).filter(
                            Feedback.message_id.in_(
                                db.query(ChatMessage.id).filter(ChatMessage.session_id == sess.id)
                            )
                        ).delete(synchronize_session=False)
                        db.query(ChatMessage).filter(ChatMessage.session_id == sess.id).delete(synchronize_session=False)
                    db.query(ChatSession).filter(ChatSession.user_id == uid).delete(synchronize_session=False)
                    db.query(AuditLogModel).filter(AuditLogModel.user_id == uid).delete(synchronize_session=False)
                for u in non_admin_users:
                    db.delete(u)
                db.commit()
                log.info("ISSUE 1: Deleted %s non-admin users: %s",
                         len(non_admin_users), [u.email for u in non_admin_users])

        # ---- Step 3: Repair KB documents that have uploaded_by_id = NULL ----
        # (BUG FIX: legacy KB uploads stored None; now we always assign admin)
        if admin_user is not None:
            orphan_kb_count = (
                db.query(Document)
                .filter(Document.is_kb == True, Document.uploaded_by_id.is_(None))
                .update({Document.uploaded_by_id: admin_user.id}, synchronize_session=False)
            )
            if orphan_kb_count:
                db.commit()
                log.info(
                    "PERSISTENCE REPAIR: Assigned uploaded_by_id=%s (%s) to %s orphan KB documents",
                    admin_user.id, admin_user.email, orphan_kb_count,
                )

        # ---- Step 4: Rebuild FAISS vector indexes IF DB has chunks but index files missing ----
        # This recovers from the shutil.rmtree bug: if docs+chunks exist in DB,
        # but FAISS index was wiped, rebuild it automatically at startup.
        from app.models import DocumentChunk
        from app.services.vector_db import rebuild_kb_index, rebuild_user_index
        from sqlalchemy import func

        # --- 4a: KB vector index ---
        kb_path = settings.vector_db_dir / "knowledge_vectors"
        kb_has_index_files = kb_path.exists() and (kb_path / "index.faiss").exists()
        kb_has_docs = (
            db.query(func.count(Document.id))
            .filter(Document.is_kb == True, Document.enabled == True)
            .scalar() or 0
        )
        kb_has_chunks = (
            db.query(func.count(DocumentChunk.id))
            .join(Document)
            .filter(Document.is_kb == True)
            .scalar() or 0
        )
        if kb_has_docs > 0 and kb_has_chunks > 0 and not kb_has_index_files:
            log.warning(
                "PERSISTENCE RECOVERY: KB has %s docs/%s chunks but no FAISS index at %s. Rebuilding now.",
                kb_has_docs, kb_has_chunks, kb_path,
            )
            vs = rebuild_kb_index(db)
            if vs is None:
                log.error("PERSISTENCE RECOVERY FAILED: rebuild_kb_index() returned None despite chunks existing.")
            else:
                log.info("PERSISTENCE RECOVERY SUCCESS: KB FAISS index rebuilt from DB.")
        elif kb_has_index_files:
            log.info(
                "PERSISTENCE OK: KB vector index already on disk (%s/%s docs in DB).",
                kb_path, kb_has_docs,
            )

        # --- 4b: Per-user upload vector indices ---
        user_ids_with_docs = (
            db.query(Document.uploaded_by_id)
            .filter(Document.is_kb == False, Document.uploaded_by_id.isnot(None))
            .distinct()
            .all()
        )
        for (uid,) in user_ids_with_docs:
            user_path = settings.vector_db_dir / "upload_vectors" / f"user_{uid}"
            user_has_index = user_path.exists() and (user_path / "index.faiss").exists()
            user_has_docs = (
                db.query(func.count(Document.id))
                .filter(Document.uploaded_by_id == uid, Document.is_kb == False, Document.enabled == True)
                .scalar() or 0
            )
            user_has_chunks = (
                db.query(func.count(DocumentChunk.id))
                .join(Document)
                .filter(Document.uploaded_by_id == uid, Document.is_kb == False)
                .scalar() or 0
            )
            if user_has_docs > 0 and user_has_chunks > 0 and not user_has_index:
                log.warning(
                    "PERSISTENCE RECOVERY: user_id=%s has %s docs/%s chunks but no FAISS index. Rebuilding now.",
                    uid, user_has_docs, user_has_chunks,
                )
                vs = rebuild_user_index(db, uid)
                if vs is None:
                    log.error(
                        "PERSISTENCE RECOVERY FAILED: rebuild_user_index(%s) returned None despite chunks existing.",
                        uid,
                    )
                else:
                    log.info("PERSISTENCE RECOVERY SUCCESS: user_id=%s FAISS index rebuilt from DB.", uid)
            elif user_has_index:
                log.info(
                    "PERSISTENCE OK: user_id=%s vector index already on disk (%s docs in DB).",
                    uid, user_has_docs,
                )

        if reassigned_user_ids:
            rebuild_user_index(db, required_admin.id)
            log.info("Account cleanup refreshed the administrator upload FAISS index.")

        # ---- Step 5: Summary counts ----
        from app.models import ChatSession, ChatMessage, AuditLog
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_docs = db.query(func.count(Document.id)).scalar() or 0
        total_sessions = db.query(func.count(ChatSession.id)).scalar() or 0
        total_messages = db.query(func.count(ChatMessage.id)).scalar() or 0
        log.info(
            "PERSISTENCE SUMMARY: users=%s docs=%s sessions=%s messages=%s audit=%s",
            total_users, total_docs, total_sessions, total_messages,
            db.query(func.count(AuditLog.id)).scalar() or 0,
        )


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
