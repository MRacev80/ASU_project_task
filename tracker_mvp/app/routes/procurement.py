from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ProcurementItem
from app.services.event_log import record_event


router = APIRouter()

PROCUREMENT_STATUSES = {"В проработке", "Оформлено", "Поставляется", "На складе"}


def _normalize_number(value: str) -> str:
    """Keeps manual numeric values readable without changing empty text fields."""
    cleaned = value.replace("\u00a0", "").replace(" ", "").replace(",", ".").strip()
    if not cleaned:
        return ""
    try:
        return f"{float(cleaned):.2f}".rstrip("0").rstrip(".")
    except ValueError:
        return value.strip()


def _redirect_to_procurement(project_id: str) -> RedirectResponse:
    return RedirectResponse(url=f"/projects/{project_id}/procurement", status_code=303)


@router.post("/projects/{project_id}/procurement")
def create_procurement_item(
    project_id: str,
    section: str = Form("Ручная закупка"),
    group_name: str = Form(""),
    name: str = Form(...),
    catalog_number: str = Form(""),
    manufacturer: str = Form(""),
    supplier: str = Form(""),
    quantity: str = Form(""),
    unit: str = Form("шт."),
    sum_no_vat: str = Form(""),
    supply_comment: str = Form(""),
    order_date: str = Form(""),
    delivery_date: str = Form(""),
    db: Session = Depends(get_db),
):
    # Ручные закупки живут рядом с импортом КП/СС, но не имеют source_file:
    # так повторный импорт расчета не удалит позицию, которую добавил человек.
    item = ProcurementItem(
        project_id=project_id,
        section=f"{section} / {group_name}" if group_name else section,
        group_name=group_name,
        row_order="999999",
        name=name,
        catalog_number=catalog_number,
        manufacturer=manufacturer,
        supplier=supplier,
        quantity=_normalize_number(quantity),
        unit=unit,
        sum_no_vat=_normalize_number(sum_no_vat),
        supply_comment=supply_comment,
        order_date=order_date,
        delivery_date=delivery_date,
        status="В проработке",
    )
    db.add(item)
    db.flush()
    record_event(
        db,
        project_id=project_id,
        event_type="procurement.created",
        entity_type="procurement_item",
        entity_id=item.id,
        description=f"Добавлена закупка: {item.name}",
    )
    db.commit()
    return _redirect_to_procurement(project_id)


@router.post("/procurement/{item_id}/status")
def update_procurement_status(
    item_id: str,
    status: str = Form("В проработке"),
    db: Session = Depends(get_db),
):
    # Статус закупки ведется вручную: расчет дает состав поставки, а снабжение ведет процесс в системе.
    item = db.get(ProcurementItem, item_id)
    if not item:
        return RedirectResponse(url="/", status_code=303)

    item.status = status if status in PROCUREMENT_STATUSES else "В проработке"
    record_event(
        db,
        project_id=item.project_id,
        event_type="procurement.status_changed",
        entity_type="procurement_item",
        entity_id=item.id,
        description=f"Статус закупки изменен: {item.name} -> {item.status}",
    )
    db.commit()
    return _redirect_to_procurement(item.project_id)


@router.post("/procurement/{item_id}/update")
def update_procurement_item(
    item_id: str,
    section: str = Form("Ручная закупка"),
    group_name: str = Form(""),
    name: str = Form(...),
    catalog_number: str = Form(""),
    manufacturer: str = Form(""),
    supplier: str = Form(""),
    quantity: str = Form(""),
    unit: str = Form("шт."),
    sum_no_vat: str = Form(""),
    status: str = Form("В проработке"),
    supply_comment: str = Form(""),
    order_date: str = Form(""),
    delivery_date: str = Form(""),
    db: Session = Depends(get_db),
):
    item = db.get(ProcurementItem, item_id)
    if not item:
        return RedirectResponse(url="/", status_code=303)
    if item.is_group_header:
        return _redirect_to_procurement(item.project_id)

    # Импортированные строки можно уточнять по снабжению, а состав из Excel при повторном импорте пересоздастся.
    item.section = f"{section} / {group_name}" if group_name else section
    item.group_name = group_name
    item.name = name
    item.catalog_number = catalog_number
    item.manufacturer = manufacturer
    item.supplier = supplier
    item.quantity = _normalize_number(quantity)
    item.unit = unit
    item.sum_no_vat = _normalize_number(sum_no_vat)
    item.status = status if status in PROCUREMENT_STATUSES else "В проработке"
    item.supply_comment = supply_comment
    item.order_date = order_date
    item.delivery_date = delivery_date
    record_event(
        db,
        project_id=item.project_id,
        event_type="procurement.updated",
        entity_type="procurement_item",
        entity_id=item.id,
        description=f"Обновлена закупка: {item.name}",
    )
    db.commit()
    return _redirect_to_procurement(item.project_id)


@router.post("/procurement/{item_id}/delete")
def delete_procurement_item(item_id: str, db: Session = Depends(get_db)):
    item = db.get(ProcurementItem, item_id)
    if not item:
        return RedirectResponse(url="/", status_code=303)

    project_id = item.project_id
    name = item.name
    # Удаление предназначено для ручных позиций; импортированные строки лучше убирать через повторный импорт расчета.
    if item.source_file:
        return _redirect_to_procurement(project_id)

    db.delete(item)
    record_event(
        db,
        project_id=project_id,
        event_type="procurement.deleted",
        entity_type="procurement_item",
        entity_id=item_id,
        description=f"Удалена ручная закупка: {name}",
    )
    db.commit()
    return _redirect_to_procurement(project_id)
