RISK_VALUE = {
    "низкая": 1,
    "низкое": 1,
    "средняя": 2,
    "среднее": 2,
    "высокая": 3,
    "высокое": 3,
}


def normalize_risk_value(value: str) -> int:
    cleaned = (value or "").strip().lower()
    if cleaned.isdigit():
        return max(0, min(int(cleaned), 3))
    return RISK_VALUE.get(cleaned, 0)


def calculate_risk_score(probability: str, impact: str) -> tuple[str, str]:
    # Простая матрица 3x3 понятнее на MVP, чем сложная методика: вероятность * влияние.
    score = normalize_risk_value(probability) * normalize_risk_value(impact)
    if score >= 6:
        return str(score), "Критичный"
    if score >= 3:
        return str(score), "Средний"
    if score >= 1:
        return str(score), "Низкий"
    return "", "Не оценен"
