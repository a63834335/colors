# -*- coding: utf-8 -*-
from PIL import Image
from app import extract_palette


def make_image(colors, size=(48, 48)):
    """Картинка из равных вертикальных полос заданных цветов."""
    img = Image.new('RGB', size)
    w = size[0] // len(colors)
    for i, rgb in enumerate(colors):
        img.paste(rgb, (i * w, 0, (i + 1) * w, size[1]))
    return img


EXAMPLES = [
    ('Однотонный красный', [(255, 0, 0)], 1, ['#ff0000']),
    ('Белый', [(255, 255, 255)], 1, ['#ffffff']),
    ('Красный + синий пополам', [(255, 0, 0), (0, 0, 255)], 2, ['#ff0000', '#0000ff']),
    ('Три цвета', [(255, 0, 0), (0, 128, 0), (0, 0, 255)], 3,
     ['#ff0000', '#008000', '#0000ff']),
]


def main():
    failed = 0
    for title, colors, n, expected in EXAMPLES:
        palette = extract_palette(make_image(colors), n)
        got = [c['hex'] for c in palette]
        ok = set(got) == set(expected) and len(got) == len(expected)
        if not ok:
            failed += 1
        print(f"[{'OK' if ok else 'ОШИБКА'}] {title}: ожидалось {expected}, получено {got}")
        for c in palette:
            print(f"        {c['hex']}  {c['name']}  {c['percent']}%")
    print('---')
    print('Все примеры пройдены.' if failed == 0 else f'Провалено примеров: {failed}')


if __name__ == '__main__':
    main()