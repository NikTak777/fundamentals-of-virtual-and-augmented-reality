import base64
import heapq
import itertools
import json
import re
from collections import Counter
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


def read_matrix(path: str) -> list[list[int]]:
    """Читает квадратную матрицу целых чисел из TXT или CSV."""
    text = Path(path).read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError("Файл не содержит матрицу.")

    matrix = [
        [int(x) for x in re.split(r"[\s;,]+", line.strip())]
        for line in text.splitlines()
        if line.strip()
    ]

    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise ValueError("Нужна квадратная матрица: N строк по N чисел.")

    return matrix


def recursive_order(n):
    """
    Рекурсивный обход с M=N=2.

    Порядок частей:
    1. Верхняя левая.
    2. Верхняя правая.
    3. Нижняя левая.
    4. Нижняя правая.

    Возвращает координаты ячеек в порядке обхода.
    """

    def visit(r0, r1, c0, c1):
        if r0 >= r1 or c0 >= c1:
            return

        if r1 - r0 == 1 and c1 - c0 == 1:
            yield r0, c0
            return

        # При нечётном размере верхняя/левая часть больше.
        rm = (r0 + r1 + 1) // 2
        cm = (c0 + c1 + 1) // 2

        yield from visit(r0, rm, c0, cm)
        yield from visit(r0, rm, cm, c1)
        yield from visit(rm, r1, c0, cm)
        yield from visit(rm, r1, cm, c1)

    return list(visit(0, n, 0, n))


def rle_encode(data):
    """RLE: список пар [значение, число повторений]."""
    result = []

    for value in data:
        if result and result[-1][0] == value:
            result[-1][1] += 1
        else:
            result.append([value, 1])

    return result


def rle_decode(pairs):
    """Восстановление последовательности из RLE."""
    return [
        value
        for value, count in pairs
        for _ in range(count)
    ]


def huffman_encode(data):
    """Построение кодов Хаффмана и упаковка потока в байты."""
    frequencies = Counter(data)
    serial = itertools.count()

    # Уникальный номер предотвращает сравнение узлов
    # при одинаковых частотах.
    heap = [
        (count, next(serial), value)
        for value, count in sorted(frequencies.items())
    ]
    heapq.heapify(heap)

    while len(heap) > 1:
        fa, _, a = heapq.heappop(heap)
        fb, _, b = heapq.heappop(heap)

        heapq.heappush(
            heap,
            (fa + fb, next(serial), (a, b))
        )

    codes = {}
    stack = [(heap[0][2], "")] if heap else []

    while stack:
        node, prefix = stack.pop()

        if isinstance(node, int):
            # Для единственного уникального значения
            # используем непустой код.
            codes[node] = prefix or "0"
        else:
            stack.append((node[1], prefix + "1"))
            stack.append((node[0], prefix + "0"))

    packed = bytearray()
    buffer = 0
    used = 0
    bit_length = 0

    for value in data:
        for bit in codes[value]:
            buffer = (buffer << 1) | int(bit)
            used += 1
            bit_length += 1

            if used == 8:
                packed.append(buffer)
                buffer = 0
                used = 0

    if used:
        # Дополняем последний байт нулями справа.
        packed.append(buffer << (8 - used))

    return codes, bytes(packed), bit_length, frequencies


def huffman_decode(packed, bit_length, codes):
    """Декодирование с учётом точной длины полезного потока."""
    if not 0 <= bit_length <= len(packed) * 8:
        raise ValueError("Некорректная длина битового потока.")

    reverse = {
        code: value
        for value, code in codes.items()
    }

    result = []
    prefix = ""

    for i in range(bit_length):
        bit = (packed[i // 8] >> (7 - i % 8)) & 1
        prefix += str(bit)

        if prefix in reverse:
            result.append(reverse[prefix])
            prefix = ""

    if prefix:
        raise ValueError("Незавершённый код Хаффмана.")

    return result


def json_size(obj):
    """Размер компактного представления JSON в байтах UTF-8."""
    text = json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":")
    )
    return len(text.encode("utf-8"))


def process(matrix):
    """Обход, два независимых метода сжатия и проверка."""
    n = len(matrix)
    order = recursive_order(n)
    data = [matrix[r][c] for r, c in order]

    pairs = rle_encode(data)

    codes, packed, bit_length, frequencies = huffman_encode(data)

    decoded_rle = rle_decode(pairs)
    decoded_huffman = huffman_decode(
        packed, bit_length, codes
    )

    restored = [[0] * n for _ in range(n)]

    for (r, c), value in zip(order, decoded_huffman):
        restored[r][c] = value

    if (
        decoded_rle != data
        or decoded_huffman != data
        or restored != matrix
    ):
        raise RuntimeError("Проверка восстановления не пройдена.")

    rle_record = {
        "shape": [n, n],
        "pairs": pairs,
    }

    huffman_record = {
        "shape": [n, n],
        "codes": [
            [value, codes[value]]
            for value in sorted(codes)
        ],
        "bit_length": bit_length,
        "data_base64": base64.b64encode(packed).decode("ascii"),
    }

    return {
        "variant": 8,
        "traversal": "recursive_2x2_TL_TR_BL_BR_ceil_split",
        "source": matrix,
        "sequence": data,
        "rle": rle_record,
        "huffman": huffman_record,
        "frequencies": [
            [value, frequencies[value]]
            for value in sorted(frequencies)
        ],
        "restored": restored,
        "verification": "OK",
        "statistics": {
            "elements": len(data),
            "runs": len(pairs),
            "source_json_bytes": json_size(matrix),
            "rle_json_bytes": json_size(rle_record),
            "huffman_json_bytes": json_size(huffman_record),
            "huffman_payload_bits": bit_length,
            "huffman_payload_bytes": len(packed),
        },
    }


