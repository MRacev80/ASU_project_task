from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.workspace import DATA_DIR, get_database_path


Base = declarative_base()
_engine = None
_session_local = None
_database_path = None


def get_engine():
    global _engine, _session_local, _database_path
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if _engine is None or _database_path != database_path:
        _database_path = database_path
        _engine = create_engine(
            f"sqlite:///{database_path}",
            connect_args={"check_same_thread": False},
        )
        _session_local = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_session_local():
    get_engine()
    return _session_local


def get_db():
    init_db()
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
