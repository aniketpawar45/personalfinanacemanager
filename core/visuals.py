from PIL import Image, ImageDraw
import io

def generate_neon_report_image(data, total, title):
    img = Image.new('RGB', (800, 1000), color='#0a0a0a')
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), title, fill="#FF00FF", font_size=50)
    draw.text((50, 120), f"₹{total:,.2f}", fill="#00FFFF", font_size=80)
    y = 250
    for entry in data[:10]:
        draw.text((50, y), f"{entry['description']} | ₹{entry['amount']}", fill="#39FF14", font_size=30)
        y += 70
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()