"""Export install assets from the approved bird-only app artwork."""

from pathlib import Path
import base64
import io

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
BRANDING = ROOT / "design/branding"
PUBLIC = ROOT / "frontend/public"
EXPORTS = BRANDING / "exports"


def main():
    image = Image.open(BRANDING / "noobtrade-bird-only-app-approved.png").convert("RGB")
    image = image.resize((1024, 1024), Image.Resampling.LANCZOS)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    image.save(EXPORTS / "noobtrade-bird-only-app-1024.png", optimize=True)
    icons = PUBLIC / "icons"
    for filename, size in {
        "noobtrade-32-v4.png": 32,
        "noobtrade-192-v4.png": 192,
        "noobtrade-512-v4.png": 512,
        "apple-touch-icon-v4.png": 180,
    }.items():
        image.resize((size, size), Image.Resampling.LANCZOS).save(icons / filename, optimize=True)

    # Extra inset protects the mascot under Android's circular launcher mask.
    maskable = Image.new("RGB", (512, 512), "black")
    maskable.paste(image.resize((400, 400), Image.Resampling.LANCZOS), (56, 56))
    maskable.save(icons / "noobtrade-maskable-512-v4.png", optimize=True)
    image.save(PUBLIC / "favicon-v4.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    image.save(PUBLIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    buffer = io.BytesIO()
    image.resize((512, 512), Image.Resampling.LANCZOS).save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    (icons / "noobtrade-app-icon-v4.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" '
        'role="img" aria-label="NoobTrade app icon">'
        f'<image width="512" height="512" href="data:image/png;base64,{encoded}"/></svg>\n',
        encoding="utf-8",
    )
    print("Exported opaque install icons, maskable icon, favicon and master artwork.")


if __name__ == "__main__":
    main()
