from PIL import Image, ImageDraw, ImageFont
import io
import logging


def generate_neon_report_image(data: list, total: float, title: str):
    """
    Generates a neon-styled report image.
    data: list of dicts with 'description' and 'amount'
    """
    try:
        # Canvas setup
        width, height = 800, 1000
        img = Image.new('RGB', (width, height), color='#0a0a0a')
        draw = ImageDraw.Draw(img)

        # Aesthetic: Neon Border
        draw.rectangle([(10, 10), (width - 10, height - 10)], outline="#FF00FF", width=5)

        # Title and Total
        draw.text((50, 50), title.upper(), fill="#FF00FF", font_size=45)
        draw.text((50, 120), f"TOTAL: ₹{total:,.2f}", fill="#00FFFF", font_size=70)

        # Draw transactions
        y = 250
        draw.line([(50, 220), (750, 220)], fill="#FFFFFF", width=2)

        for d in data[:15]:  # Limit to 15 to prevent overflow
            text = f"{d['description'][:25]:<25} | ₹{d['amount']:,.2f}"
            draw.text((50, y), text, fill="#39FF14", font_size=35)
            y += 50

        if len(data) > 15:
            draw.text((50, y), "...and more.", fill="#AAAAAA", font_size=30)

        # Save to memory
        b = io.BytesIO()
        img.save(b, format='PNG')
        return b.getvalue()
    except Exception as e:
        logging.error(f"Visual Generation Error: {e}")
        raise e