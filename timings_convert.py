#!/usr/bin/env python3
"""
Timings Frequency Converter — консольная версия.

Пересчёт таймингов оперативной памяти из отчёта ZenTimings (.html)
на другую частоту с сохранением (или увеличением) задержки в наносекундах.

Console version. Recalculates ZenTimings memory timings for a different
frequency, preserving (or improving) the latency in nanoseconds.

Использование / Usage:
    python timings_convert.py
Скрипт спросит язык, путь к отчёту, целевую частоту и режим округления.
The script asks for the language, report path, target frequency and mode.
"""

import re
import sys
import csv
import math
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Библиотека beautifulsoup4 не найдена. / beautifulsoup4 library not found.")
    print("Установите: pip install beautifulsoup4")
    sys.exit(1)


TR = {
    "ask_lang": {
        "ru": "Выберите язык / Choose language — [1] Русский / [2] English: ",
        "en": "Выберите язык / Choose language — [1] Русский / [2] English: ",
    },
    "ask_path": {"ru": "Путь к html-отчёту ZenTimings: ", "en": "Path to ZenTimings html report: "},
    "file_not_found": {"ru": "Файл не найден: {path}", "en": "File not found: {path}"},
    "ask_freq": {
        "ru": "Целевая частота памяти, MT/s (например 6400): ",
        "en": "Target memory frequency, MT/s (e.g. 6400): ",
    },
    "bad_freq": {"ru": "Некорректное значение частоты.", "en": "Invalid frequency value."},
    "ask_mode": {
        "ru": "Режим округления — [1] безопасный, не хуже исходного (по умолчанию) / [2] ближайшее значение: ",
        "en": "Rounding mode — [1] safe, not worse than original (default) / [2] nearest value: ",
    },
    "base_freq_from_report": {"ru": "Исходная частота из отчёта: {f:.0f} MT/s", "en": "Base frequency from report: {f:.0f} MT/s"},
    "timings_found": {"ru": "Найдено таймингов: {n}", "en": "Timings found: {n}"},
    "saved": {"ru": "Сохранено: {path}", "en": "Saved: {path}"},
    "col_timing": {"ru": "Тайминг", "en": "Timing"},
    "err_no_table": {
        "ru": "Не найдена таблица Memory Timings (id='timingsTable') в отчёте.",
        "en": "Memory Timings table not found (id='timingsTable') in the report.",
    },
    "err_no_freq_row": {
        "ru": "Не удалось найти строку 'Frequency' в таблице Memory Timings.",
        "en": "Could not find the 'Frequency' row in the Memory Timings table.",
    },
}

LANG = "ru"


def tr(key, **kwargs):
    text = TR[key][LANG]
    return text.format(**kwargs) if kwargs else text


def parse_zentimings(html_path: Path):
    """Извлекает частоту памяти (MT/s) и тайминги (DCT0) из отчёта ZenTimings."""
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")

    table = soup.find("table", id="timingsTable")
    if table is None:
        raise ValueError(tr("err_no_table"))

    rows = table.find_all("tr")
    timings = {}
    base_freq = None

    for tr_ in rows[1:]:  # первая строка — заголовок
        cells = tr_.find_all("td")
        if len(cells) < 2:
            continue
        name = cells[0].get_text(strip=True)
        val0 = cells[1].get_text(strip=True)

        if name == "Frequency":
            try:
                base_freq = float(val0)
            except ValueError:
                pass
            continue

        if name in ("Ratio",):
            # не тайминг задержки, а множитель делителя частоты — пропускаем
            continue

        # берём только чисто числовые тайминги (в тактах)
        if re.fullmatch(r"-?\d+", val0):
            timings[name] = int(val0)
        # пропускаем нечисловые (Enabled/Disabled, 1T, "2/3/1", RFCns, REFIns, RefreshMode и т.п.)

    if base_freq is None:
        raise ValueError(tr("err_no_freq_row"))

    return base_freq, timings


