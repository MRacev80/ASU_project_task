import uuid
from datetime import date, datetime
from typing import List

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.utcnow()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_code: Mapped[str] = mapped_column(String, default="")
    name: Mapped[str] = mapped_column(String, nullable=False)
    customer: Mapped[str] = mapped_column(String, default="")
    automation_object: Mapped[str] = mapped_column(String, default="")
    contract_number: Mapped[str] = mapped_column(String, default="")
    stage: Mapped[str] = mapped_column(String, default="")
    current_milestone: Mapped[str] = mapped_column(String, default="")
    start_plan: Mapped[str] = mapped_column(String, default="")
    finish_plan: Mapped[str] = mapped_column(String, default="")
    start_fact: Mapped[str] = mapped_column(String, default="")
    finish_fact: Mapped[str] = mapped_column(String, default="")
    readiness_percent: Mapped[str] = mapped_column(String, default="")
    contract_amount: Mapped[str] = mapped_column(String, default="")
    budget_plan: Mapped[str] = mapped_column(String, default="")
    budget_actual: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="В работе")
    project_manager: Mapped[str] = mapped_column(String, default="")
    designer: Mapped[str] = mapped_column(String, default="")
    programmer: Mapped[str] = mapped_column(String, default="")
    kip_master: Mapped[str] = mapped_column(String, default="")
    documents_path: Mapped[str] = mapped_column(String, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="project")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="project")
    events: Mapped[List["Event"]] = relationship("Event", back_populates="project")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String, default="работа")
    status: Mapped[str] = mapped_column(String, default="Бэклог")
    priority: Mapped[str] = mapped_column(String, default="Средний")
    due_date: Mapped[date] = mapped_column(Date, nullable=True)
    assignee: Mapped[str] = mapped_column(String, default="")
    source_type: Mapped[str] = mapped_column(String, default="вручную")
    result: Mapped[str] = mapped_column(Text, default="")
    blocked_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    project: Mapped[Project] = relationship("Project", back_populates="tasks")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, default="прочий документ")
    file_path: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="Активный")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    project: Mapped[Project] = relationship("Project", back_populates="documents")


