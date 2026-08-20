#!/usr/bin/env python3
"""
Пересчёт таймингов оперативной памяти из отчёта ZenTimings (.html)
на другую частоту с сохранением (или увеличением) задержки в наносекундах.

Использование:
    python zentimings_convert.py
Скрипт спросит:
    1) путь к html-отчёту ZenTimings
    2) целевую частоту памяти (MT/s)
и выведет / сохранит таблицу с 5 столбцами:
    Тайминг | Значение(старая) | нс(старая) | Значение(новая) | нс(новая)
"""

import re
import sys
import csv
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Библиотека beautifulsoup4 не найдена.")
    print("Запустите скрипт через run_windows.bat (Windows) или run_linux.sh (Linux/Mac) —")
    print("они сами создадут виртуальное окружение (.venv) и установят зависимости.")
    print("Либо вручную: pip install beautifulsoup4")
    sys.exit(1)


def parse_zentimings(html_path: Path):
    """Извлекает частоту памяти (MT/s) и тайминги (DCT0) из отчёта ZenTimings."""
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")

    table = soup.find("table", id="timingsTable")
    if table is None:
        raise ValueError("Не найдена таблица Memory Timings (id='timingsTable') в отчёте.")

    rows = table.find_all("tr")
    timings = {}
    base_freq = None

    for tr in rows[1:]:  # первая строка — заголовок
        cells = tr.find_all("td")
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
        raise ValueError("Не удалось найти строку 'Frequency' в таблице Memory Timings.")

    return base_freq, timings


def convert_timings(base_freq: float, new_freq: float, timings: dict):
    """
    Пересчитывает тайминги в тактах на новую частоту, сохраняя
    задержку в нс равной или больше исходной (округление вверх).
    """
    base_clk = base_freq / 2.0  # действительная частота DRAM, МГц
    new_clk = new_freq / 2.0

    result = []
    for name, cyc in timings.items():
        ns_old = cyc / base_clk * 1000.0

        if cyc == 0:
            cyc_new = 0
        else:
            import math
            cyc_new = math.ceil(ns_old * new_clk / 1000.0)
            if cyc_new < 1:
                cyc_new = 1

        ns_new = cyc_new / new_clk * 1000.0
        result.append((name, cyc, ns_old, cyc_new, ns_new))

    return result


def print_table(rows, base_freq, new_freq):
    header = (
        f"{'Тайминг':<12}{'Знач.@' + str(int(base_freq)):<12}"
        f"{'нс@' + str(int(base_freq)):<12}{'Знач.@' + str(int(new_freq)):<12}"
        f"{'нс@' + str(int(new_freq)):<12}"
    )
    print(header)
    print("-" * len(header))
    for name, cyc, ns_old, cyc_new, ns_new in rows:
        print(f"{name:<12}{cyc:<12}{ns_old:<12.3f}{cyc_new:<12}{ns_new:<12.3f}")


def save_csv(rows, base_freq, new_freq, out_path: Path):
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "Тайминг",
            f"Значение@{int(base_freq)}",
            f"нс@{int(base_freq)}",
            f"Значение@{int(new_freq)}",
            f"нс@{int(new_freq)}",
        ])
        for name, cyc, ns_old, cyc_new, ns_new in rows:
            writer.writerow([name, cyc, f"{ns_old:.3f}", cyc_new, f"{ns_new:.3f}"])
    print(f"\nСохранено: {out_path}")


def main():
    path_str = input("Путь к html-отчёту ZenTimings: ").strip().strip('"')
    html_path = Path(path_str)
    if not html_path.exists():
        print(f"Файл не найден: {html_path}")
        sys.exit(1)

    freq_str = input("Целевая частота памяти, MT/s (например 6400): ").strip()
    try:
        new_freq = float(freq_str)
    except ValueError:
        print("Некорректное значение частоты.")
        sys.exit(1)

    base_freq, timings = parse_zentimings(html_path)
    print(f"\nИсходная частота из отчёта: {base_freq:.0f} MT/s")
    print(f"Найдено таймингов: {len(timings)}\n")

    rows = convert_timings(base_freq, new_freq, timings)
    print_table(rows, base_freq, new_freq)

    out_path = html_path.with_name(f"timings_{int(base_freq)}_to_{int(new_freq)}.csv")
    save_csv(rows, base_freq, new_freq, out_path)


if __name__ == "__main__":
    main()
