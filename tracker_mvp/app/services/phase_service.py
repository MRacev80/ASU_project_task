import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EntityLink, ProjectPhase, Risk, TechnicalAudit


STANDARD_PHASES = [
    ("init", "Инициация"),
    ("tr", "ТР / Архитектура"),
    ("procurement", "Закупка"),
    ("software", "Разработка ПО"),
    ("docs", "Разработка РД"),
    ("fat", "Сборка / FAT"),
    ("shipment", "Отгрузка"),
    ("install", "Монтаж"),
    ("sat", "ПНР / SAT"),
    ("handover", "Сдача"),
    ("support", "Поддержка"),
]

PHASE_STATUSES = {"Не начато", "В работе", "Активная", "Параллельно", "Завершена", "Приостановлена"}
HEALTH_VALUES = {"green", "yellow", "red", "gray", "blue"}
HEALTH_LABELS = {
    "blue": "Активно",
    "gray": "Не начато",
    "green": "Норма",
    "yellow": "Есть риски",
    "red": "Проблема",
}
HEALTH_DESCRIPTIONS = {
    "blue": "идет активная работа или проверка",
    "gray": "работа еще не началась",
    "green": "отклонений нет",
    "yellow": "есть отклонения или принятые риски",
    "red": "есть критичная проблема или блокер",
}
READINESS_STATES = {"Не готово", "В работе", "Готово", "Риск"}
GATE_STATUSES = {
    "Не готов",
    "На аудите",
    "Разрешен",
    "Разрешен с рисками",
    "Стоп",
    # Старые значения оставлены для совместимости с уже сохраненными данными.
    "GO",
    "GO WITH RISKS",
    "STOP",
}

