"""Generate a tiny smoke-test image with text for OCR validation."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).parent / "smoke_text.png"


def main() -> None:
    img = Image.new("RGB", (640, 200), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except OSError:
        font = ImageFont.load_default()
    draw.text((40, 80), "WALL 4200", fill="black", font=font)
    draw.rectangle([20, 20, 620, 180], outline="black", width=3)
    img.save(OUT)
    print(f"smoke fixture: {OUT}")


if __name__ == "__main__":
    main()
