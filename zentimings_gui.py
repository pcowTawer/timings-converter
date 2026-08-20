#!/usr/bin/env python3
"""
ZenTimings Frequency Converter — небольшое GUI-приложение.

Открывает html-отчёт ZenTimings, пересчитывает тайминги на указанную
частоту (сохраняя задержку в нс равной или больше исходной) и
показывает результат в таблице. Экспорт в CSV — через меню "Файл".

Сборка в .exe (на Windows, где будет запускаться сам exe):
    pip install pyinstaller beautifulsoup4
    pyinstaller --onefile --windowed --name ZenTimingsConverter zentimings_gui.py
Готовый файл появится в папке dist/ZenTimingsConverter.exe
"""

import re
import sys
import csv
import math
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
    except subprocess.CalledProcessError:
        pass
    from bs4 import BeautifulSoup


TIMING_NAMES = [
    "RFCsb", "CL", "RCDWR", "RCDRD", "RP", "RAS", "RC", "RRDS", "RRDL", "FAW",
    "WTRS", "WTRL", "WR", "RDRDSCL", "WRWRSCL", "CWL", "RTP", "RDWR", "WRRD",
    "RDRDSC", "RDRDSD", "RDRDDD", "WRWRSC", "WRWRSD", "WRWRDD", "TRCPAGE", "CKE",
    "STAG", "STAGsb", "MOD", "MODPDA", "MRD", "MRDPDA", "RFC", "RFC2", "REFI",
    "XP", "PHYWRD", "PHYWRL", "PHYRDL", "WRPRE", "RDPRE", "RDPOST", "WRPOST", "FGR",
]


def parse_zentimings(html_path: Path):
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    table = soup.find("table", id="timingsTable")
    if table is None:
        raise ValueError("Не найдена таблица Memory Timings (id='timingsTable') в отчёте.")

    rows = table.find_all("tr")
    timings = {}
    base_freq = None

    for tr in rows[1:]:
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

        if name == "Ratio":
            continue

        if re.fullmatch(r"-?\d+", val0):
            timings[name] = int(val0)

    if base_freq is None:
        raise ValueError("Не удалось найти строку 'Frequency' в таблице Memory Timings.")

    return base_freq, timings


