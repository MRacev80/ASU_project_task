"""Маршруты для управления площадками и спецификациями проекта.

Площадки (project_sites) — географические или функциональные места работ внутри одного проекта.
Спецификации (project_specifications) — документы работ или оборудования,
привязанные к площадке. Один проект → много площадок → много спецификаций.

Все изменения фиксируются в журнале событий (event_log).

Архитектурный выбор: бизнес-логика вынесена в отдельные функции (create_site,
create_specification и т.д.), чтобы их можно было вызывать напрямую из тестов
без HTTP-слоя. Роутерные обёртки только извлекают Form-параметры и делегируют.
"""
from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ProjectSite, ProjectSpecification, ProcurementItem, SpecificationItem
from app.services.event_log import record_event


router = APIRouter()

SITE_STATUSES = {"Не начата", "В работе", "Завершена", "Приостановлена"}
SPEC_TYPES = {"Работы", "Оборудование", "Материалы", "ПО", "Документация", "Прочее"}
SPEC_STATUSES = {"Черновик", "Согласовано", "Подписано"}
ITEM_STATUSES = {"В проработке", "Оформлено", "Поставляется", "На складе", "Готово"}


def _redirect_to_sites(project_id: str, anchor: str = "") -> RedirectResponse:
    url = f"/projects/{project_id}/sites"
    if anchor:
        url += f"#{anchor}"
    return RedirectResponse(url=url, status_code=303)


# ── Площадки — бизнес-логика (вызывается напрямую из тестов) ─────────────────

def create_site(
    project_id: str,
    name: str,
    description: str = "",
    owner: str = "",
    status: str = "Не начата",
    order_index: str = "",
    comment: str = "",
    db: Session = None,
) -> RedirectResponse:
    """Создание новой площадки проекта."""
    site = ProjectSite(
        project_id=project_id,
        name=name,
        description=description,
        owner=owner,
        status=status if status in SITE_STATUSES else "Не начата",
        order_index=order_index,
        comment=comment,
    )
    db.add(site)
    db.flush()
    record_event(
        db,
        project_id=project_id,
        event_type="site.created",
        entity_type="project_site",
        entity_id=site.id,
        description=f"Создана площадка: {site.name}",
    )
    db.commit()
    return _redirect_to_sites(project_id)


def update_site(
    site_id: str,
    name: str,
    description: str = "",
    owner: str = "",
    status: str = "Не начата",
    comment: str = "",
    db: Session = None,
) -> RedirectResponse:
    """Обновление данных площадки."""
    site = db.get(ProjectSite, site_id)
    if not site:
        return RedirectResponse(url="/", status_code=303)

    before = {"name": site.name, "status": site.status}
    site.name = name
    site.description = description
    site.owner = owner
    site.status = status if status in SITE_STATUSES else "Не начата"
    site.comment = comment
    record_event(
        db,
        project_id=site.project_id,
        event_type="site.updated",
        entity_type="project_site",
        entity_id=site.id,
        description=f"Обновлена площадка: {site.name}",
        before_state=before,
        after_state={"name": site.name, "status": site.status},
    )
    db.commit()
    return _redirect_to_sites(site.project_id)


def delete_site(site_id: str, db: Session = None) -> RedirectResponse:
    """Удаление площадки со всеми спецификациями (cascade).
    Строки work_items и procurement_items не удаляются — только теряют привязку."""
    site = db.get(ProjectSite, site_id)
    if not site:
        return RedirectResponse(url="/", status_code=303)
    project_id = site.project_id
    name = site.name
    db.delete(site)
    record_event(
        db,
        project_id=project_id,
        event_type="site.deleted",
        entity_type="project_site",
        entity_id=site_id,
        description=f"Удалена площадка: {name}",
    )
    db.commit()
    return _redirect_to_sites(project_id)


# ── Спецификации — бизнес-логика ──────────────────────────────────────────────

