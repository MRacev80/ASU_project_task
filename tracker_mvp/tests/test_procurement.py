from sqlalchemy import select

from app.models import Event, ProcurementItem
from app.routes.procurement import create_procurement_item, delete_procurement_item, update_procurement_item, update_procurement_status


def test_manual_procurement_can_be_created_updated_and_deleted(db_session, project):
    create_procurement_item(
        project.id,
        section="Ручная закупка",
        group_name="SCADA",
        name="Монитор",
        catalog_number="MON-001",
        manufacturer="QA Manufacturer",
        supplier="QA Supplier",
        quantity="2",
        unit="шт.",
        sum_no_vat="3491,803278688525",
        supply_comment="Проверить наличие",
        order_date="2026-05-27",
        delivery_date="2026-06-10",
        db=db_session,
    )

    item = db_session.scalars(select(ProcurementItem).where(ProcurementItem.project_id == project.id)).one()
    assert item.name == "Монитор"
    assert item.group_name == "SCADA"
    assert item.status == "В проработке"
    assert item.sum_no_vat == "3491.8"
    assert item.source_file == ""

    update_procurement_item(
        item.id,
        section="Ручная закупка",
        group_name="SCADA",
        name="Монитор 24",
        catalog_number="MON-024",
        manufacturer="QA Manufacturer 2",
        supplier="QA Supplier 2",
        quantity="3",
        unit="шт.",
        sum_no_vat="5000",
        status="Оформлено",
        supply_comment="Заказ оформлен",
        order_date="2026-05-28",
        delivery_date="2026-06-15",
        db=db_session,
    )
    db_session.refresh(item)
    assert item.name == "Монитор 24"
    assert item.status == "Оформлено"
    assert item.supplier == "QA Supplier 2"
    assert item.delivery_date == "2026-06-15"

    delete_procurement_item(item.id, db=db_session)
    remaining = db_session.scalars(select(ProcurementItem).where(ProcurementItem.project_id == project.id)).all()
    assert remaining == []

    events = db_session.scalars(select(Event).where(Event.project_id == project.id)).all()
    assert {event.event_type for event in events} >= {
        "procurement.created",
        "procurement.updated",
        "procurement.deleted",
    }


def test_imported_procurement_is_not_deleted_by_manual_delete_route(db_session, project):
    imported = ProcurementItem(
        project_id=project.id,
        source_file="C:/qa/source.xls",
        section="Оборудование / SCADA",
        group_name="SCADA",
        name="Компьютер",
        catalog_number="PC-001",
        status="В проработке",
    )
    db_session.add(imported)
    db_session.commit()

    delete_procurement_item(imported.id, db=db_session)

    assert db_session.get(ProcurementItem, imported.id) is not None


def test_procurement_status_allows_only_declared_statuses(db_session, project):
    item = ProcurementItem(project_id=project.id, name="Датчик", status="В проработке")
    db_session.add(item)
    db_session.commit()

    update_procurement_status(item.id, status="Поставляется", db=db_session)
    db_session.refresh(item)
    assert item.status == "Поставляется"

    update_procurement_status(item.id, status="Недопустимый статус", db=db_session)
    db_session.refresh(item)
    assert item.status == "В проработке"
