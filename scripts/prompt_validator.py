#!/usr/bin/env python3
"""
Prompt Validator — валидатор промптов для Gemini Flash субагентов.
Проверяет промпт на 12 антипаттернов перед отправкой в invoke_subagent.

Запуск:
    uv run prompt_validator.py --input prompt.txt
    uv run prompt_validator.py --input prompt.txt --output report.json
    uv run prompt_validator.py --text "Ты — SEO-агент..."
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Fix Windows CP1251 encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════════
# 12 ПРОВЕРОК (АНТИПАТТЕРНОВ)
# ═══════════════════════════════════════════════════════════════

def check_ap01_hallucination(text: str) -> dict:
    """AP-01: Нет анти-галлюцинационных инструкций."""
    markers = [
        "ДАННЫЕ ОТСУТСТВУЮТ",
        "источник:",
        "ТОЛЬКО на основе данных",
        "не выдумывай",
        "не придумывай",
        "из файлов",
    ]
    found = [m for m in markers if m.lower() in text.lower()]
    passed = len(found) >= 2
    return {
        "id": "AP-01",
        "name": "Hallucination Guard",
        "severity": "CRITICAL",
        "passed": passed,
        "detail": f"Найдено {len(found)}/6 маркеров анти-галлюцинации"
                  + (f": {found}" if found else ". Добавь инструкции из anti_patterns.md#AP-01"),
    }


def check_ap02_hardcode(text: str) -> dict:
    """AP-02: Хардкод литеральных значений."""
    # Ищем конкретные даты, суммы в промпте (не в примерах)
    date_pattern = r"\b\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\b"
    money_pattern = r"\b\d{1,3}[\s\xa0]\d{3}\s*₽"
    
    dates = re.findall(date_pattern, text, re.IGNORECASE)
    money = re.findall(money_pattern, text)
    
    # Исключаем примеры (текст после "ПРИМЕР:" или "Выход:")
    example_section = text.lower().find("пример")
    if example_section > 0:
        check_text = text[:example_section]
        dates = re.findall(date_pattern, check_text, re.IGNORECASE)
        money = re.findall(money_pattern, check_text)
    
    issues = []
    if dates:
        issues.append(f"Хардкод дат: {dates[:3]}")
    if money:
        issues.append(f"Хардкод сумм: {money[:3]}")
    
    passed = len(issues) == 0
    return {
        "id": "AP-02",
        "name": "Hardcode Guard",
        "severity": "CRITICAL",
        "passed": passed,
        "detail": "; ".join(issues) if issues else "Литеральные значения не обнаружены",
    }


def check_ap03_precision(text: str) -> dict:
    """AP-03: Нет инструкций точного исполнения."""
    markers = [
        "ровно",
        "только",
        "не добавляй",
        "не создавай файлы",
        "перечитай задачу",
        "все пункты выполнены",
        "лишних",
    ]
    found = [m for m in markers if m.lower() in text.lower()]
    passed = len(found) >= 2
    return {
        "id": "AP-03",
        "name": "Precision Guard",
        "severity": "HIGH",
        "passed": passed,
        "detail": f"Найдено {len(found)}/7 маркеров точности"
                  + ("" if passed else ". Добавь: 'Выполняй РОВНО задачу. Перечитай перед отправкой.'"),
    }


def check_ap04_negative(text: str) -> dict:
    """AP-04: Негативные промпты без позитивной альтернативы."""
    neg_patterns = [
        r"(?i)\bне\s+делай\b",
        r"(?i)\bне\s+используй\b",
        r"(?i)\bне\s+пиши\b",
        r"(?i)\bне\s+отвечай\b",
        r"(?i)\bзапрещено\b",
        r"(?i)\bнельзя\b",
    ]
    pos_patterns = [
        r"(?i)\bвместо\b",
        r"(?i)\bвсегда\b",
        r"(?i)\bиспользуй\b",
    ]
    
    negatives = sum(1 for p in neg_patterns if re.search(p, text))
    positives = sum(1 for p in pos_patterns if re.search(p, text))
    
    passed = negatives == 0 or positives >= negatives
    return {
        "id": "AP-04",
        "name": "Positive Prompting",
        "severity": "HIGH",
        "passed": passed,
        "detail": f"Негативных: {negatives}, Позитивных: {positives}"
                  + ("" if passed else ". Замени 'НЕ ДЕЛАЙ X' на 'ВМЕСТО X ДЕЛАЙ Y'"),
    }


def check_ap05_context(text: str) -> dict:
    """AP-05: Отсутствие контекстного блока."""
    has_reads = bool(re.search(r"(?i)(прочитай|reads|📥|входн)", text))
    has_writes = bool(re.search(r"(?i)(результат|writes|📤|выходн|выход)", text))
    has_index = bool(re.search(r"(?i)(разметка|index|🏷️|тег[иа])", text))
    
    score = sum([has_reads, has_writes, has_index])
    passed = score >= 2
    return {
        "id": "AP-05",
        "name": "Context Block",
        "severity": "CRITICAL",
        "passed": passed,
        "detail": f"📥 READS: {'✓' if has_reads else '✗'}, "
                  f"📤 WRITES: {'✓' if has_writes else '✗'}, "
                  f"🏷️ INDEX: {'✓' if has_index else '✗'}",
    }


def check_ap06_universal(text: str) -> dict:
    """AP-06: Слишком много обязанностей для одного агента."""
    task_markers = [
        r"(?i)проанализируй",
        r"(?i)напиши\s+код",
        r"(?i)сгенерируй",
        r"(?i)проведи\s+ревью",
        r"(?i)создай\s+тест",
        r"(?i)оптимизируй",
        r"(?i)рефактор",
        r"(?i)задеплой",
    ]
    count = sum(1 for p in task_markers if re.search(p, text))
    passed = count <= 3
    return {
        "id": "AP-06",
        "name": "Single Responsibility",
        "severity": "HIGH",
        "passed": passed,
        "detail": f"Обнаружено обязанностей: {count}"
                  + ("" if passed else ". Разбей на несколько микро-агентов (макс. 3 обязанности)"),
    }


def check_ap07_cot(text: str) -> dict:
    """AP-07: Отсутствие Chain-of-Thought."""
    markers = [
        "thinking",
        "reasoning",
        "ход мыслей",
        "думай",
        "step-by-step",
        "пошагов",
        "перед принятием решения",
    ]
    found = [m for m in markers if m.lower() in text.lower()]
    passed = len(found) >= 1
    return {
        "id": "AP-07",
        "name": "Chain-of-Thought",
        "severity": "HIGH",
        "passed": passed,
        "detail": f"CoT маркеры: {found}" if found
                  else "CoT отсутствует. Добавь: 'Перед решением запиши ход мыслей'",
    }


def check_ap08_json_depth(text: str) -> dict:
    """AP-08: Глубокая JSON-вложенность."""
    # Считаем максимальную вложенность { в примерах JSON
    max_depth = 0
    current = 0
    in_json = False
    for char in text:
        if char == '{':
            current += 1
            in_json = True
            max_depth = max(max_depth, current)
        elif char == '}':
            current = max(0, current - 1)
    
    passed = max_depth <= 3
    return {
        "id": "AP-08",
        "name": "JSON Depth",
        "severity": "MEDIUM",
        "passed": passed,
        "detail": f"Макс. вложенность JSON: {max_depth}"
                  + ("" if passed else ". Уплости JSON до 2-3 уровней"),
    }


def check_ap09_contradictions(text: str) -> dict:
    """AP-09: Противоречия в промпте."""
    contradictions = []
    if re.search(r"(?i)кратко", text) and re.search(r"(?i)(подробн|детальн|исчерпывающ)", text):
        contradictions.append("'кратко' + 'подробно/детально'")
    if re.search(r"(?i)не\s+отвечай\s+текст", text) and re.search(r"(?i)объясни", text):
        contradictions.append("'не отвечай текстом' + 'объясни'")
    
    passed = len(contradictions) == 0
    return {
        "id": "AP-09",
        "name": "Contradiction Check",
        "severity": "HIGH",
        "passed": passed,
        "detail": f"Противоречия: {contradictions}" if contradictions
                  else "Явных противоречий не обнаружено",
    }


def check_ap10_fewshot(text: str) -> dict:
    """AP-10: Отсутствие few-shot примеров."""
    markers = [
        r"(?i)пример\s*\d*:",
        r"(?i)вход:",
        r"(?i)выход:",
        r"(?i)example",
        r"(?i)input:",
        r"(?i)output:",
    ]
    found = sum(1 for p in markers if re.search(p, text))
    passed = found >= 2
    return {
        "id": "AP-10",
        "name": "Few-Shot Examples",
        "severity": "MEDIUM",
        "passed": passed,
        "detail": f"Маркеры примеров: {found}"
                  + ("" if passed else ". Добавь 2-3 примера идеального ввода-вывода"),
    }


def check_ap11_length(text: str) -> dict:
    """AP-11: Слишком длинный промпт без структуры."""
    word_count = len(text.split())
    has_structure = bool(re.search(r"(#{1,3}\s|<\w+>|\[БЛОК|📥|📤|🏷️)", text))
    
    passed = word_count <= 2000 or has_structure
    return {
        "id": "AP-11",
        "name": "Length & Structure",
        "severity": "MEDIUM",
        "passed": passed,
        "detail": f"Слов: {word_count}, Структура: {'✓' if has_structure else '✗'}"
                  + ("" if passed else ". Разбей на XML/Markdown блоки"),
    }


def check_ap12_validation(text: str) -> dict:
    """AP-12: Нет упоминания валидации ответа."""
    markers = ["валидац", "zod", "проверь", "верифиц", "убедись"]
    found = [m for m in markers if m.lower() in text.lower()]
    passed = len(found) >= 1
    return {
        "id": "AP-12",
        "name": "Response Validation",
        "severity": "MEDIUM",
        "passed": passed,
        "detail": f"Маркеры валидации: {found}" if found
                  else "Нет упоминания валидации. Добавь: 'Перечитай задачу и проверь'",
    }


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def check_ap13_micromanagement(text: str) -> dict:
    """AP-13: Micromanagement (Оркестратор пытается писать код сам)."""
    markers = [r"(?i)напиши\s+код", r"(?i)отредактируй", r"(?i)сверстай"]
    delegation_markers = [r"(?i)invoke_subagent", r"(?i)define_subagent", r"(?i)делегируй"]
    
    has_micro = sum(1 for p in markers if re.search(p, text))
    has_delegation = sum(1 for p in delegation_markers if re.search(p, text))
    
    passed = has_micro == 0 and has_delegation > 0
    return {
        "id": "AP-13",
        "name": "Micromanagement Guard",
        "severity": "CRITICAL",
        "passed": passed,
        "detail": "Оркестратор делегирует задачи" if passed
                  else "Оркестратор пытается сам писать код (или нет invoke_subagent). Требуется делегирование.",
    }

def check_ap14_blind_trust(text: str) -> dict:
    """AP-14: Blind Trust (Отсутствие кросс-валидации субагентов)."""
    markers = [r"(?i)кросс-валидация", r"(?i)проверь\s+ответы", r"(?i)сравни", r"(?i)синтезируй", r"(?i)валидируй"]
    found = [m for m in markers if re.search(m, text)]
    passed = len(found) > 0
    return {
        "id": "AP-14",
        "name": "Blind Trust Guard",
        "severity": "HIGH",
        "passed": passed,
        "detail": "Найдено требование кросс-валидации" if passed
                  else "Нет инструкций на проверку/синтез ответов субагентов. Оркестратор не должен верить вслепую.",
    }

def check_ap15_memory_overload(text: str) -> dict:
    """AP-15: Memory Overload (Отсутствие работы с файлами/scratch)."""
    markers = [r"(?i)scratch", r"(?i)путь\s+к\s+файлу", r"(?i)сохрани\s+в\s+файл", r"(?i)артефакт"]
    found = [m for m in markers if re.search(m, text)]
    passed = len(found) > 0
    return {
        "id": "AP-15",
        "name": "Memory Overload Guard",
        "severity": "HIGH",
        "passed": passed,
        "detail": "Правила сохранения больших артефактов присутствуют" if passed
                  else "Нет инструкций для субагентов сохранять логи/отчеты в файлы. Переполнение контекста (send_message) неизбежно.",
    }

def check_ap16_sequence(text: str) -> dict:
    """AP-16: Sequence Guard (Защита последовательных топологий от хаоса)."""
    # Если топология явно не Pipeline, пропускаем проверку (авто-pass)
    if not re.search(r"(?i)топология.*(pipeline|последовательн)", text):
        return {
            "id": "AP-16",
            "name": "Sequence Guard (Skipped)",
            "severity": "HIGH",
            "passed": True,
            "detail": "Не Pipeline топология, проверка пропущена."
        }
    
    markers = [r"(?i)дождись", r"(?i)получив\s+ответ", r"(?i)последовательно", r"(?i)сначала.*затем"]
    found = [m for m in markers if re.search(m, text)]
    passed = len(found) > 0
    return {
        "id": "AP-16",
        "name": "Sequence Guard",
        "severity": "HIGH",
        "passed": passed,
        "detail": "Найдены маркеры последовательного ожидания" if passed
                  else "Отсутствуют инструкции для последовательного ожидания. Оркестратор запустит всех одновременно!",
    }


def check_ap17_retry_limit(text: str) -> dict:
    """AP-17: Retry Limit Guard (Защита от бесконечных циклов)."""
    markers = [r"(?i)максимум\s*\d+\s*итераци", r"(?i)лимит.*попыток", r"(?i)не\s*более\s*\d+\s*раз"]
    found = [m for m in markers if re.search(m, text)]
    passed = len(found) > 0
    return {
        "id": "AP-17",
        "name": "Retry Limit Guard",
        "severity": "HIGH",
        "passed": passed,
        "detail": "Установлен лимит на итерации правок субагентов" if passed
                  else "Отсутствует ограничение на количество итераций (Retry Loop). Рой может зависнуть в бесконечном цикле правок.",
    }

def check_ap18_escalation(text: str) -> dict:
    """AP-18: Escalation Protocol Guard (Когда звать человека)."""
    markers = [r"(?i)ask_question", r"(?i)эскалируй", r"(?i)спроси\s+пользователя", r"(?i)обратись\s+ко\s+мне"]
    found = [m for m in markers if re.search(m, text)]
    passed = len(found) > 0
    return {
        "id": "AP-18",
        "name": "Escalation Protocol Guard",
        "severity": "HIGH",
        "passed": passed,
        "detail": "Протокол эскалации к пользователю настроен" if passed
                  else "Нет правил для вызова пользователя (ask_question). Оркестратор может принимать фатальные решения автономно.",
    }


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def get_checks_for_mode(mode: str) -> list:
    checks = [
        check_ap01_hallucination,
        check_ap02_hardcode,
        check_ap03_precision,
        check_ap04_negative,
        check_ap05_context,
        check_ap07_cot,
        check_ap08_json_depth,
        check_ap09_contradictions,
        check_ap10_fewshot,
        check_ap11_length,
        check_ap12_validation,
    ]
    if mode == "orchestrator":
        checks.extend([
            check_ap13_micromanagement,
            check_ap14_blind_trust,
            check_ap15_memory_overload,
            check_ap16_sequence,
            check_ap17_retry_limit,
            check_ap18_escalation
        ])
    else:
        checks.append(check_ap06_universal)
    return checks


def validate_prompt(text: str, mode: str = "worker") -> dict:
    checks = get_checks_for_mode(mode)
    results = [check(text) for check in checks]
    
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    critical_fails = [r for r in results if not r["passed"] and r["severity"] == "CRITICAL"]
    
    score = round(passed / len(results) * 100)
    
    if score >= 90 and not critical_fails:
        grade = "A"
    elif score >= 75 and not critical_fails:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"
    
    return {
        "score": score,
        "grade": grade,
        "passed": passed,
        "failed": failed,
        "total": len(results),
        "critical_failures": [r["id"] for r in critical_fails],
        "checks": results,
    }


def print_report(report: dict, mode: str) -> None:
    print(f"\n{'='*60}")
    print(f"  PROMPT VALIDATOR REPORT (Mode: {mode.upper()})")
    print(f"  Score: {report['score']}% | Grade: {report['grade']}")
    print(f"  Passed: {report['passed']}/{report['total']}")
    print(f"{'='*60}\n")
    
    for check in report["checks"]:
        icon = "[PASS]" if check["passed"] else "[FAIL]"
        sev = f"[{check['severity']}]"
        print(f"  {icon} {check['id']} {check['name']} {sev}")
        print(f"     {check['detail']}\n")
    
    if report["critical_failures"]:
        print(f"  !!! CRITICAL FAILURES: {', '.join(report['critical_failures'])}")
        print(f"  !!! Fix these before using the prompt!\n")


def main():
    parser = argparse.ArgumentParser(
        description="Validate a prompt against 12+ anti-patterns for Gemini Flash"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", type=str, help="Path to prompt text file")
    group.add_argument("--text", type=str, help="Prompt text directly")
    parser.add_argument("--output", type=str, help="Path to save JSON report")
    parser.add_argument("--mode", type=str, choices=["worker", "orchestrator"], default="worker", help="Validation mode")
    
    args = parser.parse_args()
    
    if args.input:
        path = Path(args.input)
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text(encoding="utf-8")
    else:
        text = args.text
    
    report = validate_prompt(text, args.mode)
    print_report(report, args.mode)
    
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Report saved to: {out_path}")
    
    # Exit code: 1 if any critical failure
    sys.exit(1 if report["critical_failures"] else 0)


if __name__ == "__main__":
    main()
