import tkinter as tk
from decimal import Decimal, localcontext
from fractions import Fraction
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from core import (arithmetic_decode, arithmetic_encode, bwt_decode, bwt_encode,
                  mtf_decode, mtf_encode)


DEFAULT_TEXT = (
    "Пух, который тем временем совсем размечтался о меде, очнулся и даже "
    "подскочил, и сказал, что мед гораздо приманочней, чем желуди. "
    "Пятачок был другого мнения, и они чуть было не поспорили об этом; "
    "но Пятачок вовремя сообразил, что если они будут класть в ловушку "
    "желуди, то желуди придется собирать ему, Пятачку, а если они положат "
    "туда мед, то его достанет Пух"
)
DEFAULT_BWT = "ЧАСВУКНЩОПВПААОРЛР"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Кодирование текста")
        self.geometry("1050x760")
        self.minsize(760, 560)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)
        self.inputs, self.outputs = {}, {}
        for name, value, action in (
            ("Арифметическое кодирование", DEFAULT_TEXT, self.calculate_arithmetic),
            ("BWT", DEFAULT_BWT, self.calculate_bwt),
            ("MTF", bwt_encode(DEFAULT_BWT)[0], self.calculate_mtf),
        ):
            frame = ttk.Frame(notebook, padding=10)
            notebook.add(frame, text=name)
            ttk.Label(frame, text="Исходный текст (пробелы и регистр учитываются):").pack(anchor="w")
            source = ScrolledText(frame, height=5, wrap="word", font=("Consolas", 11))
            source.pack(fill="x", pady=6)
            source.insert("1.0", value)
            ttk.Button(frame, text="Вычислить", command=lambda f=action: self.calculate(f)).pack(anchor="w")
            output = ScrolledText(frame, wrap="word", font=("Consolas", 11))
            output.pack(fill="both", expand=True, pady=(10, 0))
            output.configure(state="disabled")
            self.inputs[name], self.outputs[name] = source, output

    def read(self, name, limit):
        text = self.inputs[name].get("1.0", "end-1c")
        if not text:
            raise ValueError("Введите непустой текст.")
        if len(text) > limit:
            raise ValueError(f"Максимальная длина для этого режима: {limit} символов.")
        return text

    def show(self, name, text):
        output = self.outputs[name]
        output.configure(state="normal")
        output.delete("1.0", "end")
        output.insert("1.0", text)
        output.configure(state="disabled")

    def calculate(self, action):
        try:
            action()
        except ValueError as error:
            messagebox.showerror("Ошибка ввода", str(error), parent=self)

    def calculate_arithmetic(self):
        name = "Арифметическое кодирование"
        text = self.read(name, 1000)
        bits, low, high, model = arithmetic_encode(text)
        restored = arithmetic_decode(bits, model, len(text))
        code = Fraction(int(bits, 2), 1 << len(bits))
        with localcontext() as context:
            context.prec = len(bits) + 2
            decimal = str(Decimal(code.numerator) / Decimal(code.denominator))
        table = "\n".join(
            f"{char!r:6} {count:4}   {count}/{len(text)}   [{left}, {right})"
            for char, (count, left, right) in model.items()
        )
        original_bits = len(text.encode("utf-8")) * 8
        self.show(name,
            f"Символов: {len(text)}; различных: {len(model)}\n\n"
            f"Символ / Частота / Вероятность / Интервал\n{table}\n\n"
            f"Итоговый полуинтервал [L, H):\nL = {low}\nH = {high}\n\n"
            f"Код в двоичной записи:\n0.{bits}\n\n"
            f"Точное десятичное значение кода:\n{decimal}\n\n"
            f"Код: {len(bits)} бит; исходный UTF-8: {original_bits} бит.\n"
            f"Отношение размера UTF-8 к размеру кода: {original_bits / len(bits):.2f}.\n"
            "Размер модели и длина сообщения в это сравнение не включены.\n"
            "Для декодирования нужны код, таблица частот и число символов.\n\n"
            f"Восстановленный текст:\n{restored}\n\nСовпадение: {restored == text}"
        )

    def calculate_bwt(self):
        text = self.read("BWT", 150)
        last, index, rotations, ordered = bwt_encode(text)
        restored = bwt_decode(last, index)
        matrix = "\n".join(
            f"{i:3}. {row!r}{'  ← исходная строка' if i == index else ''}"
            for i, row in enumerate(ordered, 1)
        )
        self.show("BWT",
            "Циклические сдвиги:\n" + "\n".join(repr(row) for row in rotations)
            + f"\n\nПосле сортировки:\n{matrix}\n\nПоследний столбец: {last}\n"
            f"Номер исходной строки (с 1): {index}\n"
            f"Восстановленная строка: {restored}\nСовпадение: {restored == text}\n\n"
            "Результат передан на вкладку MTF."
        )
        self.inputs["MTF"].delete("1.0", "end")
        self.inputs["MTF"].insert("1.0", last)
        self.calculate_mtf()

    def calculate_mtf(self):
        text = self.read("MTF", 1000)
        codes, alphabet, steps = mtf_encode(text)
        restored = mtf_decode(codes, alphabet)
        table = "\n".join(
            f"{i:3}. {char!r:6} {current!r:25} {index}"
            for i, (char, current, index) in enumerate(steps, 1)
        )
        self.show("MTF",
            f"Начальный алфавит: {''.join(alphabet)!r}\n"
            "Алфавит отсортирован по Unicode; индексы начинаются с 0.\n\n"
            f"Шаг  Символ  Алфавит до перемещения     Индекс\n{table}\n\n"
            f"Последовательность MTF:\n{' '.join(map(str, codes))}\n\n"
            f"Восстановленная строка: {restored}\nСовпадение: {restored == text}"
        )