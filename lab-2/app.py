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
        self.status = tk.StringVar(value="Откройте TXT или CSV с квадратной матрицей.")
        ttk.Label(self, textvariable=self.status, padding=10).pack(fill="x")
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.views = {}
        for name in ("Исходная матрица", "Обход", "Метод RLE", "Метод Хаффмана", "Итоговая статистика"):
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=name)

            is_matrix_tab = name in ("Исходная матрица", "Обход")

            view = ScrolledText(
                frame,
                wrap="none" if is_matrix_tab else "word",
                font=("Consolas", 11),
            )

            if is_matrix_tab:
                horizontal_scrollbar = ttk.Scrollbar(
                    frame,
                    orient="horizontal",
                    command=view.xview,
                )
                view.configure(xscrollcommand=horizontal_scrollbar.set)
                horizontal_scrollbar.pack(side="bottom", fill="x")

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
            ("Матрицы", "*.txt *.csv"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            result = process(read_matrix(path))
            self.result = result
            self.display()
            n = len(result["source"])
            self.status.set(f"Файл: {Path(path).name} | Размер: {n} x {n}")
        except (OSError, ValueError) as exc:
            messagebox.showerror(
                title="Ошибка открытия файла",
                message="Неверный формат файла: " + str(exc)
            )

    def display(self):
        r = self.result
        self.show("Исходная матрица", matrix_text(r["source"]))
        n = len(r["source"])
        steps = [[0] * n for _ in range(n)]
        for i, (row, col) in enumerate(recursive_order(n), 1):
            steps[row][col] = i
        sequence = r["sequence"]
        values_per_line = n
        sequence_text = "\n".join(
            ", ".join(map(str, sequence[start:start + values_per_line]))
            for start in range(0, len(sequence), values_per_line)
        )
        self.show(
            name="Обход",
            text=(
                "Параметры обхода: M=N=2.\n\n"
                + "Номера шагов:\n" + matrix_text(steps)
                + "\n\nОдномерный массив:\n" + sequence_text
            )
        )
        self.show("Метод RLE", "Пары [значение, число повторений]:\n\n" + str(r["rle"]["pairs"]))
        h = r["huffman"]
        frequencies = dict(r["frequencies"])
        table = "Значение\tЧастота\tКод\n" + "\n".join(
            f"{value}\t{frequencies[value]}\t{code}" for value, code in h["codes"])
        packed = base64.b64decode(h["data_base64"])
        bits = "".join(f"{byte:08b}" for byte in packed)[:h["bit_length"]]
        grouped_bits = " ".join(
            bits[start:start + 8]
            for start in range(0, len(bits), 8)
        )
        self.show(
            name="Метод Хаффмана",
            text = table + "\n\nБитовый поток:\n" + grouped_bits
                  + "\n\nУпакованные байты (HEX):\n" + packed.hex(" ")
        )
        s = r["statistics"]
        original_bits = s["source_payload_bytes"] * 8
        rle_bits = s["rle_payload_bytes"] * 8
        huffman_bits = s["huffman_payload_bits"]
        lines = [
            f"Итоговая статистика:\n",
            f"Размер поля значения: {s['value_bytes']} байт.",
            f"Размер поля счётчика: {s['rle_count_bytes']} байт.",
            f"Исходный массив: {s['elements']} значений × "
            f"{s['value_bytes']} байт = {s['source_payload_bytes']} байт ({original_bits} бит).\n",
            f"Результаты метода RLE:",
            f"RLE: {s['runs']} пар × ({s['value_bytes']} + {s['rle_count_bytes']}) байт "
            f"= {s['rle_payload_bytes']} байт ({rle_bits} бит).\n",
            f"Результаты метода Хаффмана:",
            f"Полезных бит: {huffman_bits}, байт после упаковки: {s['huffman_payload_bytes']} ({s['huffman_payload_bytes'] * 8} бит)",
            "",
        ]
        for label, compressed_bits in (("Метод RLE", rle_bits), ("Метод Хаффмана", huffman_bits)):
            ratio = compressed_bits / original_bits
            lines.append(f"{label}: {ratio:.3f} от исходного размера, "
                         f"изменение {(ratio - 1) * 100:+.2f}%")
        self.show("Итоговая статистика", "\n".join(lines))

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
