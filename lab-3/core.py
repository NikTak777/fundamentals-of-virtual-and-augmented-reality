from collections import Counter
from fractions import Fraction


def arithmetic_encode(text):
    if not text:
        raise ValueError("Введите непустой текст.")
    model, start = {}, Fraction(0)
    for char, count in sorted(Counter(text).items()):
        end = start + Fraction(count, len(text))
        model[char] = (count, start, end)
        start = end

    low, high = Fraction(0), Fraction(1)
    for char in text:
        _, left, right = model[char]
        width = high - low
        low, high = low + width * left, low + width * right

    # Ищем двоичную дробь, принадлежащую полуинтервалу [low, high).
    width = high - low
    size = max(1, width.denominator.bit_length() - width.numerator.bit_length())
    while True:
        scaled = low * (1 << size)
        number = -(-scaled.numerator // scaled.denominator)
        if Fraction(number, 1 << size) < high:
            return format(number, f"0{size}b"), low, high, model
        size += 1


def arithmetic_decode(bits, model, length):
    code = Fraction(int(bits, 2), 1 << len(bits))
    result = []
    for _ in range(length):
        for char, (_, left, right) in model.items():
            if left <= code < right:
                result.append(char)
                code = (code - left) / (right - left)
                break
        else:
            raise ValueError("Код не соответствует модели.")
    return "".join(result)


def bwt_encode(text):
    if not text:
        raise ValueError("Введите непустую строку.")
    rotations = [text[i:] + text[:i] for i in range(len(text))]
    ordered = sorted(rotations)
    return "".join(row[-1] for row in ordered), ordered.index(text) + 1, rotations, ordered


def bwt_decode(last, index):
    if not last or not 1 <= index <= len(last):
        raise ValueError("Некорректный номер строки BWT.")
    rows = [""] * len(last)
    for _ in last:
        rows = sorted(char + row for char, row in zip(last, rows))
    return rows[index - 1]


def mtf_encode(text):
    if not text:
        raise ValueError("Введите непустую строку.")
    alphabet = sorted(set(text))
    current, codes, steps = alphabet.copy(), [], []
    for char in text:
        index = current.index(char)
        steps.append((char, "".join(current), index))
        codes.append(index)
        current.insert(0, current.pop(index))
    return codes, alphabet, steps


def mtf_decode(codes, alphabet):
    current, result = list(alphabet), []
    for index in codes:
        if not 0 <= index < len(current):
            raise ValueError("Индекс MTF вне алфавита.")
        char = current.pop(index)
        result.append(char)
        current.insert(0, char)
    return "".join(result)