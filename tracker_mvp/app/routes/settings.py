from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CompanyPerson, Setting
from app.templates import templates


router = APIRouter()


@router.get("/settings")
def settings_page(request: Request, db: Session = Depends(get_db)):
    settings = db.scalars(select(Setting).order_by(Setting.key)).all()
    people = db.scalars(select(CompanyPerson).order_by(CompanyPerson.full_name)).all()
    values = {setting.key: setting.value for setting in settings}
    return templates.TemplateResponse("settings.html", {"request": request, "settings": values, "people": people})


@router.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.scalars(select(Setting).order_by(Setting.key)).all()
    return {setting.key: setting.value for setting in settings}


@router.post("/settings")
def update_settings(
    workspace_path: str = Form(""),
    backup_path: str = Form(""),
    archive_path: str = Form(""),
    db: Session = Depends(get_db),
):
    for key, value in {
        "workspace_path": workspace_path,
        "backup_path": backup_path,
        "archive_path": archive_path,
    }.items():
        setting = db.get(Setting, key)
        if setting:
            setting.value = value
        else:
            db.add(Setting(key=key, value=value))
    db.commit()
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/settings/people")
def create_person(
    full_name: str = Form(...),
    role: str = Form(""),
    department: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    # Справочник людей хранит единые варианты выбора ответственных, чтобы в проектных формах не плодить разные написания ФИО.
    person = CompanyPerson(full_name=full_name.strip(), role=role, department=department, phone=phone, email=email)
    db.add(person)
    db.commit()
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/settings/people/{person_id}/delete")
def delete_person(person_id: str, db: Session = Depends(get_db)):
    person = db.get(CompanyPerson, person_id)
    if person:
        person.is_active = "0"
        db.commit()
    return RedirectResponse(url="/settings", status_code=303)