PHASE_TEMPLATES = {
    "init": {
        "input": [
            "Запрос заказчика, ТЗ или тендерная документация",
            "Договор или коммерческие условия",
            "Исходные ограничения по срокам, бюджету и объекту",
            "Контактные лица заказчика",
            "Известные стандарты заказчика",
        ],
        "output": [
            "Паспорт проекта",
            "Границы проекта",
            "Список ключевых участников",
            "Дорожная карта проекта",
            "Первичный реестр рисков",
            "Первичная оценка бюджета и трудозатрат",
            "Список открытых вопросов",
        ],
        "dod": [
            "Понятен объект автоматизации и состав работ",
            "Назначены РП и ключевые ответственные",
            "Зафиксировано, что входит и что не входит в проект",
            "Зафиксированы ключевые риски и неизвестные",
            "Принято решение о запуске проекта",
        ],
    },
    "tr": {
        "input": [
            "Утвержденное ТЗ",
            "P&ID, технологическое описание и перечень сигналов",
            "Требования заказчика к контроллерам, человеко-машинному интерфейсу, сетям и резервированию",
            "Стандарты заказчика",
            "Ограничения по оборудованию и поставщикам",
        ],
        "output": [
            "Технические решения",
            "Архитектура системы",
            "Выбор контроллера, человеко-машинного интерфейса и сетевого оборудования",
            "Предварительная спецификация оборудования",
            "Перечень интерфейсов",
            "Концепция резервирования",
            "Требования к ПО и рабочей документации",
            "Технические риски",
            "Уточненная оценка трудозатрат",
        ],
        "dod": [
            "Архитектура покрывает требования ТЗ",
            "Определены все внешние интерфейсы",
            "Понятны критичные технические риски",
            "Нет неразрешенных блокеров по выбору платформы",
            "Технический руководитель подтвердил реализуемость",
            "РП понимает влияние решений на сроки, закупки и испытания",
        ],
    },
    "procurement": {
        "input": [
            "Утвержденная спецификация оборудования",
            "Бюджет закупок",
            "Требования к аналогам и заменам",
            "Список поставщиков",
            "Сроки проекта и критический путь",
        ],
        "output": [
            "Оформленные закупочные позиции",
            "Статусы закупок",
            "Подтвержденные сроки поставки",
            "Список замен и согласований",
            "Результаты входного контроля",
            "Складской статус",
        ],
        "dod": [
            "Все критичные позиции определены",
            "Долгопоставляемые позиции выделены",
            "По каждой позиции есть статус",
            "Замены согласованы с техническим руководителем",
            "Риски по срокам поставки управляемы или явно приняты",
            "Оборудование готово к сборке или риски явно приняты",
        ],
    },
    "software": {
        "input": [
            "Утвержденное ТР",
            "Перечень входов/выходов",
            "Алгоритмы управления",
            "Матрица блокировок",
            "Принципы аварийных сообщений",
            "Требования к человеко-машинному интерфейсу",
            "Эмулятор или стенд, если нужен",
        ],
        "output": [
            "Зафиксированная версия ПО контроллера",
            "Экраны человеко-машинного интерфейса",
            "Перечень аварийных сообщений",
            "Список версий",
            "Результаты внутренних испытаний",
            "Список замечаний",
            "Черновик протокола заводских испытаний",
        ],
        "dod": [
            "Основные алгоритмы реализованы",
            "Блокировки и аварийные сценарии реализованы",
            "Критические аварии протестированы",
            "Критичных открытых дефектов нет",
            "Версия ПО зафиксирована",
            "Резервное копирование и восстановление проверены",
            "Технический руководитель подтвердил готовность к заводским испытаниям",
        ],
    },
    "docs": {
        "input": [
            "Утвержденное ТР",
            "Спецификация оборудования",
            "Архитектура системы",
            "Перечень входов/выходов",
            "Требования к шкафам, кабелям и монтажу",
            "Актуальные изменения по ПО и закупкам",
        ],
        "output": [
            "Схемы шкафов",
            "Кабельные журналы",
            "Монтажные схемы",
            "Спецификации",
            "Эксплуатационная документация",
            "Ведомость изменений",
            "Комплект рабочей документации к производству или монтажу",
        ],
        "dod": [
            "Документация полная для сборки и монтажа",
            "Нет противоречий со спецификацией и ПО",
            "Все изменения отражены",
            "Обозначения, маркировка и кабели согласованы",
            "Документация проверена техническим руководителем или ответственным инженером",
            "Комплект можно передавать в производство или монтаж",
        ],
    },
    "fat": {
        "input": [
            "Оборудование на складе",
            "Актуальная рабочая документация",
            "Актуальная версия ПО",
            "Сценарии заводских испытаний",
            "Список требований к проверке",
            "Стенд или условия проверки",
        ],
        "output": [
            "Собранные шкафы или система",
            "Протокол заводских испытаний",
            "Список дефектов",
            "Исправления",
            "Замечания по фактическому исполнению",
            "Решение о готовности к отгрузке",
        ],
        "dod": [
            "Шкафы собраны по рабочей документации",
            "Критичные сценарии заводских испытаний пройдены",
            "Критичных дефектов нет",
            "Список некритичных дефектов управляем",
            "Проверены отказные сценарии",
            "Проверено восстановление после потери питания",
            "РП и технический руководитель приняли решение по отгрузке",
        ],
    },
    "shipment": {
        "input": [
            "Заводские испытания приняты",
            "Упаковочный лист",
            "Подтвержденная комплектность оборудования",
            "Документы на отгрузку",
            "Готовность площадки или склада заказчика",
        ],
        "output": [
            "Отгруженное оборудование",
            "Транспортные документы",
            "Подтверждение доставки",
            "Перечень отгруженных позиций",
            "Зафиксированные повреждения или расхождения, если есть",
        ],
        "dod": [
            "Комплектность подтверждена",
            "Документы оформлены",
            "Логистика согласована",
            "Риски повреждения или потери управляемы",
            "Оборудование доставлено или передано перевозчику",
        ],
    },
    "install": {
        "input": [
            "Оборудование на объекте",
            "Монтажная документация",
            "Доступ на площадку",
            "Готовность строительной и электрической части",
            "План работ и требования охраны труда",
        ],
        "output": [
            "Смонтированное оборудование",
            "Подключенные кабели",
            "Пометки фактического исполнения",
            "Монтажные акты",
            "Список замечаний",
            "Готовность к пусконаладке",
        ],
        "dod": [
            "Оборудование установлено по рабочей документации",
            "Кабели подключены и промаркированы",
            "Заземление и питание проверены",
            "Сетевые подключения готовы",
            "Критичных монтажных замечаний нет",
            "Объект готов к пусконаладке",
        ],
    },
    "sat": {
        "input": [
            "Смонтированная система",
            "Актуальная версия ПО",
            "Сценарии испытаний на объекте",
            "Закрытые критичные дефекты заводских испытаний",
            "Готовность технологического оборудования",
            "Участие заказчика",
        ],
        "output": [
            "Протокол испытаний на объекте",
            "Закрытый или согласованный перечень остаточных замечаний",
            "Обученный персонал заказчика",
            "Резервная копия финальной версии",
            "Подтверждение работоспособности системы",
        ],
        "dod": [
            "Сценарии испытаний на объекте пройдены",
            "Система работает на объекте",
            "Аварийные и восстановительные сценарии проверены",
            "Критичных дефектов нет",
            "Заказчик принял результат или подписал перечень остаточных замечаний",
            "Финальная версия ПО и документов сохранена",
        ],
    },
    "handover": {
        "input": [
            "Испытания на объекте приняты",
            "Финальная рабочая и исполнительная документация",
            "Финальная версия ПО",
            "Протоколы заводских испытаний и испытаний на объекте",
            "Закрытые договорные обязательства или согласованный остаток",
        ],
        "output": [
            "Комплект исполнительной документации",
            "Архив исходников и резервных копий",
            "Акты сдачи",
            "Финальный отчет",
            "Уроки проекта",
            "Закрытие финансовых вопросов",
        ],
        "dod": [
            "Заказчик получил полный комплект",
            "Акты подписаны",
            "Исходники и резервные копии сохранены",
            "Обязательства закрыты",
            "Остаточные замечания перенесены в поддержку или гарантию",
        ],
    },
    "support": {
        "input": [
            "Сданный проект",
            "Гарантийные обязательства",
            "Список остаточных замечаний",
            "Контакты эксплуатации",
            "Соглашение о сроках реакции",
        ],
        "output": [
            "Журнал обращений",
            "Исправления",
            "Обновленные версии ПО и документов",
            "Отчеты по гарантийным случаям",
            "База уроков проекта",
        ],
        "dod": [
            "Обращения фиксируются",
            "Критичные проблемы закрываются в согласованные сроки",
            "Изменения версионируются",
            "Заказчик получает обновления",
            "Опыт проекта попадает в базу знаний",
        ],
    },
}