def matrix_text(matrix):
    """Выравнивание столбцов для отображения."""
    width = max(
        len(str(value))
        for row in matrix
        for value in row
    )

    return "\n".join(
        " ".join(f"{value:>{width}}" for value in row)
        for row in matrix
    )


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(
            "ЛР №2 — вариант 8 — рекурсивный обход и сжатие"
        )
        self.geometry("1050x730")

        self.result = None

        bar = ttk.Frame(self, padding=10)
        bar.pack(fill="x")

        ttk.Button(
            bar,
            text="Открыть матрицу",
            command=self.open_file,
        ).pack(side="left")

        ttk.Button(
            bar,
            text="Сохранить результат",
            command=self.save,
        ).pack(side="left", padx=10)

        self.status = tk.StringVar(
            value="Откройте TXT, CSV или JSON с квадратной матрицей."
        )

        ttk.Label(
            self,
            textvariable=self.status,
            padding=10,
        ).pack(fill="x")

        notebook = ttk.Notebook(self)
        notebook.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10),
        )

        self.views = {}

        for name in (
            "Исходная матрица",
            "Обход",
            "RLE",
            "Хаффман",
            "Проверка и размеры",
        ):
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=name)

            view = ScrolledText(
                frame,
                wrap="word",
                font=("Consolas", 11),
            )
            view.pack(fill="both", expand=True)
            view.configure(state="disabled")

            self.views[name] = view

    def show(self, name, text):
        view = self.views[name]
        view.configure(state="normal")
        view.delete("1.0", "end")

        if len(text) > 100000:
            text = (
                text[:100000]
                + "\n… Предпросмотр сокращён. "
                "В файл сохраняется весь результат."
            )

        view.insert("1.0", text)
        view.configure(state="disabled")

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Матрицы", "*.txt *.csv *.json"),
                ("Все файлы", "*.*"),
            ]
        )

        if not path:
            return

        try:
            result = process(read_matrix(path))
            self.result = result
            self.display()

            n = len(result["source"])

            self.status.set(
                f"{Path(path).name} | "
                f"{n} × {n} | Восстановление: OK"
            )

        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Ошибка", str(exc))

    def display(self):
        r = self.result

        self.show(
            "Исходная матрица",
            matrix_text(r["source"]),
        )

        n = len(r["source"])
        steps = [[0] * n for _ in range(n)]

        for i, (row, col) in enumerate(recursive_order(n), 1):
            steps[row][col] = i

        self.show(
            "Обход",
            "M=N=2. Порядок частей: ВЛ → ВП → НЛ → НП.\n\n"
            + "Номера шагов:\n"
            + matrix_text(steps)
            + "\n\nОдномерный массив:\n"
            + str(r["sequence"]),
        )

        self.show(
            "RLE",
            "Пары [значение, число повторений]:\n\n"
            + str(r["rle"]["pairs"]),
        )

        h = r["huffman"]
        frequencies = dict(r["frequencies"])

        table = "Значение\tЧастота\tКод\n"

        table += "\n".join(
            f"{value}\t{frequencies[value]}\t{code}"
            for value, code in h["codes"]
        )

        packed = base64.b64decode(h["data_base64"])

        bits = "".join(
            f"{byte:08b}" for byte in packed
        )[:h["bit_length"]]

        self.show(
            "Хаффман",
            table
            + "\n\nБитовый поток:\n"
            + bits
            + "\n\nУпакованные байты (HEX):\n"
            + packed.hex(" ")
            + "\n\nНулевые биты дополнения в конце байта "
            "не входят в длину потока.",
        )

        s = r["statistics"]
        original = s["source_json_bytes"]

        lines = [
            "RLE → исходный одномерный массив: OK",
            "Хаффман → исходный одномерный массив: OK",
            "Обратный обход → исходная матрица: OK",
            "",
            f"Элементов: {s['elements']}; серий RLE: {s['runs']}",
            f"Исходная матрица в компактном JSON: {original} байт",
        ]

        for label, key in (
            ("RLE", "rle_json_bytes"),
            ("Хаффман", "huffman_json_bytes"),
        ):
            size = s[key]

            lines.append(
                f"{label}, JSON с метаданными: {size} байт; "
                f"K=исходный/сжатый={original / size:.3f}; "
                f"экономия={(1 - size / original) * 100:.2f}%"
            )

        lines.extend([
            f"Полезный поток Хаффмана: "
            f"{s['huffman_payload_bits']} бит, "
            f"{s['huffman_payload_bytes']} байт с дополнением.",
            "Размер JSON Хаффмана включает таблицу кодов и Base64.",
            "Отрицательная экономия означает увеличение объёма.",
            "Общий сохраняемый файл — отчёт с обоими методами "
            "и исходными данными.",
            "\nВосстановленная матрица:\n"
            + matrix_text(r["restored"]),
        ])

        self.show("Проверка и размеры", "\n".join(lines))

    def save(self):
        if self.result is None:
            messagebox.showinfo(
                "Сохранение",
                "Сначала откройте файл с матрицей.",
            )
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="lab2_variant8_result.json",
            filetypes=[("Отчёт JSON", "*.json")],
        )

        if not path:
            return

        try:
            Path(path).write_text(
                json.dumps(
                    self.result,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            messagebox.showinfo(
                "Готово",
                f"Результат сохранён:\n{path}",
            )

        except OSError as exc:
            messagebox.showerror(
                "Ошибка сохранения",
                str(exc),
            )


if __name__ == "__main__":
    App().mainloop()