def convert_timings(base_freq: float, new_freq: float, timings: dict, mode: str = "safe"):
    """
    Пересчитывает тайминги в тактах на новую частоту.

    mode="safe" (по умолчанию): округление в "безопасную" сторону.
        Для обычных таймингов (латентность, меньше = лучше) — вверх,
        задержка в нс не меньше исходной.
        Для REFI (интервал обновления, больше = лучше) — вниз,
        задержка в нс не больше исходной (безопасное направление —
        не увеличивать интервал между обновлениями).
    mode="nearest": просто ближайшее достижимое значение, без
        гарантии "не хуже исходного" в любую сторону.
    """
    base_clk = base_freq / 2.0  # действительная частота DRAM, МГц
    new_clk = new_freq / 2.0

    result = []
    for name, cyc in timings.items():
        ns_old = cyc / base_clk * 1000.0

        if cyc == 0:
            cyc_new = 0
        else:
            exact = ns_old * new_clk / 1000.0
            if mode == "nearest":
                lower, upper = math.floor(exact), math.ceil(exact)
                candidates = [c for c in (lower, upper) if c >= 1] or [1]
                cyc_new = min(candidates, key=lambda c: abs((c / new_clk * 1000.0) - ns_old))
            elif name == "REFI":
                cyc_new = math.floor(exact)
                if cyc_new < 1:
                    cyc_new = 1
            else:
                cyc_new = math.ceil(exact)
                if cyc_new < 1:
                    cyc_new = 1

        ns_new = cyc_new / new_clk * 1000.0
        result.append((name, cyc, ns_old, cyc_new, ns_new))

    return result


def print_table(rows, base_freq, new_freq):
    header = (
        f"{tr('col_timing'):<12}{'@' + str(int(base_freq)):<12}"
        f"{'ns@' + str(int(base_freq)):<12}{'@' + str(int(new_freq)):<12}"
        f"{'ns@' + str(int(new_freq)):<12}"
    )
    print(header)
    print("-" * len(header))
    for name, cyc, ns_old, cyc_new, ns_new in rows:
        print(f"{name:<12}{cyc:<12}{ns_old:<12.3f}{cyc_new:<12}{ns_new:<12.3f}")


def save_csv(rows, base_freq, new_freq, out_path: Path):
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            tr("col_timing"),
            f"{'Значение' if LANG == 'ru' else 'Value'}@{int(base_freq)}",
            f"{'нс' if LANG == 'ru' else 'ns'}@{int(base_freq)}",
            f"{'Значение' if LANG == 'ru' else 'Value'}@{int(new_freq)}",
            f"{'нс' if LANG == 'ru' else 'ns'}@{int(new_freq)}",
        ])
        for name, cyc, ns_old, cyc_new, ns_new in rows:
            writer.writerow([name, cyc, f"{ns_old:.3f}", cyc_new, f"{ns_new:.3f}"])
    print(tr("saved", path=out_path))


def main():
    global LANG
    lang_str = input(TR["ask_lang"]["ru"]).strip()
    LANG = "en" if lang_str == "2" else "ru"

    path_str = input(tr("ask_path")).strip().strip('"')
    html_path = Path(path_str)
    if not html_path.exists():
        print(tr("file_not_found", path=html_path))
        sys.exit(1)

    freq_str = input(tr("ask_freq")).strip()
    try:
        new_freq = float(freq_str)
    except ValueError:
        print(tr("bad_freq"))
        sys.exit(1)

    mode_str = input(tr("ask_mode")).strip()
    mode = "nearest" if mode_str == "2" else "safe"

    base_freq, timings = parse_zentimings(html_path)
    print(f"\n{tr('base_freq_from_report', f=base_freq)}")
    print(f"{tr('timings_found', n=len(timings))}\n")

    rows = convert_timings(base_freq, new_freq, timings, mode=mode)
    print_table(rows, base_freq, new_freq)

    out_path = html_path.with_name(f"timings_{int(base_freq)}_to_{int(new_freq)}.csv")
    save_csv(rows, base_freq, new_freq, out_path)


if __name__ == "__main__":
    main()