OLD_TEMPLATE_MARKERS = {
    "IO List",
    "Alarm philosophy",
    "PLC baseline",
    "SCADA screens",
    "Alarm list",
    "Test protocol",
    "FAT approved",
    "SAT procedures",
    "Все interlock реализованы",
    "Fail-safe поведение подтверждено",
    "Backup / restore проверен",
    "Punch list закрыт",
}


def ensure_project_phases(db: Session, project_id: str) -> list[ProjectPhase]:
    existing = db.scalars(
        select(ProjectPhase).where(ProjectPhase.project_id == project_id).order_by(ProjectPhase.order_index)
    ).all()
    existing_codes = {phase.code for phase in existing}
    for index, (code, name) in enumerate(STANDARD_PHASES, start=1):
        if code in existing_codes:
            continue
        # Фазы создаются автоматически, чтобы каждый проект сразу имел одинаковый управленческий скелет.
        db.add(
            ProjectPhase(
                project_id=project_id,
                code=code,
                name=name,
                order_index=str(index).zfill(2),
                status="В работе" if code == "init" else "Не начато",
                health="blue" if code == "init" else "gray",
                schedule_health="blue" if code == "init" else "gray",
                technical_health="gray",
                risk_health="gray",
                procurement_health="gray",
                documentation_health="gray",
                testing_health="gray",
                progress_percent="0",
                gate_status="Не готов",
                inputs=json.dumps(default_readiness_items(code, "input"), ensure_ascii=False),
                outputs=json.dumps(default_readiness_items(code, "output"), ensure_ascii=False),
                definition_of_done=json.dumps(default_dod_items(code), ensure_ascii=False),
            )
        )
    if len(existing_codes) != len(STANDARD_PHASES):
        db.flush()
    phases = db.scalars(select(ProjectPhase).where(ProjectPhase.project_id == project_id).order_by(ProjectPhase.order_index)).all()
    for phase in phases:
        backfill_phase_defaults(phase)
    return phases


def default_readiness_items(code: str, item_type: str) -> list[dict[str, str]]:
    titles = PHASE_TEMPLATES.get(code, {}).get(item_type, [])
    return [{"title": title, "state": "Не готово", "comment": "", "linked_entity_type": "", "linked_entity_id": ""} for title in titles]


def default_dod_items(code: str) -> list[dict[str, Any]]:
    return [
        {"title": title, "done": False, "comment": "", "linked_entity_type": "", "linked_entity_id": ""}
        for title in PHASE_TEMPLATES.get(code, {}).get("dod", [])
    ]


