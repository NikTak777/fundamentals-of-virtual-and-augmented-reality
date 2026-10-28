from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk
import tkinter as tk
from tkinter import filedialog, ttk


def rgb_to_yiq(RGB: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Возвращает три двумерных массива Y, I и Q из массива RGB-пикселей."""
    R, G, B = np.asarray(RGB, dtype=np.float64).transpose(2, 0, 1)
    Y = 0.299 * R + 0.587 * G + 0.114 * B
    I = 0.596 * R - 0.275 * G - 0.321 * B
    Q = 0.212 * R - 0.523 * G + 0.311 * B
    return Y, I, Q


def yiq_to_rgb(Y: np.ndarray, I: np.ndarray, Q: np.ndarray) -> np.ndarray:
    """Возвращает массив RGB-пикселей для отображения каналов YIQ."""
    R = Y + 0.956 * I + 0.621 * Q
    G = Y - 0.272 * I - 0.647 * Q
    B = Y - 1.107 * I + 1.704 * Q
    return np.rint(np.clip(np.stack((R, G, B), axis=-1), 0, 255)).astype(np.uint8)


def channel_images(Y, I, Q):
    """Создаёт три изображения. Каждый канал YIQ показан отдельно через RGB."""
    zero = np.zeros_like(Y)
    return {
        'Y': Image.fromarray(yiq_to_rgb(Y, zero, zero)),
        'I': Image.fromarray(yiq_to_rgb(zero, I, zero)),
        'Q': Image.fromarray(yiq_to_rgb(zero, zero, Q)),
    }


def read_image(path) -> Image.Image:
    """Открывает изображение и возвращает его в режиме RGB без прозрачности."""
    with Image.open(path) as image:
        return image.convert('RGB')


def make_overview(original, channels):
    """Создаёт общую иллюстрацию с исходником и тремя каналами."""
    width, height, label_height = 960, 494, 46
    canvas = Image.new(
        mode='RGB',
        size=(width * 2, (height + label_height) * 2),
        color='white'
    )
    draw = ImageDraw.Draw(im=canvas)
    try:
        font = ImageFont.truetype(
            font='arial.ttf',
            size=22
        )
    except OSError:
        font = ImageFont.load_default(size=20)

    items = [
        ('Original RGB', original),
        ('Y (Y, 0, 0)', channels['Y']),
        ('I (0, I, 0)', channels['I']),
        ('Q (0, 0, Q)', channels['Q'])
    ]

    for index, (label, image) in enumerate(items):
        left = (index % 2) * width
        top = (index // 2) * (height + label_height)
        draw.text(
            xy=(left + 16, top + 10),
            text=label,
            fill='black',
            font=font
        )
        preview = image.copy()
        preview.thumbnail(
            size=(width - 20, height - 20),
            resample=Image.Resampling.LANCZOS
        )
        canvas.paste(
            im=preview,
            box=(left + (width - preview.width) // 2,
                top + label_height + (height - preview.height) // 2)
        )
    return canvas


def show_results(original, channels, output_dir):
    """Показывает исходник и три изображения каналов в одном окне."""
    root = tk.Tk()
    root.title('Результат преобразования RGB на каналы YIQ')
    for index in range(2):
        root.rowconfigure(index, weight=1, uniform='images')
        root.columnconfigure(index, weight=1, uniform='images')

    def add_preview(frame, image):
        canvas = tk.Canvas(frame, highlightthickness=0, width=1, height=1)
        canvas.pack(fill='both', expand=True)
        pending = None

        def redraw():
            nonlocal pending
            pending = None
            width = max(1, canvas.winfo_width())
            height = max(1, canvas.winfo_height())
            scale = min(width / image.width, height / image.height)
            size = (max(1, round(image.width * scale)),
                    max(1, round(image.height * scale)))
            preview = image.resize(size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(preview, master=root)
            canvas.delete('all')
            canvas.create_image(width / 2, height / 2, image=photo, anchor='center')
            canvas.photo = photo

        def on_resize(event):
            nonlocal pending
            if pending is not None:
                canvas.after_cancel(pending)
            pending = canvas.after(100, redraw)

        canvas.bind('<Configure>', on_resize)

    items = [('Исходное RGB', original), ('Y - яркость: (Y, 0, 0)', channels['Y']),
             ('I - цветовая составляющая: (0, I, 0)', channels['I']),
             ('Q - цветовая составляющая: (0, 0, Q)', channels['Q'])]
    for index, (title, image) in enumerate(items):
        frame = ttk.LabelFrame(root, text=title, padding=8)
        frame.grid(row=index // 2, column=index % 2, padx=6, pady=6, sticky='nsew')
        add_preview(frame, image)

    def reveal_window():
        """Показывает окно после запуска цикла событий и выводит его вперёд."""
        root.deiconify()
        root.state('zoomed')
        root.attributes('-topmost', True)
        root.lift()
        root.focus_force()
        root.after(500, lambda: root.attributes('-topmost', False))

    root.after(100, reveal_window)
    root.mainloop()


def select_image():
    """Возвращает строку с путём к изображению или пустую строку при отмене."""
    root = tk.Tk()
    root.withdraw()
    try:
        return filedialog.askopenfilename(
            parent=root,
            title='Выберите исходное изображение',
            filetypes=[
                ('Поддерживаемые изображения', '*.bmp *.png *.jpg *.jpeg'),
                ('BMP-изображения', '*.bmp'),
                ('PNG-изображения', '*.png'),
                ('JPEG-изображения', '*.jpg *.jpeg'),
                ('Все файлы', '*.*')
            ]
        )
    finally:
        root.destroy()


def main() -> None:
    """Выбирает файл, вычисляет каналы, сохраняет и показывает результаты."""
    selected = select_image()
    if not selected:
        return

    image_path: Path = Path(selected)
    output_dir: Path = Path(__file__).resolve().parent / 'results'
    try:
        original: Image.Image = read_image(image_path)
        Y, I, Q = rgb_to_yiq(np.asarray(original))
        channels = channel_images(Y, I, Q)

        output_dir.mkdir(parents=True, exist_ok=True)
        for name, image in channels.items():
            image.save(output_dir / f'{name}.bmp')
        make_overview(original, channels).save(output_dir / 'overview.png')
        print(f'Результат доступен по пути: {output_dir}')
    except (OSError, ValueError) as error:
        print(f'Ошибка обработки изображения: {error}')
        return

    show_results(original, channels, output_dir)


if __name__ == '__main__':
    main()
