import base64
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from core import process, read_matrix, recursive_order


def matrix_text(matrix):
    width = max(len(str(v)) for row in matrix for v in row)
    return "\n".join(" ".join(f"{v:>{width}}" for v in row) for row in matrix)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Приложение для рекурсивного обхода и сжатия двумерных массивов")
        self.geometry("1920x1080")
        self.result = None
        bar = ttk.Frame(self, padding=10)
        bar.pack(fill="x")
        ttk.Button(bar, text="Открыть матрицу", command=self.open_file).pack(side="left")
        ttk.Button(bar, text="Сохранить результат", command=self.save).pack(side="left", padx=10)
        self.status = tk.StringVar(value="Откройте TXT, CSV или JSON с квадратной матрицей.")
        ttk.Label(self, textvariable=self.status, padding=10).pack(fill="x")
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.views = {}
        for name in ("Исходная матрица", "Обход", "RLE", "Хаффман", "Размеры"):
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=name)
            view = ScrolledText(frame, wrap="word", font=("Consolas", 11))
            view.pack(fill="both", expand=True)
            view.configure(state="disabled")
            self.views[name] = view

    def show(self, name, text):
        view = self.views[name]
        view.configure(state="normal")
        view.delete("1.0", "end")
        if len(text) > 100000:
            text = text[:100000] + "\n… Предпросмотр сокращён. В файл сохраняется весь результат."
        view.insert("1.0", text)
        view.configure(state="disabled")

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Матрицы", "*.txt *.csv *.json"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            result = process(read_matrix(path))
            self.result = result
            self.display()
            n = len(result["source"])
            self.status.set(f"{Path(path).name} | {n} × {n}")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Ошибка", str(exc))

    def display(self):
        r = self.result
        self.show("Исходная матрица", matrix_text(r["source"]))
        n = len(r["source"])
        steps = [[0] * n for _ in range(n)]
        for i, (row, col) in enumerate(recursive_order(n), 1):
            steps[row][col] = i
        self.show("Обход", "M=N=2. Порядок частей: ВЛ → ВП → НЛ → НП.\n\n"
                  + "Номера шагов:\n" + matrix_text(steps)
                  + "\n\nОдномерный массив:\n" + str(r["sequence"]))
        self.show("RLE", "Пары [значение, число повторений]:\n\n" + str(r["rle"]["pairs"]))
        h = r["huffman"]
        frequencies = dict(r["frequencies"])
        table = "Значение\tЧастота\tКод\n" + "\n".join(
            f"{value}\t{frequencies[value]}\t{code}" for value, code in h["codes"])
        packed = base64.b64decode(h["data_base64"])
        bits = "".join(f"{byte:08b}" for byte in packed)[:h["bit_length"]]
        self.show("Хаффман", table + "\n\nБитовый поток:\n" + bits
                  + "\n\nУпакованные байты (HEX):\n" + packed.hex(" ")
                  + "\n\nНулевые биты дополнения в конце байта не входят в длину потока.")
        s = r["statistics"]
        original = s["source_json_bytes"]
        lines = [
            f"Элементов: {s['elements']}; серий RLE: {s['runs']}",
            f"Исходная матрица в компактном JSON: {original} байт",
        ]
        for label, key in (("RLE", "rle_json_bytes"), ("Хаффман", "huffman_json_bytes")):
            size = s[key]
            lines.append(f"{label}, JSON с метаданными: {size} байт; "
                         f"K=исходный/сжатый={original / size:.3f}; "
                         f"экономия={(1 - size / original) * 100:.2f}%")
        lines.extend([
            f"Полезный поток Хаффмана: {s['huffman_payload_bits']} бит, "
            f"{s['huffman_payload_bytes']} байт с дополнением.",
            "Размер JSON Хаффмана включает таблицу кодов и Base64.",
            "Отрицательная экономия означает увеличение объёма.",
            "Общий сохраняемый файл — отчёт с обоими методами и исходными данными.",
        ])
        self.show("Размеры", "\n".join(lines))

    def save(self):
        if self.result is None:
            messagebox.showinfo("Сохранение", "Сначала откройте файл с матрицей.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", initialfile="lab2_variant8_result.json",
            filetypes=[("Отчёт JSON", "*.json")])
        if path:
            try:
                Path(path).write_text(json.dumps(self.result, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
                messagebox.showinfo("Готово", f"Результат сохранён:\n{path}")
            except OSError as exc:
                messagebox.showerror("Ошибка сохранения", str(exc))


def main():
    App().mainloop()