def backfill_phase_defaults(phase: ProjectPhase) -> None:
    # Обновляем только пустые или старые шаблонные списки; ручные правки пользователя не затираем.
    if should_replace_template(phase.inputs):
        phase.inputs = json.dumps(default_readiness_items(phase.code, "input"), ensure_ascii=False)
    if should_replace_template(phase.outputs):
        phase.outputs = json.dumps(default_readiness_items(phase.code, "output"), ensure_ascii=False)
    if should_replace_template(phase.definition_of_done):
        phase.definition_of_done = json.dumps(default_dod_items(phase.code), ensure_ascii=False)


def should_replace_template(value: str) -> bool:
    items = load_json_items(value)
    if not items:
        return True
    titles = {str(item.get("title") or "").strip() for item in items if isinstance(item, dict)}
    if not titles:
        return True
    return bool(titles & OLD_TEMPLATE_MARKERS)


def parse_items_text(raw_text: str, *, checklist: bool = False) -> list[dict[str, Any]]:
    items = []
    for line in (raw_text or "").splitlines():
        title = line.strip()
        if not title:
            continue
        parts = [part.strip() for part in title.split("|")]
        title = parts[0]
        state = normalize_choice(parts[1], READINESS_STATES, "Не готово") if len(parts) > 1 else "Не готово"
        comment = parts[2] if len(parts) > 2 else ""
        done = title.startswith("[x]") or title.startswith("[х]")
        title = title.removeprefix("[x]").removeprefix("[х]").removeprefix("[ ]").strip()
        if checklist:
            comment = parts[1] if len(parts) > 1 else ""
            items.append({"title": title, "done": done, "comment": comment, "linked_entity_type": "", "linked_entity_id": ""})
        else:
            items.append({"title": title, "state": state, "comment": comment, "linked_entity_type": "", "linked_entity_id": ""})
    return items


def load_json_items(value: str, default: list | None = None) -> list:
    try:
        loaded = json.loads(value or "[]")
    except json.JSONDecodeError:
        return default or []
    return loaded if isinstance(loaded, list) else default or []


def items_to_text(items: list[dict[str, Any]], *, checklist: bool = False) -> str:
    lines = []
    for item in items:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        if checklist:
            prefix = "[x] " if item.get("done") else "[ ] "
            comment = str(item.get("comment") or "").strip()
            lines.append(f"{prefix}{title}{' | ' + comment if comment else ''}")
        else:
            state = str(item.get("state") or "").strip()
            comment = str(item.get("comment") or "").strip()
            parts = [title]
            if state or comment:
                parts.append(state or "Не готово")
            if comment:
                parts.append(comment)
            lines.append(" | ".join(parts))
    return "\n".join(lines)


def clamp_percent(value: str) -> str:
    try:
        number = int(float(str(value or "0").replace(",", ".")))
    except ValueError:
        number = 0
    return str(min(100, max(0, number)))


def normalize_choice(value: str, allowed: set[str], default: str) -> str:
    return value if value in allowed else default


def phase_state(phase: ProjectPhase) -> dict[str, str]:
    return {
        "name": phase.name,
        "status": phase.status,
        "health": phase.health,
        "progress_percent": phase.progress_percent,
        "gate_status": phase.gate_status,
        "gate_comment": phase.gate_comment,
    }


def phase_view_model(db: Session, project_id: str, selected_phase_id: str = "") -> dict[str, Any]:
    phases = ensure_project_phases(db, project_id)
    selected = select_phase(phases, selected_phase_id)
    audits = db.scalars(
        select(TechnicalAudit).where(TechnicalAudit.project_id == project_id).order_by(TechnicalAudit.created_at.desc())
    ).all()
    latest_audits = {}
    for audit in audits:
        latest_audits.setdefault(audit.phase_id, audit)
    risk_counts = count_phase_risks(db, project_id)
    blocker_counts = count_phase_blockers(db, project_id)

    cards = []
    for phase in phases:
        dod_items = load_json_items(phase.definition_of_done)
        open_dod = sum(1 for item in dod_items if not item.get("done"))
        audit = latest_audits.get(phase.id)
        cards.append(
            {
                "phase": phase,
                "health_label": health_label(phase.health),
                "risk_count": risk_counts.get(phase.id, 0),
                "blocker_count": blocker_counts.get(phase.id, 0),
                "open_dod_count": open_dod,
                "open_audit_count": safe_int(getattr(audit, "open_findings_count", "0")) if audit else 0,
            }
        )

    selected_audit = latest_audits.get(selected.id) if selected else None
    return {
        "phases": phases,
        "phase_cards": cards,
        "selected_phase": selected,
        "selected_phase_inputs": load_json_items(selected.inputs if selected else ""),
        "selected_phase_outputs": load_json_items(selected.outputs if selected else ""),
        "selected_phase_dod": load_json_items(selected.definition_of_done if selected else ""),
        "selected_phase_inputs_text": items_to_text(load_json_items(selected.inputs if selected else "")),
        "selected_phase_outputs_text": items_to_text(load_json_items(selected.outputs if selected else "")),
        "selected_phase_dod_text": items_to_text(load_json_items(selected.definition_of_done if selected else ""), checklist=True),
        "selected_phase_audit": selected_audit,
        "project_health": project_health(selected),
        "phase_risks": linked_phase_risks(db, project_id, selected.id if selected else ""),
        "health_options": health_options(),
    }