def convert_timings(base_freq: float, new_freq: float, timings: dict):
    base_clk = base_freq / 2.0
    new_clk = new_freq / 2.0

    result = []
    for name, cyc in timings.items():
        ns_old = cyc / base_clk * 1000.0
        if cyc == 0:
            cyc_new = 0
        else:
            cyc_new = math.ceil(ns_old * new_clk / 1000.0)
            if cyc_new < 1:
                cyc_new = 1
        ns_new = cyc_new / new_clk * 1000.0
        result.append((name, cyc, ns_old, cyc_new, ns_new))
    return result


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZenTimings Frequency Converter")
        self.geometry("720x560")
        self.resizable(True, True)

        self.report_path = tk.StringVar()
        self.base_freq_var = tk.StringVar(value="")
        self.new_freq_var = tk.StringVar(value="6400")
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

        self._build_menu()
        self._build_widgets()
        self.new_manual()

    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Новый (ввести вручную)...", command=self.new_manual)
        file_menu.add_command(label="Открыть отчёт...", command=self.browse_file)
        file_menu.add_command(label="Экспорт в CSV...", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.destroy)
        menubar.add_cascade(label="Файл", menu=file_menu)
        self.config(menu=menubar)

    def _build_widgets(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Отчёт ZenTimings:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.report_path, width=55).grid(row=0, column=1, padx=5)
        ttk.Button(top, text="Обзор...", command=self.browse_file).grid(row=0, column=2)

        ttk.Label(top, text="Исходная частота (MT/s):").grid(row=1, column=0, sticky="w", pady=(8, 0))
        base_freq_entry = ttk.Entry(top, textvariable=self.base_freq_var, width=15)
        base_freq_entry.grid(row=1, column=1, sticky="w", pady=(8, 0))
        base_freq_entry.bind("<FocusOut>", lambda e: self._refresh_ns_old_column())
        base_freq_entry.bind("<Return>", lambda e: self._refresh_ns_old_column())

        ttk.Label(top, text="Целевая частота (MT/s):").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(top, textvariable=self.new_freq_var, width=15).grid(row=2, column=1, sticky="w", pady=(8, 0))

        ttk.Button(top, text="Пересчитать", command=self.calculate).grid(row=3, column=1, sticky="w", pady=10)

        columns = ("timing", "val_old", "ns_old", "val_new", "ns_new")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        headers = {
            "timing": "Тайминг",
            "val_old": "Значение (старая)",
            "ns_old": "нс (старая)",
            "val_new": "Значение (новая)",
            "ns_new": "нс (новая)",
        }
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=130, anchor="center")
        self.tree.column("timing", anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Configure>", self._on_tree_configure)
        self.bind("<Configure>", self._on_tree_configure)

        hint = ttk.Label(
            self,
            text="Двойной клик по «Значение» или «нс» — редактировать (при вводе нс подбирается ближайшее целое число тактов). Частоту можно менять выше.",
            foreground="gray",
        )
        hint.pack(fill="x", padx=10)

        self.status = ttk.Label(self, text="", foreground="gray")
        self.status.pack(fill="x", padx=10, pady=(0, 8))

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Выберите отчёт ZenTimings",
            filetypes=[("HTML files", "*.html;*.htm"), ("All files", "*.*")],
        )
        if not path:
            return
        self.report_path.set(path)
        try:
            base_freq, timings = parse_zentimings(Path(path))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать отчёт: {e}")
            return

        self.base_freq_var.set(str(int(base_freq)))
        self.timings = dict(timings)
        self.new_timings = {}
        self.order = list(TIMING_NAMES)
        self.rows = []
        self._populate_original()
        self.status.config(text=f"Импортировано таймингов: {len(self.timings)}. Частота из отчёта: {int(base_freq)} MT/s (можно менять).")

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
        self.tree.heading("val_old", text="Значение (старая)")
        self.tree.heading("ns_old", text="нс (старая)")
        self.tree.heading("val_new", text="Значение (новая)")
        self.tree.heading("ns_new", text="нс (новая)")
        for name in self.order:
            self.tree.insert("", "end", iid=name, values=(name, "", "", "", ""))
        self.status.config(text="Пустая таблица со стандартными таймингами ZenTimings. Введите частоту и значения.")

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
        base = int(base_freq) if base_freq else ""
        self.tree.heading("val_old", text=f"Значение @{base}" if base_freq else "Значение (старая)")
        self.tree.heading("ns_old", text=f"нс @{base}" if base_freq else "нс (старая)")
        self.tree.heading("val_new", text="Значение (новая)")
        self.tree.heading("ns_new", text="нс (новая)")
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
                    messagebox.showerror("Ошибка", "Сначала укажите " + ("исходную" if is_old else "целевую") + " частоту.")
                    return
                if not re.fullmatch(r"-?\d+", new_val):
                    messagebox.showerror("Ошибка", "Тайминг (такты) должен быть целым числом.")
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
                messagebox.showerror("Ошибка", "Сначала укажите " + ("исходную" if is_old else "целевую") + " частоту.")
                return
            try:
                ns_target = float(new_val)
            except ValueError:
                messagebox.showerror("Ошибка", "Время должно быть числом (нс).")
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
                text=f"{row_iid}: ближайшее время к {ns_target:.3f} нс — {best_ns:.3f} нс ({best_cyc} такт.)."
            )

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        self._edit_save_fn = save_edit

    def _on_tree_configure(self, event=None):
        """При изменении размера окна/таблицы: если поле редактирования открыто —
        сдвигает его вместе со строкой, сохраняя введённый текст. Если поле
        пустое (пользователь ничего не ввёл), закрывает его без сохранения."""
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
            messagebox.showerror("Ошибка", "Нет заполненных таймингов. Импортируйте отчёт или введите значения вручную.")
            return

        base_freq = self._get_base_freq()
        if base_freq is None:
            messagebox.showerror("Ошибка", "Укажите исходную частоту (MT/s), числом.")
            return

        try:
            new_freq = float(self.new_freq_var.get().strip())
        except ValueError:
            messagebox.showerror("Ошибка", "Целевая частота должна быть числом.")
            return

        self.base_freq = base_freq
        self.new_freq = new_freq
        self.rows = convert_timings(base_freq, new_freq, active)
        self.new_timings = {name: cyc_new for name, _, _, cyc_new, _ in self.rows}

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tree.heading("val_old", text=f"Значение @{int(base_freq)}")
        self.tree.heading("ns_old", text=f"нс @{int(base_freq)}")
        self.tree.heading("val_new", text=f"Значение @{int(new_freq)}")
        self.tree.heading("ns_new", text=f"нс @{int(new_freq)}")

        rows_by_name = {r[0]: r for r in self.rows}
        for name in self.order:
            if name in rows_by_name:
                _, cyc, ns_old, cyc_new, ns_new = rows_by_name[name]
                self.tree.insert("", "end", iid=name, values=(name, cyc, f"{ns_old:.3f}", cyc_new, f"{ns_new:.3f}"))
            else:
                self.tree.insert("", "end", iid=name, values=(name, "", "", "", ""))

        self.status.config(text=f"Готово. Строк: {len(self.rows)}.")

    def export_csv(self):
        children = self.tree.get_children()
        if not children:
            messagebox.showwarning("Внимание", "Таблица пуста.")
            return

        base_freq = self.base_freq or self._get_base_freq() or 0
        new_freq = self.new_freq or 0
        default_name = f"timings_{int(base_freq)}_to_{int(new_freq)}.csv"
        out_path = filedialog.asksaveasfilename(
            title="Сохранить как CSV",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv")],
        )
        if not out_path:
            return

        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                "Тайминг",
                f"Значение@{int(base_freq)}" if base_freq else "Значение (старая)",
                f"нс@{int(base_freq)}" if base_freq else "нс (старая)",
                f"Значение@{int(new_freq)}" if new_freq else "Значение (новая)",
                f"нс@{int(new_freq)}" if new_freq else "нс (новая)",
            ])
            for iid in children:
                writer.writerow(self.tree.item(iid, "values"))

        self.status.config(text=f"Сохранено: {out_path}")
        messagebox.showinfo("Готово", f"Экспортировано в:\n{out_path}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
