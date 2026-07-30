"""
Comprehensive error handling utilities for ONGC IntelliAssist backend.
Prevents backend crashes during answer generation.
"""
import logging
import functools
from typing import Any, Callable

log = logging.getLogger("ongc.errors")


class BackendError(Exception):
    """Base exception for backend errors."""
    pass


class LLMTimeoutError(BackendError):
    """Raised when LLM (Ollama/Groq) times out."""
    pass


class RetrieverError(BackendError):
    """Raised when vector DB retrieval fails."""
    pass


class VectorDBError(BackendError):
    """Raised when FAISS/Chroma operations fail."""
    pass


class DatabaseConnectionError(BackendError):
    """Raised when database connection fails."""
    pass


class EmbeddingError(BackendError):
    """Raised when embedding generation fails."""
    pass


class StreamingError(BackendError):
    """Raised when streaming response fails."""
    pass


def safe_async_operation(
    fallback_value: Any = None,
    error_message: str = "Operation failed",
    log_errors: bool = True,
):
    """
    Decorator for async operations that catches all exceptions
    and returns a fallback value instead of crashing.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except LLMTimeoutError as e:
                if log_errors:
                    log.warning(f"LLM timeout in {func.__name__}: {e}")
                return fallback_value
            except RetrieverError as e:
                if log_errors:
                    log.warning(f"Retriever error in {func.__name__}: {e}")
                return fallback_value
            except VectorDBError as e:
                if log_errors:
                    log.warning(f"Vector DB error in {func.__name__}: {e}")
                return fallback_value
            except DatabaseConnectionError as e:
                if log_errors:
                    log.error(f"Database connection error in {func.__name__}: {e}")
                return fallback_value
            except EmbeddingError as e:
                if log_errors:
                    log.warning(f"Embedding error in {func.__name__}: {e}")
                return fallback_value
            except StreamingError as e:
                if log_errors:
                    log.warning(f"Streaming error in {func.__name__}: {e}")
                return fallback_value
            except Exception as e:
                if log_errors:
                    log.exception(f"Unexpected error in {func.__name__}: {e}")
                return fallback_value
        return wrapper
    return decorator


def safe_sync_operation(
    fallback_value: Any = None,
    error_message: str = "Operation failed",
    log_errors: bool = True,
):
    """
    Decorator for sync operations that catches all exceptions
    and returns a fallback value instead of crashing.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except LLMTimeoutError as e:
                if log_errors:
                    log.warning(f"LLM timeout in {func.__name__}: {e}")
                return fallback_value
            except RetrieverError as e:
                if log_errors:
                    log.warning(f"Retriever error in {func.__name__}: {e}")
                return fallback_value
            except VectorDBError as e:
                if log_errors:
                    log.warning(f"Vector DB error in {func.__name__}: {e}")
                return fallback_value
            except DatabaseConnectionError as e:
                if log_errors:
                    log.error(f"Database connection error in {func.__name__}: {e}")
                return fallback_value
            except EmbeddingError as e:
                if log_errors:
                    log.warning(f"Embedding error in {func.__name__}: {e}")
                return fallback_value
            except Exception as e:
                if log_errors:
                    log.exception(f"Unexpected error in {func.__name__}: {e}")
                return fallback_value
        return wrapper
    return decorator


def classify_exception(exc: Exception) -> BackendError:
    """Classify an exception into a specific BackendError type."""
    exc_str = str(exc).lower()
    
    # LLM timeouts
    if any(kw in exc_str for kw in ["timeout", "timed out", "deadline"]):
        if "ollama" in exc_str or "groq" in exc_str or "llm" in exc_str:
            return LLMTimeoutError(str(exc))
    
    # Vector DB errors
    if any(kw in exc_str for kw in ["faiss", "chroma", "vector", "embedding"]):
        return VectorDBError(str(exc))
    
    # Database errors
    if any(kw in exc_str for kw in ["database", "sqlite", "connection", "locked"]):
        return DatabaseConnectionError(str(exc))
    
    # Streaming errors
    if any(kw in exc_str for kw in ["stream", "broken pipe", "connection reset"]):
        return StreamingError(str(exc))
    
    # Default
    return BackendError(str(exc))
