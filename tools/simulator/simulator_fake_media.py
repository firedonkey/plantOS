from __future__ import annotations

import struct
import zlib
import math


def make_plant_png(width: int = 360, height: int = 240, *, seed: int = 1, frame_index: int = 1) -> bytes:
    """Generate a small deterministic PNG that looks plant-like enough for UI tests."""
    width = max(32, min(1024, width))
    height = max(32, min(1024, height))
    frame_index = max(1, frame_index)
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            row.extend(_pixel(x, y, width, height, seed, frame_index))
        rows.append(bytes(row))
    raw = b"".join(rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw, 6))
        + _chunk(b"IEND", b"")
    )


def _pixel(x: int, y: int, width: int, height: int, seed: int, frame_index: int) -> tuple[int, int, int]:
    overlay = _badge_pixel(x, y, frame_index)
    if overlay is not None:
        return overlay

    horizon = int(height * 0.62)
    scene_phase = (frame_index % 12) / 12.0
    light_x = width * (0.62 + 0.18 * scene_phase)
    light_y = height * (0.12 + 0.06 * math.sin(frame_index * 0.7))
    light = max(0.0, 1.0 - ((x - light_x) ** 2 + (y - light_y) ** 2) / (width * height * 0.28))
    if y < horizon:
        base = 236 + int(12 * light)
        green_tint = 240 + int(8 * light)
        blue = 233 + int(12 * light) + int(4 * math.sin(frame_index * 0.8))
        r, g, b = base, green_tint, blue
    else:
        soil = 82 + int(10 * math.sin((x + seed + frame_index * 9) * 0.08))
        r, g, b = soil, 68, 48

    cx = width // 2
    growth = min(22, (frame_index - 1) * 2)
    sway = int(4 * math.sin(frame_index * 0.75))
    stem_top = int(height * 0.30) - growth
    stem_bottom = int(height * 0.73)
    if abs(x - (cx + sway)) <= 3 and stem_top <= y <= stem_bottom:
        return (50, 122, 72)

    for index, offset in enumerate((-72, -44, -20, 20, 48, 76)):
        leaf_cx = cx + offset + sway + int(3 * math.sin(frame_index * 0.55 + index))
        leaf_cy = int(height * (0.34 + 0.045 * (index % 3))) - growth // 2
        rx = 42 - (index % 2) * 6 + (frame_index % 3)
        ry = 16 + (index % 3) * 2 + (frame_index % 2)
        dx = (x - leaf_cx) / rx
        dy = (y - leaf_cy) / ry
        if dx * dx + dy * dy <= 1.0:
            stripe = int(10 * math.sin((x + seed * 7 + frame_index * 13) * 0.18))
            return (39, max(105, 145 + stripe), 79)

    pot_top = int(height * 0.70)
    pot_bottom = int(height * 0.91)
    pot_left = int(width * 0.31)
    pot_right = int(width * 0.69)
    taper = int((y - pot_top) * 0.18) if y >= pot_top else 0
    if pot_top <= y <= pot_bottom and pot_left + taper <= x <= pot_right - taper:
        return (142, 112, 82)

    stripe = _frame_stripe_pixel(x, y, width, height, frame_index)
    if stripe is not None:
        return stripe

    return (r, g, b)


def _badge_pixel(x: int, y: int, frame_index: int) -> tuple[int, int, int] | None:
    left = 14
    top = 14
    width = 92
    height = 31
    if not (left <= x < left + width and top <= y < top + height):
        return None
    if x in {left, left + width - 1} or y in {top, top + height - 1}:
        return (47, 133, 88)

    badge_color = _frame_color(frame_index)
    if (x - (left + 15)) ** 2 + (y - (top + 15)) ** 2 <= 64:
        return badge_color

    digit = _digit_pixel(x, y, f"{frame_index % 1000:03d}", left + 36, top + 8, scale=3)
    if digit is not None:
        return digit
    return (247, 250, 247)


def _digit_pixel(x: int, y: int, text: str, left: int, top: int, *, scale: int) -> tuple[int, int, int] | None:
    patterns = {
        "0": ("111", "101", "101", "101", "111"),
        "1": ("010", "110", "010", "010", "111"),
        "2": ("111", "001", "111", "100", "111"),
        "3": ("111", "001", "111", "001", "111"),
        "4": ("101", "101", "111", "001", "001"),
        "5": ("111", "100", "111", "001", "111"),
        "6": ("111", "100", "111", "101", "111"),
        "7": ("111", "001", "010", "010", "010"),
        "8": ("111", "101", "111", "101", "111"),
        "9": ("111", "101", "111", "001", "111"),
    }
    digit_width = 3 * scale
    gap = scale
    for index, char in enumerate(text):
        pattern = patterns.get(char)
        if pattern is None:
            continue
        x0 = left + index * (digit_width + gap)
        y0 = top
        if not (x0 <= x < x0 + digit_width and y0 <= y < y0 + 5 * scale):
            continue
        col = (x - x0) // scale
        row = (y - y0) // scale
        if pattern[row][col] == "1":
            return (31, 51, 42)
    return None


def _frame_stripe_pixel(x: int, y: int, width: int, height: int, frame_index: int) -> tuple[int, int, int] | None:
    if not (height - 16 <= y < height - 10):
        return None
    active_width = max(8, int((frame_index % 20) / 19 * (width - 28)))
    if 14 <= x <= 14 + active_width:
        return _frame_color(frame_index)
    if 14 <= x <= width - 14:
        return (222, 230, 224)
    return None


def _frame_color(frame_index: int) -> tuple[int, int, int]:
    palette = (
        (47, 133, 88),
        (52, 124, 177),
        (183, 104, 55),
        (124, 93, 168),
        (62, 145, 121),
    )
    return palette[frame_index % len(palette)]


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
