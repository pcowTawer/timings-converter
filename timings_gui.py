#!/usr/bin/env python3
"""
Timings Frequency Converter — небольшое GUI-приложение.

Открывает html-отчёт ZenTimings, пересчитывает тайминги на указанную
частоту и показывает результат в таблице. Экспорт в CSV — через меню "Файл".
Поддерживает переключение языка интерфейса (RU/EN) на лету.

Сборка в .exe: см. build_windows.bat / build_linux.sh в репозитории.
"""

import re
import sys
import csv
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Библиотека beautifulsoup4 не найдена. / beautifulsoup4 library not found.")
    print("Запустите приложение через build_*/venv-скрипты, либо: pip install beautifulsoup4")
    sys.exit(1)


TIMING_NAMES = [
    "RFCsb", "CL", "RCDWR", "RCDRD", "RP", "RAS", "RC", "RRDS", "RRDL", "FAW",
    "WTRS", "WTRL", "WR", "RDRDSCL", "WRWRSCL", "CWL", "RTP", "RDWR", "WRRD",
    "RDRDSC", "RDRDSD", "RDRDDD", "WRWRSC", "WRWRSD", "WRWRDD", "TRCPAGE", "CKE",
    "STAG", "STAGsb", "MOD", "MODPDA", "MRD", "MRDPDA", "RFC", "RFC2", "REFI",
    "XP", "PHYWRD", "PHYWRL", "PHYRDL", "WRPRE", "RDPRE", "RDPOST", "WRPOST", "FGR",
]


# --- локализация ---------------------------------------------------------

CURRENT_LANG = "ru"

