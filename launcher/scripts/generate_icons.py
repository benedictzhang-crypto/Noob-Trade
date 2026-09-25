from pathlib import Path
import shutil
import subprocess

from PIL import Image


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_PUBLIC_DIR = PROJECT_ROOT / "frontend" / "public"
FRONTEND_ICONS_DIR = FRONTEND_PUBLIC_DIR / "icons"
APP_ICON_SOURCE_PATH = PROJECT_ROOT / "design" / "branding" / "exports" / "noobtrade-bird-only-app-1024.png"
BASE_PNG_PATH = ASSETS_DIR / "noobtrade_icon.png"
ICO_PATH = ASSETS_DIR / "noobtrade.ico"
ICNS_PATH = ASSETS_DIR / "noobtrade.icns"
ICONSET_DIR = ASSETS_DIR / "noobtrade.iconset"


def build_assets():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    image = build_base_icon(1024)
    image.save(BASE_PNG_PATH, format="PNG")
    image.save(ICO_PATH, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    save_frontend_icons(image)
    save_frontend_favicons()
    maybe_build_icns(image)
    print(BASE_PNG_PATH)
    print(ICO_PATH)
    if ICNS_PATH.exists():
      print(ICNS_PATH)


def build_base_icon(size):
    with Image.open(APP_ICON_SOURCE_PATH) as source:
        return source.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)


def save_frontend_icons(image):
    icon_sets = {
        32: ["noobtrade-32.png", "noobtrade-32-v2.png", "noobtrade-32-v3.png", "noobtrade-32-v4.png", "noobtrade-32-v5.png"],
        180: ["apple-touch-icon.png", "apple-touch-icon-v2.png", "apple-touch-icon-v3.png", "apple-touch-icon-v4.png", "apple-touch-icon-v5.png"],
        192: ["noobtrade-192.png", "noobtrade-192-v2.png", "noobtrade-192-v3.png", "noobtrade-192-v4.png", "noobtrade-192-v5.png"],
        512: [
            "noobtrade-512.png",
            "noobtrade-512-v2.png",
            "noobtrade-512-v3.png",
            "noobtrade-512-v4.png",
            "noobtrade-512-v5.png",
            "noobtrade-maskable-512-v3.png",
            "noobtrade-maskable-512-v4.png",
            "noobtrade-maskable-512-v5.png",
        ],
    }

    for size, file_names in icon_sets.items():
        resized = image.resize((size, size), Image.Resampling.LANCZOS)
        for file_name in file_names:
            resized.save(FRONTEND_ICONS_DIR / file_name, format="PNG")

    apple_touch_icon = image.resize((180, 180), Image.Resampling.LANCZOS)
    apple_touch_icon.save(FRONTEND_PUBLIC_DIR / "apple-touch-icon.png", format="PNG")
    apple_touch_icon.save(FRONTEND_PUBLIC_DIR / "apple-touch-icon-precomposed.png", format="PNG")


def save_frontend_favicons():
    for file_name in ["favicon.ico", "favicon-v2.ico", "favicon-v3.ico", "favicon-v4.ico", "favicon-v5.ico"]:
        shutil.copyfile(ICO_PATH, FRONTEND_PUBLIC_DIR / file_name)


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


if __name__ == "__main__":
    build_assets()
