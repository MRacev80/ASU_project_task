from app.models import ProcurementItem, WorkItem
from app.models import Risk
from app.routes.pages import (
    calculate_work_totals,
    filter_procurement_items,
    filter_risks,
    filter_work_items,
    group_work_items_by_section,
    sort_procurement_items,
)


def test_budget_filter_and_totals_work_for_current_selection():
    items = [
        WorkItem(
            project_id="p1",
            section="1. Спецификация работ",
            group_name="Проектирование",
            name="Разработка инструкции",
            quantity="60",
            sum_no_vat="47437.5",
            sum_with_vat="56925",
        ),
        WorkItem(
            project_id="p1",
            section="2. Сопутствующие расходы",
            group_name="Командировки",
            name="Командировка",
            quantity="2",
            sum_no_vat="50000",
            sum_with_vat="61000",
        ),
    ]

    filtered = filter_work_items(items, "1. Спецификация работ", "инструкции")
    totals = calculate_work_totals(filtered)

    assert [item.name for item in filtered] == ["Разработка инструкции"]
    assert totals == {"quantity": "60", "sum_no_vat": "47437.5", "sum_with_vat": "56925"}


def test_budget_grouping_calculates_section_totals():
    items = [
        WorkItem(project_id="p1", section="1. Спецификация работ", name="Работа 1", quantity="10", sum_no_vat="100", sum_with_vat="120"),
        WorkItem(project_id="p1", section="1. Спецификация работ", name="Работа 2", quantity="5", sum_no_vat="50", sum_with_vat="60"),
        WorkItem(project_id="p1", section="2. Расходы", name="Расход", quantity="1", sum_no_vat="25", sum_with_vat="30"),
    ]

    groups = group_work_items_by_section(items)

    assert groups[0]["section"] == "1. Спецификация работ"
    assert groups[0]["totals"] == {"quantity": "15", "sum_no_vat": "150", "sum_with_vat": "180"}
    assert groups[1]["section"] == "2. Расходы"


def test_procurement_filters_keep_group_rows_readable():
    group = ProcurementItem(project_id="p1", name="SCADA", group_name="SCADA", section="Оборудование", is_group_header="1")
    computer = ProcurementItem(
        project_id="p1",
        name="Компьютер",
        group_name="SCADA",
        section="Оборудование / SCADA",
        manufacturer="Ситилинк",
        status="Оформлено",
        row_order="2",
    )
    cable = ProcurementItem(
        project_id="p1",
        name="Кабель",
        group_name="Кабели",
        section="Кабельная продукция / Кабели",
        manufacturer="Cabeus",
        status="В проработке",
        row_order="3",
    )

    filtered = filter_procurement_items([group, computer, cable], status="Оформлено", group="SCADA", manufacturer="")
    sorted_items = sort_procurement_items(filtered, sort="section", direction="asc")

    assert [item.name for item in sorted_items] == ["SCADA", "Компьютер"]


def test_risk_filters_by_status_level_and_owner():
    risks = [
        Risk(project_id="p1", title="Критичный риск", status="Открыт", risk_level="Критичный", owner="РП"),
        Risk(project_id="p1", title="Низкий риск", status="Закрыт", risk_level="Низкий", owner="Инженер"),
    ]

    filtered = filter_risks(risks, status="Открыт", level="Критичный", owner="РП")

    assert [risk.title for risk in filtered] == ["Критичный риск"]
