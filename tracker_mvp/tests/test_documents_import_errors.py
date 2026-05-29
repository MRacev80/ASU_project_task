from sqlalchemy import select

from app.models import ProcurementItem, WorkItem
from app.routes.documents import import_calculation


def test_import_missing_calculation_file_redirects_with_error_without_deleting_existing_rows(db_session, project, tmp_path):
    existing_work = WorkItem(
        project_id=project.id,
        source_file=str(tmp_path / "existing.xls"),
        name="Существующая работа",
        quantity="1",
        sum_no_vat="100",
    )
    existing_procurement = ProcurementItem(
        project_id=project.id,
        source_file=str(tmp_path / "existing.xls"),
        name="Существующая закупка",
        status="В проработке",
    )
    db_session.add_all([existing_work, existing_procurement])
    db_session.commit()

    response = import_calculation(project.id, file_path=str(tmp_path / "missing.xls"), db=db_session)

    assert response.status_code == 303
    assert "error=" in response.headers["location"]
    assert db_session.scalars(select(WorkItem).where(WorkItem.project_id == project.id)).all()
    assert db_session.scalars(select(ProcurementItem).where(ProcurementItem.project_id == project.id)).all()
