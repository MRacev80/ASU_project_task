"""Тесты для площадок (project_sites) и спецификаций (project_specifications).

Проверяем:
- создание площадки, запись event
- создание спецификации к площадке, запись event
- обновление статуса спецификации
- удаление площадки (cascade удаляет спецификации)
- вкладка /sites доступна в HTTP-ответе приложения
- создание позиции спецификации, запись event
- удаление спецификации cascade удаляет позиции
"""
from sqlalchemy import select

from app.models import Event, ProjectSite, ProjectSpecification, SpecificationItem
from app.routes.sites import (
    create_item,
    create_site,
    create_specification,
    delete_site,
    delete_specification,
    update_specification,
)


def test_site_creation_records_event(db_session, project):
    """Создание площадки должно сохранить запись в журнале событий."""
    resp = create_site(
        project_id=project.id,
        name="Ульяновск",
        description="Линия аппликатора 1",
        owner="Иванов И.И.",
        status="Не начата",
        order_index="1",
        comment="Открытые вопросы по Logopack",
        db=db_session,
    )
    assert f"/projects/{project.id}/sites" in resp.headers["location"]

    site = db_session.scalars(select(ProjectSite).where(ProjectSite.project_id == project.id)).one()
    assert site.name == "Ульяновск"
    assert site.status == "Не начата"
    assert site.owner == "Иванов И.И."

    event = db_session.scalars(
        select(Event).where(Event.project_id == project.id, Event.event_type == "site.created")
    ).one()
    assert "Ульяновск" in event.description


def test_specification_creation_links_to_site(db_session, project):
    """Спецификация должна быть привязана к площадке и записать событие."""
    create_site(
        project_id=project.id,
        name="Саранск",
        db=db_session,
    )
    db_session.commit()
    site = db_session.scalars(select(ProjectSite).where(ProjectSite.name == "Саранск")).one()

    resp = create_specification(
        site_id=site.id,
        title="Спецификация работ Саранск",
        spec_type="Работы",
        source_type="файл",
        status="Черновик",
        progress_percent="30",
        owner="Петров П.П.",
        total_amount="500000",
        version="v1",
        signed_date="",
        comment="",
        db=db_session,
    )
    assert f"/projects/{project.id}/sites" in resp.headers["location"]

    spec = db_session.scalars(
        select(ProjectSpecification).where(ProjectSpecification.site_id == site.id)
    ).one()
    assert spec.spec_type == "Работы"
    assert spec.progress_percent == "30"
    assert spec.title == "Спецификация работ Саранск"

    event = db_session.scalars(
        select(Event).where(Event.project_id == project.id, Event.event_type == "specification.created")
    ).one()
    assert "Саранск" in event.description


def test_multiple_specs_per_site(db_session, project):
    """На одной площадке может быть несколько спецификаций разных типов."""
    create_site(project_id=project.id, name="Клин", db=db_session)
    db_session.commit()
    site = db_session.scalars(select(ProjectSite).where(ProjectSite.name == "Клин")).one()

    create_specification(site_id=site.id, title="КП Клин", spec_type="Работы", db=db_session)
    create_specification(site_id=site.id, title="СС Клин", spec_type="Оборудование", db=db_session)
    db_session.commit()

    specs = db_session.scalars(
        select(ProjectSpecification).where(ProjectSpecification.site_id == site.id)
    ).all()
    assert len(specs) == 2
    types = {s.spec_type for s in specs}
    assert types == {"Работы", "Оборудование"}


def test_specification_update_changes_status_and_progress(db_session, project):
    """Обновление спецификации изменяет статус, % и записывает событие."""
    create_site(project_id=project.id, name="Волжский", db=db_session)
    db_session.commit()
    site = db_session.scalars(select(ProjectSite).where(ProjectSite.name == "Волжский")).one()

    create_specification(site_id=site.id, title="КП Волжский", spec_type="Работы", db=db_session)
    db_session.commit()
    spec = db_session.scalars(
        select(ProjectSpecification).where(ProjectSpecification.site_id == site.id)
    ).one()

    update_specification(
        spec_id=spec.id,
        title="КП Волжский",
        spec_type="Работы",
        status="Согласовано",
        progress_percent="75",
        db=db_session,
    )
    db_session.refresh(spec)
    assert spec.status == "Согласовано"
    assert spec.progress_percent == "75"

    update_event = db_session.scalars(
        select(Event).where(Event.entity_type == "project_specification", Event.event_type == "specification.updated")
    ).one()
    assert update_event is not None