TR = {
    "app_title": {"ru": "Timings Frequency Converter", "en": "Timings Frequency Converter"},
    "menu_file": {"ru": "Файл", "en": "File"},
    "menu_new": {"ru": "Новый (ввести вручную)...", "en": "New (manual entry)..."},
    "menu_open_report": {"ru": "Открыть отчёт...", "en": "Open report..."},
    "menu_open_csv": {"ru": "Открыть CSV...", "en": "Open CSV..."},
    "menu_export_csv": {"ru": "Экспорт в CSV...", "en": "Export to CSV..."},
    "menu_exit": {"ru": "Выход", "en": "Exit"},
    "menu_lang": {"ru": "Язык", "en": "Language"},
    "lang_ru": {"ru": "Русский", "en": "Russian"},
    "lang_en": {"ru": "English", "en": "English"},

    "label_report": {"ru": "Отчёт ZenTimings:", "en": "ZenTimings report:"},
    "btn_browse": {"ru": "Обзор...", "en": "Browse..."},
    "label_base_freq": {"ru": "Исходная частота (MT/s):", "en": "Base frequency (MT/s):"},
    "label_new_freq": {"ru": "Целевая частота (MT/s):", "en": "Target frequency (MT/s):"},
    "label_round_mode": {"ru": "Режим округления:", "en": "Rounding mode:"},
    "mode_safe": {"ru": "Безопасный (не хуже исходного)", "en": "Safe (not worse than original)"},
    "mode_nearest": {"ru": "Ближайшее значение", "en": "Nearest value"},
    "btn_calc": {"ru": "Пересчитать", "en": "Convert"},

    "col_timing": {"ru": "Тайминг", "en": "Timing"},
    "col_val_old": {"ru": "Значение (старая)", "en": "Value (old)"},
    "col_ns_old": {"ru": "нс (старая)", "en": "ns (old)"},
    "col_val_new": {"ru": "Значение (новая)", "en": "Value (new)"},
    "col_ns_new": {"ru": "нс (новая)", "en": "ns (new)"},
    "col_val_at": {"ru": "Значение @{f}", "en": "Value @{f}"},
    "col_ns_at": {"ru": "нс @{f}", "en": "ns @{f}"},

    "hint": {
        "ru": "Двойной клик по «Значение» или «нс» — редактировать (при вводе нс подбирается ближайшее целое число тактов). Частоту можно менять выше.",
        "en": "Double-click a \"Value\" or \"ns\" cell to edit (entering ns snaps to the nearest whole cycle). Frequency fields above are editable.",
    },

    "status_empty": {
        "ru": "Пустая таблица со стандартными таймингами ZenTimings. Введите частоту и значения.",
        "en": "Empty table with standard ZenTimings entries. Enter the frequency and values.",
    },
    "status_imported_report": {
        "ru": "Импортировано таймингов: {n}. Частота из отчёта: {f} MT/s (можно менять).",
        "en": "Imported {n} timings. Frequency from report: {f} MT/s (editable).",
    },
    "status_imported_csv": {
        "ru": "Импортировано из CSV: {n} таймингов.",
        "en": "Imported {n} timings from CSV.",
    },
    "status_done": {
        "ru": "Готово. Строк: {n}.",
        "en": "Done. Rows: {n}.",
    },
    "status_nearest": {
        "ru": "{name}: ближайшее время к {target} нс — {best} нс ({cyc} такт.).",
        "en": "{name}: closest time to {target} ns is {best} ns ({cyc} cycles).",
    },
    "status_saved": {
        "ru": "Сохранено: {path}",
        "en": "Saved: {path}",
    },
    "status_changed_language": {
        "ru": "Язык изменён на русский.",
        "en": "Language changed to english.",
    },
    

    "err_title": {"ru": "Ошибка", "en": "Error"},
    "warn_title": {"ru": "Внимание", "en": "Warning"},
    "done_title": {"ru": "Готово", "en": "Done"},

    "err_read_report": {"ru": "Не удалось прочитать отчёт: {e}", "en": "Could not read report: {e}"},
    "err_read_csv": {"ru": "Не удалось прочитать CSV: {e}", "en": "Could not read CSV: {e}"},
    "err_csv_no_timings": {"ru": "В файле не найдено ни одного тайминга.", "en": "No timings found in the file."},
    "err_no_freq_first": {"ru": "Сначала укажите {which} частоту.", "en": "Please set the {which} frequency first."},
    "which_base": {"ru": "исходную", "en": "base"},
    "which_target": {"ru": "целевую", "en": "target"},
    "err_int_expected": {"ru": "Тайминг (такты) должен быть целым числом.", "en": "Timing (cycles) must be a whole number."},
    "err_ns_expected": {"ru": "Время должно быть числом (нс).", "en": "Time must be a number (ns)."},
    "err_no_active_timings": {
        "ru": "Нет заполненных таймингов. Импортируйте отчёт или введите значения вручную.",
        "en": "No timings filled in. Import a report or enter values manually.",
    },
    "err_base_freq_number": {"ru": "Укажите исходную частоту (MT/s), числом.", "en": "Enter the base frequency (MT/s) as a number."},
    "err_new_freq_number": {"ru": "Целевая частота должна быть числом.", "en": "Target frequency must be a number."},
    "warn_table_empty": {"ru": "Таблица пуста.", "en": "Table is empty."},

    "dlg_choose_report": {"ru": "Выберите отчёт ZenTimings", "en": "Choose a ZenTimings report"},
    "dlg_choose_csv": {"ru": "Выберите CSV, экспортированный этим приложением", "en": "Choose a CSV exported by this app"},
    "dlg_save_csv": {"ru": "Сохранить как CSV", "en": "Save as CSV"},
    "filetype_html": {"ru": "HTML файлы", "en": "HTML files"},
    "filetype_csv": {"ru": "CSV файлы", "en": "CSV files"},
    "filetype_all": {"ru": "Все файлы", "en": "All files"},
    "exported_to": {"ru": "Экспортировано в:\n{path}", "en": "Exported to:\n{path}"},

    "csv_not_5_cols": {
        "ru": "Не похоже на CSV, экспортированный этим приложением (ожидается 5 столбцов).",
        "en": "Doesn't look like a CSV exported by this app (5 columns expected).",
    },
    "csv_empty": {"ru": "Файл пуст.", "en": "File is empty."},
    "err_no_timings_table": {
        "ru": "Не найдена таблица Memory Timings (id='timingsTable') в отчёте.",
        "en": "Memory Timings table not found (id='timingsTable') in the report.",
    },
    "err_no_frequency_row": {
        "ru": "Не удалось найти строку 'Frequency' в таблице Memory Timings.",
        "en": "Could not find the 'Frequency' row in the Memory Timings table.",
    },
}