def create_specification(
    site_id: str,
    title: str,
    spec_type: str = "Работы",
    source_type: str = "файл",
    status: str = "Черновик",
    progress_percent: str = "0",
    owner: str = "",
    total_amount: str = "",
    version: str = "",
    signed_date: str = "",
    comment: str = "",
    db: Session = None,
) -> RedirectResponse:
    """Создание спецификации, привязанной к площадке."""
    site = db.get(ProjectSite, site_id)
    if not site:
        return RedirectResponse(url="/", status_code=303)

    spec = ProjectSpecification(
        project_id=site.project_id,
        site_id=site_id,
        title=title,
        spec_type=spec_type if spec_type in SPEC_TYPES else "Работы",
        source_type=source_type,
        status=status if status in SPEC_STATUSES else "Черновик",
        progress_percent=progress_percent or "0",
        owner=owner,
        total_amount=total_amount,
        version=version,
        signed_date=signed_date,
        comment=comment,
    )
    db.add(spec)
    db.flush()
    record_event(
        db,
        project_id=site.project_id,
        event_type="specification.created",
        entity_type="project_specification",
        entity_id=spec.id,
        description=f"Создана спецификация: {spec.title} ({spec.spec_type}) — {site.name}",
    )
    db.commit()
    return _redirect_to_sites(site.project_id)


def update_specification(
    spec_id: str,
    title: str,
    spec_type: str = "Работы",
    status: str = "Черновик",
    progress_percent: str = "0",
    owner: str = "",
    total_amount: str = "",
    version: str = "",
    signed_date: str = "",
    comment: str = "",
    db: Session = None,
) -> RedirectResponse:
    """Обновление спецификации."""
    spec = db.get(ProjectSpecification, spec_id)
    if not spec:
        return RedirectResponse(url="/", status_code=303)

    before = {"status": spec.status, "progress_percent": spec.progress_percent}
    spec.title = title
    spec.spec_type = spec_type if spec_type in SPEC_TYPES else "Работы"
    spec.status = status if status in SPEC_STATUSES else "Черновик"
    spec.progress_percent = progress_percent or "0"
    spec.owner = owner
    spec.total_amount = total_amount
    spec.version = version
    spec.signed_date = signed_date
    spec.comment = comment
    record_event(
        db,
        project_id=spec.project_id,
        event_type="specification.updated",
        entity_type="project_specification",
        entity_id=spec.id,
        description=f"Обновлена спецификация: {spec.title} ({spec.spec_type})",
        before_state=before,
        after_state={"status": spec.status, "progress_percent": spec.progress_percent},
    )
    db.commit()
    return _redirect_to_sites(spec.project_id)


def delete_specification(spec_id: str, db: Session = None) -> RedirectResponse:
    """Удаление спецификации. Строки work_items/procurement_items не удаляются."""
    spec = db.get(ProjectSpecification, spec_id)
    if not spec:
        return RedirectResponse(url="/", status_code=303)
    project_id = spec.project_id
    title = spec.title
    db.delete(spec)
    record_event(
        db,
        project_id=project_id,
        event_type="specification.deleted",
        entity_type="project_specification",
        entity_id=spec_id,
        description=f"Удалена спецификация: {title}",
    )
    db.commit()
    return _redirect_to_sites(project_id)


# ── HTTP-роутеры (тонкие обёртки над бизнес-функциями) ───────────────────────