def select_phase(phases: list[ProjectPhase], selected_phase_id: str = "") -> ProjectPhase | None:
    if selected_phase_id:
        for phase in phases:
            if phase.id == selected_phase_id or phase.code == selected_phase_id:
                return phase
    for phase in phases:
        if phase.status not in {"Завершена", "Не начато"}:
            return phase
    return phases[0] if phases else None


def project_health(phase: ProjectPhase | None) -> list[dict[str, str]]:
    if not phase:
        return []
    return [
        {"label": "Сроки", "value": health_label(phase.schedule_health), "tone": phase.schedule_health},
        {"label": "Техника", "value": health_label(phase.technical_health), "tone": phase.technical_health},
        {"label": "Риски", "value": health_label(phase.risk_health), "tone": phase.risk_health},
        {"label": "Закупки", "value": health_label(phase.procurement_health), "tone": phase.procurement_health},
        {"label": "Документы", "value": health_label(phase.documentation_health), "tone": phase.documentation_health},
        {"label": "Испытания", "value": health_label(phase.testing_health), "tone": phase.testing_health},
    ]


def health_label(value: str) -> str:
    return HEALTH_LABELS.get(value, value or "Не указано")


def health_options() -> list[dict[str, str]]:
    return [
        {"value": value, "label": HEALTH_LABELS[value], "description": HEALTH_DESCRIPTIONS[value]}
        for value in ["gray", "blue", "green", "yellow", "red"]
    ]


def count_phase_risks(db: Session, project_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    links = db.scalars(select(EntityLink).where(EntityLink.project_id == project_id)).all()
    for link in links:
        phase_id = ""
        if link.source_type == "phase" and link.target_type == "risk":
            phase_id = link.source_id
        elif link.target_type == "phase" and link.source_type == "risk":
            phase_id = link.target_id
        if phase_id:
            counts[phase_id] = counts.get(phase_id, 0) + 1
    return counts


def count_phase_blockers(db: Session, project_id: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    risks_by_id = {risk.id: risk for risk in db.scalars(select(Risk).where(Risk.project_id == project_id)).all()}
    links = db.scalars(select(EntityLink).where(EntityLink.project_id == project_id)).all()
    for link in links:
        risk_id = ""
        phase_id = ""
        if link.source_type == "phase" and link.target_type == "risk":
            phase_id, risk_id = link.source_id, link.target_id
        elif link.target_type == "phase" and link.source_type == "risk":
            phase_id, risk_id = link.target_id, link.source_id
        risk = risks_by_id.get(risk_id)
        if phase_id and risk and (risk.status == "Открыт" and risk.risk_level == "Критичный"):
            counts[phase_id] = counts.get(phase_id, 0) + 1
    return counts


def linked_phase_risks(db: Session, project_id: str, phase_id: str) -> list[Risk]:
    if not phase_id:
        return []
    risk_ids = set()
    links = db.scalars(select(EntityLink).where(EntityLink.project_id == project_id)).all()
    for link in links:
        if link.source_type == "phase" and link.source_id == phase_id and link.target_type == "risk":
            risk_ids.add(link.target_id)
        if link.target_type == "phase" and link.target_id == phase_id and link.source_type == "risk":
            risk_ids.add(link.source_id)
    if not risk_ids:
        return []
    return db.scalars(select(Risk).where(Risk.id.in_(risk_ids)).order_by(Risk.created_at.desc())).all()


def today_string() -> str:
    return datetime.now().strftime("%d.%m.%Y")


def safe_int(value: str) -> int:
    try:
        return int(str(value or "0"))
    except ValueError:
        return 0