def tr(key, **kwargs):
    text = TR[key][CURRENT_LANG]
    return text.format(**kwargs) if kwargs else text


# --- парсинг / расчёт (независимо от языка) -------------------------------

def parse_exported_csv(csv_path: Path):
    """Читает CSV, ранее экспортированный этим приложением.
    Возвращает (base_freq, new_freq, timings, new_timings) —
    new_freq/new_timings могут быть None/пустыми, если новая частота
    ещё не была посчитана на момент экспорта."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        rows = list(reader)

    if not rows:
        raise ValueError(tr("csv_empty"))

    header = rows[0]
    if len(header) < 5:
        raise ValueError(tr("csv_not_5_cols"))

    def extract_freq(col_name):
        m = re.search(r"@(\d+)", col_name)
        return float(m.group(1)) if m else None

    base_freq = extract_freq(header[1])
    new_freq = extract_freq(header[3])

    timings = {}
    new_timings = {}
    for row in rows[1:]:
        if len(row) < 5 or not row[0]:
            continue
        name = row[0]
        if re.fullmatch(r"-?\d+", row[1].strip()):
            timings[name] = int(row[1].strip())
        if re.fullmatch(r"-?\d+", row[3].strip()):
            new_timings[name] = int(row[3].strip())

    return base_freq, new_freq, timings, new_timings


def parse_zentimings(html_path: Path):
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    table = soup.find("table", id="timingsTable")
    if table is None:
        raise ValueError(tr("err_no_timings_table"))

    rows = table.find_all("tr")
    timings = {}
    base_freq = None

    for tr_ in rows[1:]:
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

        if name == "Ratio":
            continue

        if re.fullmatch(r"-?\d+", val0):
            timings[name] = int(val0)

    if base_freq is None:
        raise ValueError(tr("err_no_frequency_row"))

    return base_freq, timings


def convert_timings(base_freq: float, new_freq: float, timings: dict, mode: str = "safe"):
    """
    mode="safe": округление в "безопасную" сторону — не хуже исходного.
        Для обычных таймингов (латентность) — вверх (нс не меньше исходного).
        Для REFI (больше = лучше) — вниз (нс не больше исходного), так как
        безопасное направление для интервала обновления — не увеличивать его.
    mode="nearest": просто ближайшее достижимое значение без гарантии "не хуже".
    """
    base_clk = base_freq / 2.0
    new_clk = new_freq / 2.0

    result = []
    for name, cyc in timings.items():
        ns_old = cyc / base_clk * 1000.0
        if cyc == 0:
            cyc_new = 0
        else:
            exact = ns_old * new_clk / 1000.0
            if mode == "nearest":
                lower = math.floor(exact)
                upper = math.ceil(exact)
                candidates = [c for c in (lower, upper) if c >= 1] or [1]
                cyc_new = min(candidates, key=lambda c: abs((c / new_clk * 1000.0) - ns_old))
            elif name == "REFI":
                # больше = лучше -> "не хуже" означает не увеличивать интервал -> округляем вниз
                cyc_new = math.floor(exact)
                if cyc_new < 1:
                    cyc_new = 1
            else:
                # меньше = лучше -> "не хуже" означает не уменьшать задержку -> округляем вверх
                cyc_new = math.ceil(exact)
                if cyc_new < 1:
                    cyc_new = 1
        ns_new = cyc_new / new_clk * 1000.0
        result.append((name, cyc, ns_old, cyc_new, ns_new))
    return result


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("720x560")
        self.resizable(True, True)

        self.report_path = tk.StringVar()
        self.base_freq_var = tk.StringVar(value="")
        self.new_freq_var = tk.StringVar(value="6400")
        self.mode_var = tk.StringVar(value="safe")
        self.rows = []
        self.timings = {}      # редактируемые исходные тайминги {name: cycles}
        self.new_timings = {}  # редактируемые новые тайминги {name: cycles}
        self.order = list(TIMING_NAMES)        # порядок отображения
        self.base_freq = None
        self.new_freq = None
        self._edit_entry = None
        self._edit_save_fn = None
        self._edit_row_iid = None
        self._edit_col = None
        self._last_size = None

        self._build_menu()
        self._build_widgets()
        self._apply_language()
        self.new_manual()
        self.update_idletasks()
        self._last_size = (self.winfo_width(), self.winfo_height())

    # --- локализация UI ---------------------------------------------------

    def _build_menu(self):
        self.menubar = tk.Menu(self)

        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(command=self.new_manual)
        self.file_menu.add_command(command=self.browse_file)
        self.file_menu.add_command(command=self.browse_csv)
        self.file_menu.add_command(command=self.export_csv)
        self.file_menu.add_separator()
        self.file_menu.add_command(command=self.destroy)
        self.menubar.add_cascade(menu=self.file_menu)

        self.lang_menu = tk.Menu(self.menubar, tearoff=0)
        self.lang_menu.add_command(command=lambda: self.set_language("ru"))
        self.lang_menu.add_command(command=lambda: self.set_language("en"))
        self.menubar.add_cascade(menu=self.lang_menu)

        self.config(menu=self.menubar)

    def _build_widgets(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        self.top_frame = top

        self.label_report = ttk.Label(top)
        self.label_report.grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.report_path, width=55).grid(row=0, column=1, padx=5)
        self.btn_browse = ttk.Button(top, command=self.browse_file)
        self.btn_browse.grid(row=0, column=2)

        self.label_base_freq = ttk.Label(top)
        self.label_base_freq.grid(row=1, column=0, sticky="w", pady=(8, 0))
        base_freq_entry = ttk.Entry(top, textvariable=self.base_freq_var, width=15)
        base_freq_entry.grid(row=1, column=1, sticky="w", pady=(8, 0))
        base_freq_entry.bind("<FocusOut>", lambda e: self._refresh_ns_old_column())
        base_freq_entry.bind("<Return>", lambda e: self._refresh_ns_old_column())

        self.label_new_freq = ttk.Label(top)
        self.label_new_freq.grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(top, textvariable=self.new_freq_var, width=15).grid(row=2, column=1, sticky="w", pady=(8, 0))

        self.label_round_mode = ttk.Label(top)
        self.label_round_mode.grid(row=3, column=0, sticky="w", pady=(8, 0))
        mode_frame = ttk.Frame(top)
        mode_frame.grid(row=3, column=1, columnspan=2, sticky="w", pady=(8, 0))
        self.radio_safe = ttk.Radiobutton(mode_frame, variable=self.mode_var, value="safe")
        self.radio_safe.pack(side="left")
        self.radio_nearest = ttk.Radiobutton(mode_frame, variable=self.mode_var, value="nearest")
        self.radio_nearest.pack(side="left", padx=(10, 0))

        self.btn_calc = ttk.Button(top, command=self.calculate)
        self.btn_calc.grid(row=4, column=1, sticky="w", pady=10)

        columns = ("timing", "val_old", "ns_old", "val_new", "ns_new")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.column(col, width=130, anchor="center")
        self.tree.column("timing", anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Configure>", self._on_tree_configure)
        self.bind("<Configure>", self._on_tree_configure)

        self.hint = ttk.Label(self, foreground="gray", wraplength=700, justify="left")
        self.hint.pack(fill="x", padx=10)

        self.status = ttk.Label(self, text="", foreground="gray")
        self.status.pack(fill="x", padx=10, pady=(0, 8))

    def set_language(self, lang):
        global CURRENT_LANG
        if lang == CURRENT_LANG:
            return
        CURRENT_LANG = lang
        self._apply_language()
        self._refresh_headers_only()

    def _apply_language(self):
        self.title(tr("app_title"))

        self.menubar.entryconfig(0, label=tr("menu_file"))
        self.menubar.entryconfig(1, label=tr("menu_lang"))
        self.file_menu.entryconfig(0, label=tr("menu_new"))
        self.file_menu.entryconfig(1, label=tr("menu_open_report"))
        self.file_menu.entryconfig(2, label=tr("menu_open_csv"))
        self.file_menu.entryconfig(3, label=tr("menu_export_csv"))
        self.file_menu.entryconfig(5, label=tr("menu_exit"))
        self.lang_menu.entryconfig(0, label=tr("lang_ru"))
        self.lang_menu.entryconfig(1, label=tr("lang_en"))

        self.label_report.config(text=tr("label_report"))
        self.btn_browse.config(text=tr("btn_browse"))
        self.label_base_freq.config(text=tr("label_base_freq"))
        self.label_new_freq.config(text=tr("label_new_freq"))
        self.label_round_mode.config(text=tr("label_round_mode"))
        self.radio_safe.config(text=tr("mode_safe"))
        self.radio_nearest.config(text=tr("mode_nearest"))
        self.btn_calc.config(text=tr("btn_calc"))
        self.hint.config(text=tr("hint"))
        self.status.config(text=tr("status_changed_language"))

    def _refresh_headers_only(self):
        """Обновляет заголовки таблицы и текущий статус под новый язык,
        не трогая уже введённые данные."""
        base_freq = self._get_base_freq()
        new_freq = self.new_freq or self._get_new_freq()

        self.tree.heading("timing", text=tr("col_timing"))
        self.tree.heading("val_old", text=tr("col_val_at", f=int(base_freq)) if base_freq else tr("col_val_old"))
        self.tree.heading("ns_old", text=tr("col_ns_at", f=int(base_freq)) if base_freq else tr("col_ns_old"))
        self.tree.heading("val_new", text=tr("col_val_at", f=int(new_freq)) if new_freq else tr("col_val_new"))
        self.tree.heading("ns_new", text=tr("col_ns_at", f=int(new_freq)) if new_freq else tr("col_ns_new"))

    # --- работа с данными ---------------------------------------------------

    def browse_file(self):
        path = filedialog.askopenfilename(
            title=tr("dlg_choose_report"),
            filetypes=[(tr("filetype_html"), "*.html;*.htm"), (tr("filetype_all"), "*.*")],
        )
        if not path:
            return
        self.report_path.set(path)
        try:
            base_freq, timings = parse_zentimings(Path(path))
        except Exception as e:
            messagebox.showerror(tr("err_title"), tr("err_read_report", e=e))
            return

        self.base_freq_var.set(str(int(base_freq)))
        self.timings = dict(timings)
        self.new_timings = {}
        self.order = list(TIMING_NAMES)
        self.rows = []
        self._populate_original()
        self.status.config(text=tr("status_imported_report", n=len(self.timings), f=int(base_freq)))

    def browse_csv(self):
        path = filedialog.askopenfilename(
            title=tr("dlg_choose_csv"),
            filetypes=[(tr("filetype_csv"), "*.csv"), (tr("filetype_all"), "*.*")],
        )
        if not path:
            return
        try:
            base_freq, new_freq, timings, new_timings = parse_exported_csv(Path(path))
        except Exception as e:
            messagebox.showerror(tr("err_title"), tr("err_read_csv", e=e))
            return

        if not timings:
            messagebox.showerror(tr("err_title"), tr("err_csv_no_timings"))
            return

        self.report_path.set(path)
        self.base_freq_var.set(str(int(base_freq)) if base_freq else "")
        self.new_freq_var.set(str(int(new_freq)) if new_freq else self.new_freq_var.get())
        self.timings = timings
        self.new_timings = new_timings
        self.order = list(TIMING_NAMES)
        self.base_freq = base_freq
        self.new_freq = new_freq
        self.rows = []

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tree.heading("val_old", text=tr("col_val_at", f=int(base_freq)) if base_freq else tr("col_val_old"))
        self.tree.heading("ns_old", text=tr("col_ns_at", f=int(base_freq)) if base_freq else tr("col_ns_old"))
        self.tree.heading("val_new", text=tr("col_val_at", f=int(new_freq)) if new_freq else tr("col_val_new"))
        self.tree.heading("ns_new", text=tr("col_ns_at", f=int(new_freq)) if new_freq else tr("col_ns_new"))

        base_clk = (base_freq / 2.0) if base_freq else None
        new_clk = (new_freq / 2.0) if new_freq else None
        for name in self.order:
            cyc = timings.get(name)
            cyc_new = new_timings.get(name)
            ns_old = f"{(cyc / base_clk * 1000.0):.3f}" if (cyc is not None and base_clk) else ""
            ns_new = f"{(cyc_new / new_clk * 1000.0):.3f}" if (cyc_new is not None and new_clk) else ""
            self.tree.insert("", "end", iid=name, values=(
                name,
                cyc if cyc is not None else "",
                ns_old,
                cyc_new if cyc_new is not None else "",
                ns_new,
            ))

        self.status.config(text=tr("status_imported_csv", n=len(timings)))

    def new_manual(self):
        """Начать с чистого листа — фиксированный список таймингов ZenTimings, значения пустые."""
        self.report_path.set("")
        self.base_freq_var.set("")
        self.timings = {}
        self.new_timings = {}
        self.order = list(TIMING_NAMES)
        self.rows = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree.heading("timing", text=tr("col_timing"))
        self.tree.heading("val_old", text=tr("col_val_old"))
        self.tree.heading("ns_old", text=tr("col_ns_old"))
        self.tree.heading("val_new", text=tr("col_val_new"))
        self.tree.heading("ns_new", text=tr("col_ns_new"))
        for name in self.order:
            self.tree.insert("", "end", iid=name, values=(name, "", "", "", ""))
        self.status.config(text=tr("status_empty"))

    def _get_base_freq(self):
        try:
            return float(self.base_freq_var.get().strip())
        except (ValueError, AttributeError):
            return None

    def _get_new_freq(self):
        try:
            return float(self.new_freq_var.get().strip())
        except (ValueError, AttributeError):
            return None

    def _refresh_ns_old_column(self):
        base_freq = self._get_base_freq()
        base_clk = base_freq / 2.0 if base_freq else None
        for name in self.order:
            cyc = self.timings.get(name)
            if cyc is None or base_clk is None:
                continue
            ns_old = cyc / base_clk * 1000.0
            self.tree.set(name, "ns_old", f"{ns_old:.3f}")

    def _populate_original(self):
        """Заполняет таблицу исходными (редактируемыми) таймингами, до пересчёта."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        base_freq = self._get_base_freq()
        self.tree.heading("timing", text=tr("col_timing"))
        self.tree.heading("val_old", text=tr("col_val_at", f=int(base_freq)) if base_freq else tr("col_val_old"))
        self.tree.heading("ns_old", text=tr("col_ns_at", f=int(base_freq)) if base_freq else tr("col_ns_old"))
        self.tree.heading("val_new", text=tr("col_val_new"))
        self.tree.heading("ns_new", text=tr("col_ns_new"))
        base_clk = (base_freq / 2.0) if base_freq else None
        for name in self.order:
            cyc = self.timings.get(name)
            if cyc is None:
                self.tree.insert("", "end", iid=name, values=(name, "", "", "", ""))
                continue
            ns_old = (cyc / base_clk * 1000.0) if base_clk else 0.0
            self.tree.insert("", "end", iid=name, values=(name, cyc, f"{ns_old:.3f}" if base_clk else "", "", ""))

    def _on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        row_iid = self.tree.identify_row(event.y)
        if not row_iid:
            return
        # редактируемые столбцы: val_old(#2), ns_old(#3), val_new(#4), ns_new(#5)
        if col not in ("#2", "#3", "#4", "#5"):
            return

        col_map = {"#2": "val_old", "#3": "ns_old", "#4": "val_new", "#5": "ns_new"}
        col_key = col_map[col]

        x, y, w, h = self.tree.bbox(row_iid, col)
        current_value = self.tree.set(row_iid, col_key)

        if self._edit_entry is not None:
            self._edit_entry.destroy()

        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, current_value)
        entry.focus()
        self._edit_entry = entry
        self._edit_row_iid = row_iid
        self._edit_col = col

        def save_edit(_evt=None):
            new_val = entry.get().strip().replace(",", ".")
            entry.destroy()
            self._edit_entry = None
            self._edit_save_fn = None
            if new_val == "":
                return

            if col_key in ("val_old", "val_new"):
                is_old = col_key == "val_old"
                freq = self._get_base_freq() if is_old else self._get_new_freq()
                if freq is None:
                    messagebox.showerror(tr("err_title"), tr("err_no_freq_first", which=tr("which_base" if is_old else "which_target")))
                    return
                if not re.fullmatch(r"-?\d+", new_val):
                    messagebox.showerror(tr("err_title"), tr("err_int_expected"))
                    return
                cyc = int(new_val)
                clk = freq / 2.0
                ns = cyc / clk * 1000.0
                store = self.timings if is_old else self.new_timings
                store[row_iid] = cyc
                self.tree.set(row_iid, col_key, cyc)
                self.tree.set(row_iid, "ns_old" if is_old else "ns_new", f"{ns:.3f}")
                return

            # col_key in ("ns_old", "ns_new") — вводим желаемое время, подбираем ближайший целый такт
            is_old = col_key == "ns_old"
            freq = self._get_base_freq() if is_old else self._get_new_freq()
            if freq is None:
                messagebox.showerror(tr("err_title"), tr("err_no_freq_first", which=tr("which_base" if is_old else "which_target")))
                return
            try:
                ns_target = float(new_val)
            except ValueError:
                messagebox.showerror(tr("err_title"), tr("err_ns_expected"))
                return
            clk = freq / 2.0
            exact_cyc = ns_target * clk / 1000.0
            lower = math.floor(exact_cyc)
            upper = math.ceil(exact_cyc)
            candidates = {c for c in (lower, upper) if c >= 0}
            if not candidates:
                candidates = {0}
            best_cyc = min(candidates, key=lambda c: abs((c / clk * 1000.0) - ns_target))
            best_ns = best_cyc / clk * 1000.0

            store = self.timings if is_old else self.new_timings
            store[row_iid] = best_cyc
            self.tree.set(row_iid, "val_old" if is_old else "val_new", best_cyc)
            self.tree.set(row_iid, col_key, f"{best_ns:.3f}")
            self.status.config(
                text=tr("status_nearest", name=row_iid, target=f"{ns_target:.3f}", best=f"{best_ns:.3f}", cyc=best_cyc)
            )

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        self._edit_save_fn = save_edit

    def _on_tree_configure(self, event=None):
        """При изменении размера окна/таблицы: если поле редактирования открыто —
        сдвигает его вместе со строкой, сохраняя введённый текст. Если поле
        пустое (пользователь ничего не ввёл), закрывает его без сохранения.
        Срабатывает только на реальное изменение размера окна, а не на любые
        служебные Configure-события (иначе поле закрывалось бы сразу после
        открытия, не давая ничего ввести)."""
        size = (self.winfo_width(), self.winfo_height())
        if size == self._last_size:
            return
        self._last_size = size

        entry = self._edit_entry
        if entry is None:
            return
        try:
            if not entry.winfo_exists():
                self._edit_entry = None
                self._edit_save_fn = None
                return
        except Exception:
            self._edit_entry = None
            self._edit_save_fn = None
            return

        if entry.get().strip() == "":
            entry.destroy()
            self._edit_entry = None
            self._edit_save_fn = None
            return

        bbox = self.tree.bbox(self._edit_row_iid, self._edit_col)
        if not bbox:
            # строка временно не видна (например, окно свёрнуто) — оставляем поле как есть
            return
        x, y, w, h = bbox
        entry.place(x=x, y=y, width=w, height=h)

    def calculate(self):
        active = {name: cyc for name, cyc in self.timings.items() if cyc is not None}
        if not active:
            messagebox.showerror(tr("err_title"), tr("err_no_active_timings"))
            return

        base_freq = self._get_base_freq()
        if base_freq is None:
            messagebox.showerror(tr("err_title"), tr("err_base_freq_number"))
            return

        try:
            new_freq = float(self.new_freq_var.get().strip())
        except ValueError:
            messagebox.showerror(tr("err_title"), tr("err_new_freq_number"))
            return

        self.base_freq = base_freq
        self.new_freq = new_freq
        self.rows = convert_timings(base_freq, new_freq, active, mode=self.mode_var.get())
        self.new_timings = {name: cyc_new for name, _, _, cyc_new, _ in self.rows}

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tree.heading("val_old", text=tr("col_val_at", f=int(base_freq)))
        self.tree.heading("ns_old", text=tr("col_ns_at", f=int(base_freq)))
        self.tree.heading("val_new", text=tr("col_val_at", f=int(new_freq)))
        self.tree.heading("ns_new", text=tr("col_ns_at", f=int(new_freq)))

        rows_by_name = {r[0]: r for r in self.rows}
        for name in self.order:
            if name in rows_by_name:
                _, cyc, ns_old, cyc_new, ns_new = rows_by_name[name]
                self.tree.insert("", "end", iid=name, values=(name, cyc, f"{ns_old:.3f}", cyc_new, f"{ns_new:.3f}"))
            else:
                self.tree.insert("", "end", iid=name, values=(name, "", "", "", ""))

        self.status.config(text=tr("status_done", n=len(self.rows)))

    def export_csv(self):
        children = self.tree.get_children()
        if not children:
            messagebox.showwarning(tr("warn_title"), tr("warn_table_empty"))
            return

        base_freq = self.base_freq or self._get_base_freq() or 0
        new_freq = self.new_freq or 0
        default_name = f"timings_{int(base_freq)}_to_{int(new_freq)}.csv"
        out_path = filedialog.asksaveasfilename(
            title=tr("dlg_save_csv"),
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[(tr("filetype_csv"), "*.csv")],
        )
        if not out_path:
            return

        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                tr("col_timing"),
                tr("col_val_at", f=int(base_freq)) if base_freq else tr("col_val_old"),
                tr("col_ns_at", f=int(base_freq)) if base_freq else tr("col_ns_old"),
                tr("col_val_at", f=int(new_freq)) if new_freq else tr("col_val_new"),
                tr("col_ns_at", f=int(new_freq)) if new_freq else tr("col_ns_new"),
            ])
            for iid in children:
                writer.writerow(self.tree.item(iid, "values"))

        self.status.config(text=tr("status_saved", path=out_path))
        messagebox.showinfo(tr("done_title"), tr("exported_to", path=out_path))


if __name__ == "__main__":
    app = App()
    app.mainloop()