from sqlalchemy import select

from app.models import Event, ProjectPhase, TechnicalAudit
from app.routes.phases import create_technical_audit, update_gate, update_phase
from app.services.phase_service import ensure_project_phases, phase_view_model


def test_standard_project_phases_are_created_for_project(db_session, project):
    phases = ensure_project_phases(db_session, project.id)
    db_session.commit()

    assert len(phases) == 11
    assert phases[0].code == "init"
    assert any(phase.name == "Разработка ПО" for phase in phases)
    assert phases[0].status == "В работе"
    assert all(phase.inputs != "[]" for phase in phases)
    assert all(phase.outputs != "[]" for phase in phases)
    assert all(phase.definition_of_done != "[]" for phase in phases)


def test_phase_can_be_updated_and_gate_event_is_logged(db_session, project):
    phase = ensure_project_phases(db_session, project.id)[3]
    db_session.commit()

    update_phase(
        phase.id,
        status="Активная",
        health="blue",
        schedule_health="yellow",
        technical_health="red",
        risk_health="yellow",
        procurement_health="green",
        documentation_health="yellow",
        testing_health="gray",
        progress_percent="68",
        start_plan="16.05",
        finish_plan="10.06",
        start_fact="16.05",
        finish_fact="",
        project_manager="QA РП",
        technical_lead="QA Lead",
        summary="ПО в активной разработке",
        inputs_text="Утвержденное ТР | Готово | Документ согласован\nПеречень входов/выходов | Риск | Есть вопросы",
        outputs_text="Зафиксированная версия ПО контроллера | В работе | 68%\nЭкраны человеко-машинного интерфейса | Не готово",
        dod_text="[x] Версия ПО зафиксирована | Архив сохранен\n[ ] Безопасное поведение при отказах подтверждено | Нужен тест",
        gate_status="На аудите",
        gate_comment="Проверить recovery",
        db=db_session,
    )

    refreshed = db_session.get(ProjectPhase, phase.id)
    assert refreshed.progress_percent == "68"
    assert refreshed.technical_health == "red"
    assert "Перечень входов/выходов" in refreshed.inputs
    assert "Есть вопросы" in refreshed.inputs
    assert "68%" in refreshed.outputs
    assert "Безопасное поведение при отказах подтверждено" in refreshed.definition_of_done
    assert "Нужен тест" in refreshed.definition_of_done

    update_gate(
        phase.id,
        gate_status="Разрешен с рисками",
        gate_comment="Риски приняты",
        gate_decision_by="QA РП",
        db=db_session,
    )
    refreshed = db_session.get(ProjectPhase, phase.id)
    events = db_session.scalars(select(Event).where(Event.entity_type == "phase")).all()

    assert refreshed.gate_status == "Разрешен с рисками"
    assert refreshed.health == "yellow"
    assert refreshed.gate_decision_by == "QA РП"
    assert any(event.event_type == "phase.gate_updated" for event in events)


def test_phase_view_model_includes_audit_and_health(db_session, project):
    phase = ensure_project_phases(db_session, project.id)[1]
    db_session.commit()

    create_technical_audit(
        phase.id,
        auditor="QA Lead",
        status="В работе",
        audit_date="28.05.2026",
        findings="Есть замечания",
        open_findings_count="2",
        critical_findings_count="1",
        decision="Стоп",
        decision_comment="Нужна доработка",
        db=db_session,
    )

    model = phase_view_model(db_session, project.id, phase.id)
    audit = db_session.scalars(select(TechnicalAudit).where(TechnicalAudit.phase_id == phase.id)).one()

    assert model["selected_phase"].id == phase.id
    assert model["selected_phase_audit"].id == audit.id
    assert model["phase_cards"][1]["open_audit_count"] == 2
    assert {item["label"] for item in model["project_health"]} == {
        "Сроки",
        "Техника",
        "Риски",
        "Закупки",
        "Документы",
        "Испытания",
    }
