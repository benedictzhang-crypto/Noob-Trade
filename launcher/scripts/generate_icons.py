from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
BASE_PNG_PATH = ASSETS_DIR / "noobtrade_icon.png"
ICO_PATH = ASSETS_DIR / "noobtrade.ico"
ICNS_PATH = ASSETS_DIR / "noobtrade.icns"
ICONSET_DIR = ASSETS_DIR / "noobtrade.iconset"
WORDMARK_SVG_PATH = ASSETS_DIR / "noobtrade_wordmark.svg"

ORANGE = "#ff6900"
OFF_WHITE = "#fffaf5"
TEXT = ("Noob", "Trade")


def build_assets():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    image = build_base_icon(1024)
    image.save(BASE_PNG_PATH, format="PNG")
    image.save(ICO_PATH, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    WORDMARK_SVG_PATH.write_text(build_wordmark_svg(), encoding="utf-8")
    maybe_build_icns(image)
    print(BASE_PNG_PATH)
    print(ICO_PATH)
    if ICNS_PATH.exists():
      print(ICNS_PATH)


def build_base_icon(size):
    canvas = Image.new("RGBA", (size, size), OFF_WHITE)
    draw = ImageDraw.Draw(canvas)

    outer_margin = int(size * 0.06)
    card_radius = int(size * 0.16)
    draw.rounded_rectangle(
        [outer_margin, outer_margin, size - outer_margin, size - outer_margin],
        radius=card_radius,
        fill=OFF_WHITE,
    )

    noob_font = load_font(int(size * 0.23))
    trade_font = load_font(int(size * 0.22))

    noob_box = draw.textbbox((0, 0), TEXT[0], font=noob_font)
    trade_box = draw.textbbox((0, 0), TEXT[1], font=trade_font)
    noob_width = noob_box[2] - noob_box[0]
    trade_width = trade_box[2] - trade_box[0]

    noob_x = (size - noob_width) / 2
    trade_x = (size - trade_width) / 2
    noob_y = size * 0.23
    trade_y = size * 0.47

    draw.text((noob_x, noob_y), TEXT[0], font=noob_font, fill=ORANGE)
    draw.text((trade_x, trade_y), TEXT[1], font=trade_font, fill=ORANGE)

    underline_top = size * 0.425
    draw.rounded_rectangle(
        [size * 0.15, underline_top, size * 0.46, underline_top + size * 0.038],
        radius=int(size * 0.012),
        fill=ORANGE,
    )

    draw.polygon(
        [
            (size * 0.12, size * 0.18),
            (size * 0.18, size * 0.16),
            (size * 0.16, size * 0.24),
        ],
        fill=ORANGE,
    )
    draw.polygon(
        [
            (size * 0.17, size * 0.82),
            (size * 0.24, size * 0.8),
            (size * 0.18, size * 0.86),
        ],
        fill=ORANGE,
    )
    draw.polygon(
        [
            (size * 0.78, size * 0.84),
            (size * 0.86, size * 0.82),
            (size * 0.84, size * 0.88),
        ],
        fill=ORANGE,
    )

    return canvas


def load_font(size):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/SFNS.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    for candidate in candidates:
        font_path = Path(candidate)
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size=size)

    return ImageFont.load_default()


def maybe_build_icns(base_image):
    iconutil_path = shutil.which("iconutil")

    if not iconutil_path:
        return

    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)

    ICONSET_DIR.mkdir(parents=True, exist_ok=True)
    icon_sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }

    for file_name, size in icon_sizes.items():
        resized = base_image.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(ICONSET_DIR / file_name, format="PNG")

    subprocess.run(
        [iconutil_path, "-c", "icns", str(ICONSET_DIR), "-o", str(ICNS_PATH)],
        check=True,
    )


def build_wordmark_svg():
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" role="img" aria-label="Noob Trade">
  <rect width="1024" height="1024" rx="160" fill="{OFF_WHITE}" />
  <polygon points="124,184 180,170 162,246" fill="{ORANGE}" />
  <polygon points="168,840 244,818 184,882" fill="{ORANGE}" />
  <polygon points="790,850 872,830 846,892" fill="{ORANGE}" />
  <text x="512" y="380" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="234" font-weight="700" fill="{ORANGE}">Noob</text>
  <rect x="156" y="432" width="310" height="38" rx="10" fill="{ORANGE}" />
  <text x="512" y="666" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="228" font-weight="700" fill="{ORANGE}">Trade</text>
</svg>
"""


if __name__ == "__main__":
    build_assets()
