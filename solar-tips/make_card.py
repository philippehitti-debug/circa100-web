"""Render a 1080x1350 Instagram card (JPEG) for one solar tip.
Usage: python make_card.py <tip_id> [out.jpg]
"""
import json, sys, os, textwrap
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350
INK, BLUE, SAGE, SUN, WHITE, MUTED = (5, 5, 5), (47, 124, 240), (185, 202, 147), (242, 179, 61), (240, 242, 245), (150, 158, 168)


def font(name, size, weight):
    f = ImageFont.truetype(os.path.join(HERE, "fonts", name), size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def wrap(draw, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render(tip, out_path, number=None):
    tech = tip["audience"] == "technical"
    accent = BLUE if tech else SUN
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)

    # sun motif
    cx, cy = W - 150, 170
    for r, a in [(260, 18), (200, 28), (140, 46)]:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ov).ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent + (a,))
        im.paste(ov, (0, 0), ov)
    d = ImageDraw.Draw(im)
    d.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], fill=accent)

    m = 90
    lab = font("Oswald.ttf", 30, b"Medium")
    label = ("FOR TECHNICAL TEAMS" if tech else "FOR EVERY HOME") + "  ·  " + tip["cat"].upper()
    d.text((m, 110), label, font=lab, fill=accent)
    if number:
        d.text((m, 160), f"SOLAR TIP #{number:03d}", font=font("Oswald.ttf", 26, b"Light"), fill=MUTED)

    # title
    tf = font("Oswald.ttf", 92, b"Medium")
    y = 330
    for ln in wrap(d, tip["title"], tf, W - 2 * m):
        d.text((m, y), ln, font=tf, fill=WHITE)
        y += 104
    y += 24
    d.rectangle([m, y, m + 120, y + 8], fill=accent)
    y += 60

    bf = font("Inter.ttf", 42, b"Regular")
    for ln in wrap(d, tip["body"], bf, W - 2 * m):
        d.text((m, y), ln, font=bf, fill=(214, 218, 224))
        y += 62
    y += 36
    mf = font("Inter.ttf", 32, b"Light")
    for ln in wrap(d, tip.get("more", ""), mf, W - 2 * m):
        if y > H - 230:
            break
        d.text((m, y), ln, font=mf, fill=MUTED)
        y += 48

    # footer
    d.line([m, H - 170, W - m, H - 170], fill=(60, 64, 70), width=2)
    d.text((m, H - 135), "circa 100", font=font("Oswald.ttf", 52, b"Medium"), fill=WHITE)
    tw = d.textlength("circa 100", font=font("Oswald.ttf", 52, b"Medium"))
    d.ellipse([m + tw + 8, H - 98, m + tw + 22, H - 84], fill=(242, 130, 40))
    sf = font("Inter.ttf", 28, b"Regular")
    t = "circa100.com/solar-blog"
    d.text((W - m - d.textlength(t, font=sf), H - 118), t, font=sf, fill=MUTED)
    im.save(out_path, "JPEG", quality=90, optimize=True, progressive=False)
    return out_path


if __name__ == "__main__":
    data = json.load(open(os.path.join(HERE, "tips.json"), encoding="utf-8"))
    tid = sys.argv[1]
    tip = next(t for t in data["tips"] if t["id"] == tid)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "cards", f"{tid}.jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(render(tip, out))
