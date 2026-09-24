from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
FRONTEND_ICONS_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "icons"
BASE_PNG_PATH = ASSETS_DIR / "noobtrade_icon.png"
ICO_PATH = ASSETS_DIR / "noobtrade.ico"
ICNS_PATH = ASSETS_DIR / "noobtrade.icns"
ICONSET_DIR = ASSETS_DIR / "noobtrade.iconset"
WORDMARK_SVG_PATH = ASSETS_DIR / "noobtrade_wordmark.svg"

ORANGE = "#ff8a00"
BLACK = "#111111"
WHITE = "#ffffff"


def build_assets():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    image = build_base_icon(1024)
    image.save(BASE_PNG_PATH, format="PNG")
    image.save(ICO_PATH, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    save_frontend_icons(image)
    WORDMARK_SVG_PATH.write_text(build_wordmark_svg(), encoding="utf-8")
    maybe_build_icns(image)
    print(BASE_PNG_PATH)
    print(ICO_PATH)
    if ICNS_PATH.exists():
      print(ICNS_PATH)


def build_base_icon(size):
    canvas = Image.new("RGBA", (size, size), BLACK)
    draw = ImageDraw.Draw(canvas)

    scale = size / 1024
    points = lambda values: [(int(x * scale), int(y * scale)) for x, y in values]
    draw.polygon(points([(214, 754), (214, 270), (326, 270), (562, 586), (562, 270), (670, 270), (670, 754), (558, 754), (322, 438), (322, 754)]), fill=WHITE)
    draw.rectangle([int(554 * scale), int(270 * scale), int(820 * scale), int(378 * scale)], fill=WHITE)
    draw.rectangle([int(633 * scale), int(330 * scale), int(741 * scale), int(754 * scale)], fill=WHITE)
    draw.ellipse(
        [size * 0.489, size * 0.165, size * 0.585, size * 0.261],
        fill=ORANGE,
    )

    return canvas


def save_frontend_icons(image):
    sizes = {
        "noobtrade-32.png": 32,
        "noobtrade-192.png": 192,
        "noobtrade-512.png": 512,
        "apple-touch-icon.png": 180,
    }

    for file_name, size in sizes.items():
        resized = image.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(FRONTEND_ICONS_DIR / file_name, format="PNG")


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
    shutil.rmtree(ICONSET_DIR)


def build_wordmark_svg():
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 120" role="img" aria-label="NoobTrade">
  <text x="8" y="94" font-family="Inter, Arial, Helvetica, sans-serif" font-size="91" font-weight="800" letter-spacing="-5" fill="{BLACK}">NoobTrade</text>
  <circle cx="45" cy="18" r="10" fill="{ORANGE}" />
</svg>
"""


if __name__ == "__main__":
    build_assets()
