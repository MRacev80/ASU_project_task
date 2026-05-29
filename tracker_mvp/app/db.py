from sqlalchemy import create_engine, text
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
    migrate_project_columns()
    migrate_procurement_columns()
    migrate_risk_columns()
    migrate_event_columns()
    migrate_project_phase_columns()
    migrate_technical_audit_columns()
    migrate_work_item_site_columns()
    migrate_procurement_site_columns()


def migrate_project_columns():
    columns = {
        "project_code": "VARCHAR DEFAULT ''",
        "contract_number": "VARCHAR DEFAULT ''",
        "current_milestone": "VARCHAR DEFAULT ''",
        "start_plan": "VARCHAR DEFAULT ''",
        "finish_plan": "VARCHAR DEFAULT ''",
        "start_fact": "VARCHAR DEFAULT ''",
        "finish_fact": "VARCHAR DEFAULT ''",
        "readiness_percent": "VARCHAR DEFAULT ''",
        "contract_amount": "VARCHAR DEFAULT ''",
        "budget_plan": "VARCHAR DEFAULT ''",
        "budget_actual": "VARCHAR DEFAULT ''",
        "designer": "VARCHAR DEFAULT ''",
        "programmer": "VARCHAR DEFAULT ''",
        "kip_master": "VARCHAR DEFAULT ''",
    }
    engine = get_engine()
    with engine.begin() as connection:
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(projects)"))}
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE projects ADD COLUMN {name} {definition}"))


def migrate_procurement_columns():
    columns = {
        "group_name": "VARCHAR DEFAULT ''",
        "row_order": "VARCHAR DEFAULT ''",
        "is_group_header": "VARCHAR DEFAULT ''",
        "supplier": "VARCHAR DEFAULT ''",
        "supply_comment": "TEXT DEFAULT ''",
        "order_date": "VARCHAR DEFAULT ''",
        "delivery_date": "VARCHAR DEFAULT ''",
        "updated_at": "DATETIME",
    }
    engine = get_engine()
    with engine.begin() as connection:
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(procurement_items)"))}
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE procurement_items ADD COLUMN {name} {definition}"))


def migrate_risk_columns():
    columns = {
        "risk_score": "VARCHAR DEFAULT ''",
        "risk_level": "VARCHAR DEFAULT ''",
        "linked_entity_type": "VARCHAR DEFAULT ''",
        "linked_entity_id": "VARCHAR DEFAULT ''",
    }
    engine = get_engine()
    with engine.begin() as connection:
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(risks)"))}
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE risks ADD COLUMN {name} {definition}"))


def migrate_event_columns():
    columns = {
        "source": "VARCHAR DEFAULT 'ui'",
        "before_state": "TEXT DEFAULT ''",
        "after_state": "TEXT DEFAULT ''",
    }
    engine = get_engine()
    with engine.begin() as connection:
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(events)"))}
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE events ADD COLUMN {name} {definition}"))


def migrate_project_phase_columns():
    columns = {
        "schedule_health": "VARCHAR DEFAULT 'gray'",
        "technical_health": "VARCHAR DEFAULT 'gray'",
        "risk_health": "VARCHAR DEFAULT 'gray'",
        "procurement_health": "VARCHAR DEFAULT 'gray'",
        "documentation_health": "VARCHAR DEFAULT 'gray'",
        "testing_health": "VARCHAR DEFAULT 'gray'",
        "progress_percent": "VARCHAR DEFAULT '0'",
        "summary": "TEXT DEFAULT ''",
        "gate_decision_by": "VARCHAR DEFAULT ''",
        "gate_decision_at": "VARCHAR DEFAULT ''",
    }
    engine = get_engine()
    with engine.begin() as connection:
        existing_tables = {row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        if "project_phases" not in existing_tables:
            return
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(project_phases)"))}
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE project_phases ADD COLUMN {name} {definition}"))


def migrate_technical_audit_columns():
    columns = {
        "audit_date": "VARCHAR DEFAULT ''",
        "open_findings_count": "VARCHAR DEFAULT '0'",
        "critical_findings_count": "VARCHAR DEFAULT '0'",
        "decision_comment": "TEXT DEFAULT ''",
    }
    engine = get_engine()
    with engine.begin() as connection:
        existing_tables = {row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        if "technical_audits" not in existing_tables:
            return
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(technical_audits)"))}
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE technical_audits ADD COLUMN {name} {definition}"))


def migrate_work_item_site_columns():
    """Привязка строк работ к площадкам и спецификациям.
    Добавляется к существующей таблице work_items без потери данных."""
    columns = {
        "site_id": "VARCHAR DEFAULT ''",
        "specification_id": "VARCHAR DEFAULT ''",
    }
    engine = get_engine()
    with engine.begin() as connection:
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(work_items)"))}
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE work_items ADD COLUMN {name} {definition}"))


def migrate_procurement_site_columns():
    """Привязка закупочных позиций к площадкам и спецификациям.
    Добавляется к существующей таблице procurement_items без потери данных."""
    columns = {
        "site_id": "VARCHAR DEFAULT ''",
        "specification_id": "VARCHAR DEFAULT ''",
    }
    engine = get_engine()
    with engine.begin() as connection:
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(procurement_items)"))}
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE procurement_items ADD COLUMN {name} {definition}"))
