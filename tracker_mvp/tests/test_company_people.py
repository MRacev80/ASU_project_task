from sqlalchemy import select

from app.models import CompanyPerson
from app.routes.settings import create_person, delete_person


def test_company_people_can_be_created_and_hidden(db_session):
    create_person(
        full_name="Иванов Иван",
        role="Проектировщик",
        department="АСУТП",
        phone="+7 000 000",
        email="ivanov@example.local",
        db=db_session,
    )

    person = db_session.scalars(select(CompanyPerson).where(CompanyPerson.full_name == "Иванов Иван")).one()
    assert person.role == "Проектировщик"
    assert person.is_active == "1"

    delete_person(person.id, db=db_session)
    db_session.refresh(person)

    assert person.is_active == "0"