@router.post("/projects/{project_id}/sites")
def http_create_site(
    project_id: str,
    name: str = Form(...),
    description: str = Form(""),
    owner: str = Form(""),
    status: str = Form("Не начата"),
    order_index: str = Form(""),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    return create_site(
        project_id=project_id, name=name, description=description,
        owner=owner, status=status, order_index=order_index,
        comment=comment, db=db,
    )


@router.post("/sites/{site_id}/update")
def http_update_site(
    site_id: str,
    name: str = Form(...),
    description: str = Form(""),
    owner: str = Form(""),
    status: str = Form("Не начата"),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    return update_site(
        site_id=site_id, name=name, description=description,
        owner=owner, status=status, comment=comment, db=db,
    )


@router.post("/sites/{site_id}/delete")
def http_delete_site(site_id: str, db: Session = Depends(get_db)):
    return delete_site(site_id=site_id, db=db)


@router.post("/sites/{site_id}/specifications")
def http_create_specification(
    site_id: str,
    title: str = Form(...),
    spec_type: str = Form("Работы"),
    source_type: str = Form("файл"),
    status: str = Form("Черновик"),
    progress_percent: str = Form("0"),
    owner: str = Form(""),
    total_amount: str = Form(""),
    version: str = Form(""),
    signed_date: str = Form(""),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    return create_specification(
        site_id=site_id, title=title, spec_type=spec_type, source_type=source_type,
        status=status, progress_percent=progress_percent, owner=owner,
        total_amount=total_amount, version=version, signed_date=signed_date,
        comment=comment, db=db,
    )


@router.post("/specifications/{spec_id}/update")
def http_update_specification(
    spec_id: str,
    title: str = Form(...),
    spec_type: str = Form("Работы"),
    status: str = Form("Черновик"),
    progress_percent: str = Form("0"),
    owner: str = Form(""),
    total_amount: str = Form(""),
    version: str = Form(""),
    signed_date: str = Form(""),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    return update_specification(
        spec_id=spec_id, title=title, spec_type=spec_type, status=status,
        progress_percent=progress_percent, owner=owner, total_amount=total_amount,
        version=version, signed_date=signed_date, comment=comment, db=db,
    )


@router.post("/specifications/{spec_id}/delete")
def http_delete_specification(spec_id: str, db: Session = Depends(get_db)):
    return delete_specification(spec_id=spec_id, db=db)


# ── Позиции спецификации — бизнес-логика ─────────────────────────────────────

def create_item(
    specification_id: str,
    name: str,
    catalog_number: str = "",
    manufacturer: str = "",
    unit: str = "",
    quantity: str = "",
    unit_price: str = "",
    total_amount: str = "",
    delivery_date: str = "",
    status: str = "В проработке",
    comment: str = "",
    db: Session = None,
) -> RedirectResponse:
    """Создание позиции спецификации вручную.
    Позиции позволяют отслеживать конкретные единицы оборудования или объёмы работ
    в разрезе спецификации — независимо от импорта Excel.

    Если спецификация типа «Оборудование» — автоматически создаём ProcurementItem,
    чтобы позиция сразу попадала в реестр закупок без двойного ввода."""
    spec = db.get(ProjectSpecification, specification_id)
    if not spec:
        return RedirectResponse(url="/", status_code=303)

    item_status = status if status in ITEM_STATUSES else "В проработке"
    item = SpecificationItem(
        specification_id=specification_id,
        project_id=spec.project_id,
        site_id=spec.site_id,
        name=name,
        catalog_number=catalog_number,
        manufacturer=manufacturer,
        unit=unit,
        quantity=quantity,
        unit_price=unit_price,
        total_amount=total_amount,
        delivery_date=delivery_date,
        status=item_status,
        comment=comment,
    )
    db.add(item)
    db.flush()
    record_event(
        db,
        project_id=spec.project_id,
        event_type="item.created",
        entity_type="specification_item",
        entity_id=item.id,
        description=f"Добавлена позиция: {item.name} → {spec.title}",
    )

    # Авто-синхронизация с закупками: оборудование по спецификации всегда нужно купить.
    # Создаём ProcurementItem с той же площадкой и спецификацией, чтобы закупщик
    # видел позицию в реестре Закупки без отдельного ввода.
    if spec.spec_type == "Оборудование":
        procurement = ProcurementItem(
            project_id=spec.project_id,
            site_id=spec.site_id,
            specification_id=specification_id,
            name=name,
            catalog_number=catalog_number,
            manufacturer=manufacturer,
            unit=unit,
            quantity=quantity,
            unit_price_no_vat=unit_price,
            sum_no_vat=total_amount,
            delivery_date=delivery_date,
            status=item_status,
            supply_comment=comment,
            source_file="spec_item",  # маркер: создано из позиции спецификации
        )
        db.add(procurement)
        db.flush()  # получаем id до записи события
        record_event(
            db,
            project_id=spec.project_id,
            event_type="procurement.created",
            entity_type="procurement_item",
            entity_id=procurement.id,
            description=f"Авто-закупка из спецификации: {name} ({spec.title})",
        )

    db.commit()
    # Якорь site-{site_id} сохраняет открытую площадку после перезагрузки страницы.
    return _redirect_to_sites(spec.project_id, anchor=f"site-{spec.site_id}")


def update_item(
    item_id: str,
    name: str,
    catalog_number: str = "",
    manufacturer: str = "",
    unit: str = "",
    quantity: str = "",
    unit_price: str = "",
    total_amount: str = "",
    delivery_date: str = "",
    status: str = "В проработке",
    comment: str = "",
    db: Session = None,
) -> RedirectResponse:
    """Обновление позиции спецификации."""
    item = db.get(SpecificationItem, item_id)
    if not item:
        return RedirectResponse(url="/", status_code=303)

    before = {"status": item.status, "quantity": item.quantity}
    item.name = name
    item.catalog_number = catalog_number
    item.manufacturer = manufacturer
    item.unit = unit
    item.quantity = quantity
    item.unit_price = unit_price
    item.total_amount = total_amount
    item.delivery_date = delivery_date
    item.status = status if status in ITEM_STATUSES else "В проработке"
    item.comment = comment
    record_event(
        db,
        project_id=item.project_id,
        event_type="item.updated",
        entity_type="specification_item",
        entity_id=item.id,
        description=f"Обновлена позиция: {item.name}",
        before_state=before,
        after_state={"status": item.status, "quantity": item.quantity},
    )
    db.commit()
    return _redirect_to_sites(item.project_id)


def delete_item(item_id: str, db: Session = None) -> RedirectResponse:
    """Удаление позиции спецификации."""
    item = db.get(SpecificationItem, item_id)
    if not item:
        return RedirectResponse(url="/", status_code=303)
    project_id = item.project_id
    name = item.name
    db.delete(item)
    record_event(
        db,
        project_id=project_id,
        event_type="item.deleted",
        entity_type="specification_item",
        entity_id=item_id,
        description=f"Удалена позиция: {name}",
    )
    db.commit()
    return _redirect_to_sites(project_id)


# ── HTTP-роутеры для позиций ──────────────────────────────────────────────────

@router.post("/specifications/{spec_id}/items")
def http_create_item(
    spec_id: str,
    name: str = Form(...),
    catalog_number: str = Form(""),
    manufacturer: str = Form(""),
    unit: str = Form(""),
    quantity: str = Form(""),
    unit_price: str = Form(""),
    total_amount: str = Form(""),
    delivery_date: str = Form(""),
    status: str = Form("В проработке"),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    return create_item(
        specification_id=spec_id, name=name, catalog_number=catalog_number,
        manufacturer=manufacturer, unit=unit, quantity=quantity,
        unit_price=unit_price, total_amount=total_amount,
        delivery_date=delivery_date, status=status, comment=comment, db=db,
    )


@router.post("/items/{item_id}/update")
def http_update_item(
    item_id: str,
    name: str = Form(...),
    catalog_number: str = Form(""),
    manufacturer: str = Form(""),
    unit: str = Form(""),
    quantity: str = Form(""),
    unit_price: str = Form(""),
    total_amount: str = Form(""),
    delivery_date: str = Form(""),
    status: str = Form("В проработке"),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    return update_item(
        item_id=item_id, name=name, catalog_number=catalog_number,
        manufacturer=manufacturer, unit=unit, quantity=quantity,
        unit_price=unit_price, total_amount=total_amount,
        delivery_date=delivery_date, status=status, comment=comment, db=db,
    )


@router.post("/items/{item_id}/delete")
def http_delete_item(item_id: str, db: Session = Depends(get_db)):
    return delete_item(item_id=item_id, db=db)
