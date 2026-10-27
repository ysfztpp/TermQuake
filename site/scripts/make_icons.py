"""Generate the PWA icons (seismograph trace on ink). Run: python site/scripts/make_icons.py"""

from pathlib import Path

from PIL import Image, ImageDraw

INK = (23, 32, 38, 255)
SIGNAL = (232, 89, 12, 255)
# Seismograph trace on a 32x32 grid (same path as the in-app mark).
TRACE = [(2, 17), (9, 17), (11.5, 10), (15.5, 24), (19, 13), (21.2, 17), (30, 17)]
OUT = Path(__file__).resolve().parents[1] / "public"


def icon(size: int, *, padding: float, radius: float) -> Image.Image:
    scale = 4  # draw large, then downsample for smooth edges
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, s - 1, s - 1], radius=radius * s, fill=INK)
    inner = s * (1 - 2 * padding)
    offset = s * padding
    points = [(offset + x / 32 * inner, offset + y / 32 * inner) for x, y in TRACE]
    width = max(2, round(inner * 2.6 / 32))
    draw.line(points, fill=SIGNAL, width=width, joint="curve")
    for x, y in (points[0], points[-1]):
        r = width / 2
        draw.ellipse([x - r, y - r, x + r, y + r], fill=SIGNAL)
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    (OUT / "icons").mkdir(parents=True, exist_ok=True)
    icon(192, padding=0.14, radius=0.22).save(OUT / "icons/icon-192.png")
    icon(512, padding=0.14, radius=0.22).save(OUT / "icons/icon-512.png")
    # Maskable: full-bleed background, artwork inside the 80% safe zone.
    icon(512, padding=0.22, radius=0).save(OUT / "icons/icon-maskable-512.png")
    icon(180, padding=0.16, radius=0).save(OUT / "icons/apple-touch-icon.png")
    path = " ".join(f"{'M' if i == 0 else 'L'}{x} {y}" for i, (x, y) in enumerate(TRACE))
    (OUT / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="7" fill="#172026"/>'
        f'<path d="{path}" transform="translate(3 3) scale(.8125)" fill="none" stroke="#E8590C" '
        'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>\n',
        encoding="utf-8",
    )
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
