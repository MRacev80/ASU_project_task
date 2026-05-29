import re
from pathlib import Path
from typing import Any

import xlrd


# Этот сервис превращает Excel-расчет КП/СС в рабочие строки приложения.
# Источник истины остается Excel-файл, а строки работ и закупок в БД являются
# производными данными, которые можно пересоздать повторным импортом.


SECTION_LABELS = {
    "3.": "Оборудование",
    "4.": "Полевое оборудование",
    "5.": "Кабельная продукция",
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _cell(row: dict[int, str], number: int) -> str:
    return row.get(number, "").strip()


def _number_to_float(value: str) -> float:
    # Excel хранит числа то как числа, то как текст с пробелами и разными прочерками.
    # Для фильтрации и вывода приводим оба варианта к float; пустые и нечисловые значения считаем нулем.
    cleaned = (
        value.replace("\u00a0", "")
        .replace(" ", "")
        .replace(",", ".")
        .replace("−", "")
        .replace("–", "")
        .replace("—", "")
        .replace("-", "")
        .strip()
    )
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _format_number(value: str) -> str:
    number = _number_to_float(value)
    if number == 0 and not value.strip().startswith("0"):
        return ""
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _has_positive_sum(*values: str) -> bool:
    return any(_number_to_float(value) > 0 for value in values)


def _has_positive_quantity(value: str) -> bool:
    return _number_to_float(value) > 0


def _is_empty_amount(value: str) -> bool:
    return _number_to_float(value) == 0


def _section_label(section: str) -> str:
    for prefix, label in SECTION_LABELS.items():
        if section.startswith(prefix):
            return label
    return section


def _is_procurement_group_header(c2: str, c6: str, c7: str, c9: str, c10: str) -> bool:
    # В расчетах групповые строки вроде "SCADA" или "Шкаф управления" служат
    # заголовками состава оборудования: у них есть название, но нет количества и сумм.
    return bool(c2 and not c6 and not c7 and not c9 and not c10)


def read_asup_rows(file_path: str) -> list[dict[int, str]]:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    # Расчеты КП/СС сейчас сохранены в старом формате .xls.
    # xlrd читает такой формат напрямую и не требует запускать Microsoft Excel.
    workbook = xlrd.open_workbook(str(path), formatting_info=False)
    if "АСУП" not in workbook.sheet_names():
        raise ValueError(f"В файле нет листа АСУП: {path}")

    sheet = workbook.sheet_by_name("АСУП")
    rows: list[dict[int, str]] = []
    for row_index in range(sheet.nrows):
        row: dict[int, str] = {"__row__": str(row_index + 1)}
        for col_index in range(min(sheet.ncols, 15)):
            value = _text(sheet.cell_value(row_index, col_index))
            if value:
                row[col_index + 1] = value
        if len(row) > 1:
            rows.append(row)
    return rows


def parse_calculation(file_path: str) -> dict[str, list[dict]]:
    rows = read_asup_rows(file_path)
    source_file = str(Path(file_path).expanduser().resolve())
    works: list[dict] = []
    procurement: list[dict] = []
    section = ""
    group_name = ""

    for row in rows:
        row_order = row.get("__row__", "")
        c1 = _cell(row, 1)
        c2 = _cell(row, 2)
        c3 = _cell(row, 3)
        c4 = _cell(row, 4)
        c5 = _cell(row, 5)
        c6 = _cell(row, 6)
        c7 = _cell(row, 7)
        c8 = _cell(row, 8)
        c9 = _cell(row, 9)
        c10 = _cell(row, 10)
        c12 = _cell(row, 12)
        c13 = _cell(row, 13)
        c15 = _cell(row, 15)

        # Лист АСУП разбит на numbered sections:
        # 1 - работы, 2 - сопутствующие расходы, 3-5 - оборудование и материалы.
        if re.match(r"^\d+\.", c2):
            section = c2
            group_name = ""
            continue
        if c2 in {"Наименование", "ИТОГО"}:
            continue

        if section.startswith("1."):
            if c2 and not c3:
                group_name = c2
            if c2 and c3:
                group_name = c2
            # Бюджетные строки являются производными от Excel.
            # Если часы или сумма нулевые/пустые, значит этой работы в расчете фактически нет.
            if c3 and c6 == "Нормочас" and _has_positive_quantity(c7) and _has_positive_sum(c9, c10):
                works.append(
                    {
                        "source_file": source_file,
                        "section": section,
                        "group_name": group_name,
                        "name": c3,
                        "unit": c6,
                        "quantity": _format_number(c7),
                        "unit_price": _format_number(c8),
                        "sum_no_vat": _format_number(c9),
                        "sum_with_vat": _format_number(c10),
                    }
                )
            continue

        if section.startswith("2."):
            if c2 and not c6 and not c7:
                group_name = c2
                continue
            # Сопутствующие расходы попадают в бюджет только при ненулевом количестве и ненулевой сумме.
            if c2 and _has_positive_quantity(c6) and _has_positive_sum(c9, c10):
                works.append(
                    {
                        "source_file": source_file,
                        "section": section,
                        "group_name": group_name,
                        "name": c2,
                        "unit": c5,
                        "quantity": _format_number(c6),
                        "unit_price": _format_number(c7),
                        "sum_no_vat": _format_number(c9),
                        "sum_with_vat": _format_number(c10),
                    }
                )
            continue

        if section.startswith(("3.", "4.", "5.")):
            if not c2 or c2 in {"ИТОГО", "Наименование"}:
                continue
            if c1 == "#Н/Д" and not c6 and _is_empty_amount(c9) and _is_empty_amount(c10):
                continue

            section_label = _section_label(section)
            if _is_procurement_group_header(c2, c6, c7, c9, c10):
                group_name = c2
                procurement.append(
                    {
                        "source_file": source_file,
                        "section": section_label,
                        "group_name": group_name,
                        "row_order": row_order,
                        "is_group_header": "1",
                        "name": c2,
                        "catalog_number": "",
                        "manufacturer": "",
                        "unit": "",
                        "quantity": "",
                        "unit_price_no_vat": "",
                        "unit_price_with_vat": "",
                        "sum_no_vat": "",
                        "sum_with_vat": "",
                        "install_hours": "",
                        "connection_hours": "",
                        "note": "",
                    }
                )
                continue

            if not c6 and not c7 and not c9 and not c10 and not c12 and not c13:
                continue
            procurement.append(
                {
                    "source_file": source_file,
                    "section": f"{section_label} / {group_name}" if group_name else section_label,
                    "group_name": group_name,
                    "row_order": row_order,
                    "is_group_header": "",
                    "name": c2,
                    "catalog_number": c3,
                    "manufacturer": c4,
                    "unit": c5,
                    "quantity": _format_number(c6),
                    "unit_price_no_vat": _format_number(c7),
                    "unit_price_with_vat": _format_number(c8),
                    "sum_no_vat": _format_number(c9),
                    "sum_with_vat": _format_number(c10),
                    # Эти часы сохраняем в БД как исходные данные расчета,
                    # но во вкладке "Закупки" не показываем: снабжению они не нужны.
                    "install_hours": _format_number(c12),
                    "connection_hours": _format_number(c13),
                    "note": c15,
                }
            )

    return {"works": works, "procurement": procurement}