class WorkItem(Base):
    __tablename__ = "work_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    # site_id и specification_id связывают строки работ с площадкой и спецификацией проекта.
    # Если площадка не выбрана при импорте, поля остаются пустыми (обратная совместимость).
    site_id: Mapped[str] = mapped_column(String, default="")
    specification_id: Mapped[str] = mapped_column(String, default="")
    source_file: Mapped[str] = mapped_column(Text, default="")
    section: Mapped[str] = mapped_column(String, default="")
    group_name: Mapped[str] = mapped_column(String, default="")
    name: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(String, default="")
    quantity: Mapped[str] = mapped_column(String, default="")
    unit_price: Mapped[str] = mapped_column(String, default="")
    sum_no_vat: Mapped[str] = mapped_column(String, default="")
    sum_with_vat: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ProcurementItem(Base):
    __tablename__ = "procurement_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    # site_id и specification_id связывают позиции оборудования с площадкой и спецификацией.
    # Если площадка не выбрана при импорте, поля остаются пустыми (обратная совместимость).
    site_id: Mapped[str] = mapped_column(String, default="")
    specification_id: Mapped[str] = mapped_column(String, default="")
    source_file: Mapped[str] = mapped_column(Text, default="")
    section: Mapped[str] = mapped_column(String, default="")
    group_name: Mapped[str] = mapped_column(String, default="")
    row_order: Mapped[str] = mapped_column(String, default="")
    is_group_header: Mapped[str] = mapped_column(String, default="")
    name: Mapped[str] = mapped_column(Text, nullable=False)
    catalog_number: Mapped[str] = mapped_column(String, default="")
    manufacturer: Mapped[str] = mapped_column(String, default="")
    supplier: Mapped[str] = mapped_column(String, default="")
    unit: Mapped[str] = mapped_column(String, default="")
    quantity: Mapped[str] = mapped_column(String, default="")
    unit_price_no_vat: Mapped[str] = mapped_column(String, default="")
    unit_price_with_vat: Mapped[str] = mapped_column(String, default="")
    sum_no_vat: Mapped[str] = mapped_column(String, default="")
    sum_with_vat: Mapped[str] = mapped_column(String, default="")
    install_hours: Mapped[str] = mapped_column(String, default="")
    connection_hours: Mapped[str] = mapped_column(String, default="")
    note: Mapped[str] = mapped_column(Text, default="")
    supply_comment: Mapped[str] = mapped_column(Text, default="")
    order_date: Mapped[str] = mapped_column(String, default="")
    delivery_date: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="В проработке")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Risk(Base):
    __tablename__ = "risks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    probability: Mapped[str] = mapped_column(String, default="")
    impact: Mapped[str] = mapped_column(String, default="")
    risk_score: Mapped[str] = mapped_column(String, default="")
    risk_level: Mapped[str] = mapped_column(String, default="")
    mitigation: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="Открыт")
    linked_entity_type: Mapped[str] = mapped_column(String, default="")
    linked_entity_id: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class P3Activity(Base):
    __tablename__ = "p3_activities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    group_code: Mapped[str] = mapped_column(String, default="")
    group_title: Mapped[str] = mapped_column(String, default="")
    title: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, default="")
    project_links: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="Не начато")
    owner: Mapped[str] = mapped_column(String, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    last_done_at: Mapped[str] = mapped_column(String, default="")
    next_due_at: Mapped[str] = mapped_column(String, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class P3Cycle(Base):
    __tablename__ = "p3_cycles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    cycle_number: Mapped[str] = mapped_column(String, default="")
    start_date: Mapped[str] = mapped_column(String, default="")
    end_date: Mapped[str] = mapped_column(String, default="")
    duration_days: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="Планируется")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class ProjectPhase(Base):
    __tablename__ = "project_phases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="Не начато")
    health: Mapped[str] = mapped_column(String, default="gray")
    schedule_health: Mapped[str] = mapped_column(String, default="gray")
    technical_health: Mapped[str] = mapped_column(String, default="gray")
    risk_health: Mapped[str] = mapped_column(String, default="gray")
    procurement_health: Mapped[str] = mapped_column(String, default="gray")
    documentation_health: Mapped[str] = mapped_column(String, default="gray")
    testing_health: Mapped[str] = mapped_column(String, default="gray")
    progress_percent: Mapped[str] = mapped_column(String, default="0")
    start_plan: Mapped[str] = mapped_column(String, default="")
    finish_plan: Mapped[str] = mapped_column(String, default="")
    start_fact: Mapped[str] = mapped_column(String, default="")
    finish_fact: Mapped[str] = mapped_column(String, default="")
    project_manager: Mapped[str] = mapped_column(String, default="")
    technical_lead: Mapped[str] = mapped_column(String, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[str] = mapped_column(Text, default="[]")
    outputs: Mapped[str] = mapped_column(Text, default="[]")
    kpi: Mapped[str] = mapped_column(Text, default="[]")
    definition_of_done: Mapped[str] = mapped_column(Text, default="[]")
    gate_status: Mapped[str] = mapped_column(String, default="Не готов")
    gate_comment: Mapped[str] = mapped_column(Text, default="")
    gate_decision_by: Mapped[str] = mapped_column(String, default="")
    gate_decision_at: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class TechnicalAudit(Base):
    __tablename__ = "technical_audits"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    phase_id: Mapped[str] = mapped_column(ForeignKey("project_phases.id"), nullable=False)
    auditor: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="Не начат")
    audit_date: Mapped[str] = mapped_column(String, default="")
    scope_review: Mapped[str] = mapped_column(Text, default="")
    risk_review: Mapped[str] = mapped_column(Text, default="")
    interface_review: Mapped[str] = mapped_column(Text, default="")
    reliability_review: Mapped[str] = mapped_column(Text, default="")
    recovery_review: Mapped[str] = mapped_column(Text, default="")
    cybersecurity_review: Mapped[str] = mapped_column(Text, default="")
    maintainability_review: Mapped[str] = mapped_column(Text, default="")
    schedule_review: Mapped[str] = mapped_column(Text, default="")
    findings: Mapped[str] = mapped_column(Text, default="")
    open_findings_count: Mapped[str] = mapped_column(String, default="0")
    critical_findings_count: Mapped[str] = mapped_column(String, default="0")
    decision: Mapped[str] = mapped_column(String, default="")
    decision_comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    actor_type: Mapped[str] = mapped_column(String, default="человек")
    actor_id: Mapped[str] = mapped_column(String, default="local")
    source: Mapped[str] = mapped_column(String, default="ui")
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    before_state: Mapped[str] = mapped_column(Text, default="")
    after_state: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    project: Mapped[Project] = relationship("Project", back_populates="events")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class CompanyPerson(Base):
    __tablename__ = "company_people"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="")
    department: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str] = mapped_column(String, default="")
    email: Mapped[str] = mapped_column(String, default="")
    is_active: Mapped[str] = mapped_column(String, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class EntityLink(Base):
    __tablename__ = "entity_links"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    relation_type: Mapped[str] = mapped_column(String, default="связано")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ProjectSite(Base):
    """Площадка проекта — географическое или функциональное место работ.
    Один проект может иметь несколько площадок (например, заводы в рамках ДС).
    К каждой площадке привязываются спецификации работ и оборудования."""
    __tablename__ = "project_sites"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="Не начата")
    # status values: Не начата / В работе / Завершена / Приостановлена
    order_index: Mapped[str] = mapped_column(String, default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    specifications: Mapped[List["ProjectSpecification"]] = relationship(
        "ProjectSpecification", back_populates="site", cascade="all, delete-orphan"
    )


class ProjectSpecification(Base):
    """Спецификация проекта — документ с перечнем работ или оборудования по конкретной площадке.
    На одну площадку может быть несколько спецификаций разных типов.
    При импорте расчёта КП/СС создаётся или выбирается спецификация нужного типа,
    и все строки work_items / procurement_items связываются с ней."""
    __tablename__ = "project_specifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    site_id: Mapped[str] = mapped_column(ForeignKey("project_sites.id"), nullable=False)
    # spec_type values: Работы / Оборудование / Материалы / ПО / Документация / Прочее
    spec_type: Mapped[str] = mapped_column(String, default="Работы")
    title: Mapped[str] = mapped_column(String, nullable=False)
    # source_type values: файл / вручную
    source_type: Mapped[str] = mapped_column(String, default="файл")
    source_file: Mapped[str] = mapped_column(Text, default="")
    # status values: Черновик / Согласовано / Подписано
    status: Mapped[str] = mapped_column(String, default="Черновик")
    progress_percent: Mapped[str] = mapped_column(String, default="0")
    owner: Mapped[str] = mapped_column(String, default="")
    total_amount: Mapped[str] = mapped_column(String, default="")
    version: Mapped[str] = mapped_column(String, default="")
    signed_date: Mapped[str] = mapped_column(String, default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    site: Mapped["ProjectSite"] = relationship("ProjectSite", back_populates="specifications")
    items: Mapped[List["SpecificationItem"]] = relationship(
        "SpecificationItem", back_populates="specification", cascade="all, delete-orphan"
    )


class SpecificationItem(Base):
    """Позиция спецификации — строка оборудования или работы, введённая вручную.
    Позволяет отслеживать состояние конкретных единиц оборудования или объёмов работ
    в разрезе спецификации и площадки без привязки к импорту Excel."""
    __tablename__ = "specification_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    specification_id: Mapped[str] = mapped_column(
        ForeignKey("project_specifications.id"), nullable=False
    )
    # Денормализованные поля для быстрой выборки по проекту и площадке без JOIN.
    project_id: Mapped[str] = mapped_column(String, default="")
    site_id: Mapped[str] = mapped_column(String, default="")

    name: Mapped[str] = mapped_column(Text, nullable=False)
    catalog_number: Mapped[str] = mapped_column(String, default="")
    manufacturer: Mapped[str] = mapped_column(String, default="")
    unit: Mapped[str] = mapped_column(String, default="")
    quantity: Mapped[str] = mapped_column(String, default="")
    unit_price: Mapped[str] = mapped_column(String, default="")
    total_amount: Mapped[str] = mapped_column(String, default="")
    # delivery_date хранится как текст: "Q3 2026", "2026-09-01" и т.д.
    delivery_date: Mapped[str] = mapped_column(String, default="")
    # status values: В проработке / Оформлено / Поставляется / На складе / Готово
    status: Mapped[str] = mapped_column(String, default="В проработке")
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    specification: Mapped["ProjectSpecification"] = relationship(
        "ProjectSpecification", back_populates="items"
    )


class AgentProposal(Base):
    __tablename__ = "agent_proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String, default="local-agent")
    source_file: Mapped[str] = mapped_column(Text, default="")
    proposal_type: Mapped[str] = mapped_column(String, default="create_task")
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    target_type: Mapped[str] = mapped_column(String, default="")
    target_id: Mapped[str] = mapped_column(String, default="")
    suggested_status: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="На рассмотрении")
    decision_comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
