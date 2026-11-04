import base64
import heapq
import itertools
import json
import re
from collections import Counter
from pathlib import Path


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
    if any(type(x) is not int for row in matrix for x in row):
        raise ValueError("Элементы должны быть целыми числами.")

    return matrix


def recursive_order(size: int) -> list[tuple[int, int]]:
    """Возвращает координаты ячеек в порядке рекурсивного обхода M=N=2."""

    def visit_block(row_start: int, row_end: int, col_start: int, col_end: int):
        height = row_end - row_start
        width = col_end - col_start

        if height <= 0 or width <= 0:
            return

        if height == 1 and width == 1:
            yield row_start, col_start
            return

        row_mid = row_start + (height + 1) // 2
        col_mid = col_start + (width + 1) // 2

        yield from visit_block(row_start, row_mid, col_start, col_mid)  # Верхний левый
        yield from visit_block(row_start, row_mid, col_mid, col_end)    # Верхний правый
        yield from visit_block(row_mid, row_end, col_start, col_mid)    # Нижний левый
        yield from visit_block(row_mid, row_end, col_mid, col_end)      # Нижний правый

    return list(visit_block(0, size, 0, size))


def rle_encode(data):
    """RLE: список пар [значение, число повторений]."""
    result = []
    for value in data:
        if result and result[-1][0] == value:
            result[-1][1] += 1
        else:
            result.append([value, 1])
    return result


def huffman_encode(data):
    """Построение кодов Хаффмана и упаковка потока в байты."""
    frequencies = Counter(data)
    serial = itertools.count()
    heap = [(count, next(serial), value)
            for value, count in sorted(frequencies.items())]
    heapq.heapify(heap)
    while len(heap) > 1:
        fa, _, a = heapq.heappop(heap)
        fb, _, b = heapq.heappop(heap)
        heapq.heappush(heap, (fa + fb, next(serial), (a, b)))

    codes = {}
    stack = [(heap[0][2], "")] if heap else []
    while stack:
        node, prefix = stack.pop()
        if isinstance(node, int):
            codes[node] = prefix or "0"
        else:
            stack.append((node[1], prefix + "1"))
            stack.append((node[0], prefix + "0"))

    packed = bytearray()
    buffer = used = bit_length = 0
    for value in data:
        for bit in codes[value]:
            buffer = (buffer << 1) | int(bit)
            used += 1
            bit_length += 1
            if used == 8:
                packed.append(buffer)
                buffer = used = 0
    if used:
        packed.append(buffer << (8 - used))
    return codes, bytes(packed), bit_length, frequencies


def json_size(obj):
    """Размер компактного представления JSON в байтах UTF-8."""
    return len(json.dumps(obj, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8"))


def process(matrix):
    """Обходит матрицу, сжимает последовательность и собирает отчёт."""
    size = len(matrix)
    coordinates = recursive_order(size)
    sequence = [matrix[row][col] for row, col in coordinates]

    rle_pairs = rle_encode(sequence)
    huffman_codes, huffman_bytes, huffman_bit_count, frequencies = (
        huffman_encode(sequence)
    )

    rle_result = {"shape": [size, size], "pairs": rle_pairs}
    huffman_result = {
        "shape": [size, size],
        "codes": [[value, huffman_codes[value]] for value in sorted(huffman_codes)],
        "bit_length": huffman_bit_count,
        "data_base64": base64.b64encode(huffman_bytes).decode("ascii"),
    }
    return {
        "variant": 8,
        "traversal": "recursive_2x2_TL_TR_BL_BR_ceil_split",
        "source": matrix,
        "sequence": sequence,
        "rle": rle_result,
        "huffman": huffman_result,
        "frequencies": [[value, frequencies[value]] for value in sorted(frequencies)],
        "statistics": {
            "elements": len(sequence),
            "runs": len(rle_pairs),
            "source_json_bytes": json_size(matrix),
            "rle_json_bytes": json_size(rle_result),
            "huffman_json_bytes": json_size(huffman_result),
            "huffman_payload_bits": huffman_bit_count,
            "huffman_payload_bytes": len(huffman_bytes),
        },
    }
