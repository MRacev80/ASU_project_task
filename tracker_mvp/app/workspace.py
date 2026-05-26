import json
import uuid
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
STATE_FILE = DATA_DIR / "app_state.json"

PROJECT_DIRS = [
    "documents",
    "archive",
    "backup",
    "exports",
    "agents/inbox",
    "agents/work",
    "agents/outbox",
    "agents/logs",
]


def ensure_app_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_state() -> dict:
    ensure_app_data_dir()
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state: dict) -> None:
    ensure_app_data_dir()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_active_workspace() -> Path | None:
    path = load_state().get("active_workspace")
    if not path:
        return None
    workspace = Path(path)
    return workspace if workspace.exists() else None


def set_active_workspace(path: str | Path) -> Path:
    workspace = Path(path).expanduser().resolve()
    state = load_state()
    state["active_workspace"] = str(workspace)
    save_state(state)
    return workspace


def workspace_has_manifest(path: str | Path) -> bool:
    return (Path(path) / "project_config.json").exists()


def create_workspace(path: str | Path, *, project_name: str, customer: str = "", automation_object: str = "") -> Path:
    workspace = Path(path).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    for relative in PROJECT_DIRS:
        (workspace / relative).mkdir(parents=True, exist_ok=True)

    now = datetime.utcnow().isoformat(timespec="seconds")
    config_path = workspace / "project_config.json"
    if not config_path.exists():
        config = {
            "project_id": str(uuid.uuid4()),
            "project_name": project_name,
            "customer": customer,
            "automation_object": automation_object,
            "database": "tracker.sqlite",
            "documents_dir": "documents",
            "archive_dir": "archive",
            "backup_dir": "backup",
            "agents_dir": "agents",
            "created_at": now,
            "updated_at": now,
            "schema_version": 1,
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    context_path = workspace / "project_context.md"
    if not context_path.exists():
        context_path.write_text(
            f"""# Контекст проекта

## Объект
{automation_object or "Не указан"}

## Заказчик
{customer or "Не указан"}

## Цель проекта
Описать цель проекта.

## Текущая стадия
Не указана.

## Главные документы
- documents/

## Текущий фокус
Заполнить карточку проекта и собрать исходные данные.

## Ограничения
Не указаны.

## Открытые вопросы
- Уточнить состав документации.
""",
            encoding="utf-8",
        )

    rules_path = workspace / "agent_rules.md"
    if not rules_path.exists():
        rules_path.write_text(
            """# Правила работы агента

## Можно

- читать `project_config.json`;
- читать `project_context.md`;
- читать документы из `documents/`;
- создавать временные файлы в `agents/work/`;
- сохранять результаты в `agents/outbox/`;
- писать логи в `agents/logs/`.

## Нельзя

- напрямую менять `tracker.sqlite`;
- удалять или перезаписывать документы;
- переносить файлы в архив без подтверждения человека;
- менять `project_config.json` без подтверждения;
- закрывать задачи без приемки человеком;
- считать результаты агента утвержденными.

## Результаты

Все результаты агента должны быть предложениями и сохраняться в `agents/outbox/`.
""",
            encoding="utf-8",
        )

    set_active_workspace(workspace)
    return workspace


def open_workspace(path: str | Path) -> Path:
    workspace = Path(path).expanduser().resolve()
    if not workspace.exists():
        raise FileNotFoundError(f"Папка не найдена: {workspace}")
    if not workspace_has_manifest(workspace):
        raise FileNotFoundError(f"В папке нет project_config.json: {workspace}")
    set_active_workspace(workspace)
    return workspace


def get_database_path() -> Path:
    workspace = get_active_workspace()
    if workspace is None:
        return DATA_DIR / "tracker.sqlite"
    config_path = workspace / "project_config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            database = config.get("database", "tracker.sqlite")
            return workspace / database
        except json.JSONDecodeError:
            pass
    return workspace / "tracker.sqlite"