def test_delete_site_cascades_specifications(db_session, project):
    """Удаление площадки должно каскадно удалить её спецификации."""
    create_site(project_id=project.id, name="Иваново", db=db_session)
    db_session.commit()
    site = db_session.scalars(select(ProjectSite).where(ProjectSite.name == "Иваново")).one()

    create_specification(site_id=site.id, title="КП Иваново", spec_type="Работы", db=db_session)
    db_session.commit()

    # Проверяем, что спецификация есть
    specs_before = db_session.scalars(
        select(ProjectSpecification).where(ProjectSpecification.site_id == site.id)
    ).all()
    assert len(specs_before) == 1

    delete_site(site_id=site.id, db=db_session)
    db_session.commit()

    # После удаления площадки — спецификации должны исчезнуть
    specs_after = db_session.scalars(
        select(ProjectSpecification).where(ProjectSpecification.site_id == site.id)
    ).all()
    assert len(specs_after) == 0

    sites_after = db_session.scalars(
        select(ProjectSite).where(ProjectSite.project_id == project.id)
    ).all()
    assert len(sites_after) == 0


def test_sites_tab_renders(client):
    """Вкладка /sites должна отдавать HTTP 200 после создания проекта."""
    # Создаём проект через HTTP, затем открываем его вкладку Площадки
    create_resp = client.post("/projects", data={"name": "Тест площадки", "customer": "QA"}, follow_redirects=False)
    assert create_resp.status_code in (200, 302, 303)

    from app.db import get_session_local
    from sqlalchemy import select
    from app.models import Project
    session = get_session_local()()
    project = session.scalars(select(Project).where(Project.name == "Тест площадки")).first()
    session.close()

    if project:
        resp = client.get(f"/projects/{project.id}/sites")
        assert resp.status_code == 200
        assert "Площадки" in resp.text


def test_item_creation_links_to_spec(db_session, project):
    """Позиция спецификации должна быть привязана к спецификации и записать событие."""
    create_site(project_id=project.id, name="Самара", db=db_session)
    db_session.commit()
    site = db_session.scalars(select(ProjectSite).where(ProjectSite.name == "Самара")).one()

    create_specification(site_id=site.id, title="КП Самара", spec_type="Оборудование", db=db_session)
    db_session.commit()
    spec = db_session.scalars(
        select(ProjectSpecification).where(ProjectSpecification.site_id == site.id)
    ).one()

    create_item(
        specification_id=spec.id,
        name="Контроллер Siemens S7-300",
        catalog_number="6ES7 315-2AH14",
        manufacturer="Siemens",
        unit="шт",
        quantity="2",
        unit_price="150000",
        total_amount="300000",
        delivery_date="Q3 2026",
        status="В проработке",
        db=db_session,
    )

    item = db_session.scalars(
        select(SpecificationItem).where(SpecificationItem.specification_id == spec.id)
    ).one()
    assert item.name == "Контроллер Siemens S7-300"
    assert item.quantity == "2"
    assert item.delivery_date == "Q3 2026"
    assert item.project_id == project.id
    assert item.site_id == site.id

    event = db_session.scalars(
        select(Event).where(Event.project_id == project.id, Event.event_type == "item.created")
    ).one()
    assert "Siemens" in event.description


def test_delete_spec_cascades_items(db_session, project):
    """Удаление спецификации должно каскадно удалить все её позиции."""
    create_site(project_id=project.id, name="Пенза", db=db_session)
    db_session.commit()
    site = db_session.scalars(select(ProjectSite).where(ProjectSite.name == "Пенза")).one()

    create_specification(site_id=site.id, title="КП Пенза", spec_type="Работы", db=db_session)
    db_session.commit()
    spec = db_session.scalars(
        select(ProjectSpecification).where(ProjectSpecification.site_id == site.id)
    ).one()

    create_item(specification_id=spec.id, name="Монтаж кабеля КВВГнг", unit="м", quantity="500", db=db_session)
    db_session.commit()

    items_before = db_session.scalars(
        select(SpecificationItem).where(SpecificationItem.specification_id == spec.id)
    ).all()
    assert len(items_before) == 1

    delete_specification(spec_id=spec.id, db=db_session)
    db_session.commit()

    items_after = db_session.scalars(
        select(SpecificationItem).where(SpecificationItem.specification_id == spec.id)
    ).all()
    assert len(items_after) == 0
