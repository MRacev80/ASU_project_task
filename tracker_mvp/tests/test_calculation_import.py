from pathlib import Path

from app.services import calculation_import


def _row(row_number: int, **cells: str) -> dict[int, str]:
    result: dict[int, str] = {"__row__": str(row_number)}
    for key, value in cells.items():
        result[int(key[1:])] = value
    return result


def test_parse_calculation_filters_empty_budget_rows_and_keeps_real_work(monkeypatch, tmp_path):
    source = tmp_path / "Расчет КП тест.xls"
    source.write_text("stub", encoding="utf-8")

    rows = [
        _row(1, c2="1. Спецификация работ"),
        _row(2, c2="Проектирование"),
        _row(
            3,
            c2="Проектирование",
            c3="Разработка инструкции по эксплуатации",
            c6="Нормочас",
            c7="60",
            c8="790,625",
            c9="47 437,50",
            c10="56 925,00",
        ),
        _row(
            4,
            c2="Проектирование",
            c3="Монтажные работы",
            c6="Нормочас",
            c7="0",
            c8="539,06",
            c9="-",
            c10="-",
        ),
        _row(
            5,
            c2="Проектирование",
            c3="Разработка конструкторской документации",
            c6="Нормочас",
            c7="10",
            c8="862,50",
            c9="—",
            c10="",
        ),
        _row(6, c2="2. Сопутствующие расходы"),
        _row(7, c2="Командировка", c5="день", c6="2", c7="25000", c9="50 000", c10="61 000"),
        _row(8, c2="Пустой расход", c5="день", c6="0", c7="25000", c9="0", c10="0"),
    ]
    monkeypatch.setattr(calculation_import, "read_asup_rows", lambda _path: rows)

    result = calculation_import.parse_calculation(str(source))

    names = [item["name"] for item in result["works"]]
    assert names == ["Разработка инструкции по эксплуатации", "Командировка"]
    assert result["works"][0]["quantity"] == "60"
    assert result["works"][0]["unit_price"] == "790.62"
    assert result["works"][0]["sum_no_vat"] == "47437.5"
    assert result["works"][1]["sum_with_vat"] == "61000"


def test_parse_calculation_builds_procurement_groups_and_rounds_numbers(monkeypatch, tmp_path):
    source = tmp_path / "Расчет СС тест.xls"
    source.write_text("stub", encoding="utf-8")

    rows = [
        _row(1, c2="3. Спецификация оборудования"),
        _row(2, c2="SCADA"),
        _row(
            3,
            c2="Компьютер",
            c3="PC-001",
            c4="Ситилинк",
            c5="шт.",
            c6="1",
            c7="41666,666",
            c8="50000",
            c9="41666,666",
            c10="50000",
        ),
        _row(4, c2="Шкаф управления"),
        _row(
            5,
            c2="Блок питания",
            c3="NDR-240-24",
            c4="Mean Well",
            c5="шт.",
            c6="3",
            c7="3750",
            c8="4500",
            c9="11250",
            c10="13500",
        ),
        _row(6, c2="5. Спецификация материалов"),
        _row(7, c2="Кабельная продукция"),
        _row(
            8,
            c2="Кабель Ethernet",
            c3="FTP-4P",
            c4="Cabeus",
            c5="м.",
            c6="60",
            c7="58,1967213114754",
            c8="69,84",
            c9="3491.803278688525",
            c10="4190,16",
        ),
    ]
    monkeypatch.setattr(calculation_import, "read_asup_rows", lambda _path: rows)

    result = calculation_import.parse_calculation(str(source))

    procurement = result["procurement"]
    assert procurement[0]["is_group_header"] == "1"
    assert procurement[0]["name"] == "SCADA"
    assert procurement[1]["section"] == "Оборудование / SCADA"
    assert procurement[1]["sum_no_vat"] == "41666.67"
    assert procurement[2]["name"] == "Шкаф управления"
    assert procurement[3]["group_name"] == "Шкаф управления"
    assert procurement[4]["section"] == "Кабельная продукция"
    assert procurement[5]["section"] == "Кабельная продукция / Кабельная продукция"
    assert procurement[5]["sum_no_vat"] == "3491.8"


def test_read_asup_rows_raises_for_missing_file(tmp_path):
    missing_file = tmp_path / "missing.xls"

    try:
        calculation_import.read_asup_rows(str(missing_file))
    except FileNotFoundError as exc:
        assert str(missing_file) in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError")
