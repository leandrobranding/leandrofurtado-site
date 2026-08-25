"""Gera cases fictícios de marcação (imagens abstratas) para visualizar o layout.

Uso:  .venv/bin/python scripts/seed_demo.py
Para remover depois: apague os cases no admin (a mídia é removida junto).
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFilter

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Case, Category, MediaItem, Tag
from app.services.seeds import run_seeds

random.seed(7)

# Paleta da marca: somente preto, branco e cinzas.
PALETTES = {
    "solaris":  [("#e8e6e1", "#141414", "#f5f3ee"), "Key Visual e campanha para festival de música"],
    "aurora":   [("#b9b7b2", "#0f0f0f", "#ffffff"), "Identidade visual para healthtech"],
    "verde":    [("#8a8883", "#191919", "#e8e6e1"), "Branding e social para marca de cosméticos"],
    "porto":    [("#d4d2cd", "#111111", "#ffffff"), "Interface digital para fintech"],
    "brasa":    [("#9c9a95", "#0c0c0c", "#f5f3ee"), "Motion e vídeo para lançamento automotivo"],
    "areia":    [("#c6c4bf", "#161616", "#ffffff"), "Fotografia editorial para moda"],
}


def grain(img, amount=14):
    noise = Image.effect_noise(img.size, amount).convert("L")
    return Image.composite(img, img.point(lambda p: min(255, p + 8)), noise.point(lambda p: 255 if p > 128 else 0))


def gradient(size, c1, c2, angle=90):
    w, h = size
    base = Image.new("RGB", (2, 2))
    grad = Image.new("L", (max(w, h), 1))
    for x in range(grad.width):
        grad.putpixel((x, 0), int(255 * x / grad.width))
    grad = grad.resize((max(w, h), max(w, h))).rotate(angle, expand=False)
    grad = grad.resize(size)
    a = Image.new("RGB", size, c1)
    b = Image.new("RGB", size, c2)
    return Image.composite(b, a, grad)


def art(size, accent, dark, light, kind):
    """Composições monocromáticas na linguagem angular da marca LF:
    diagonais cortadas, blocos, grids e formas duras — preto/branco/cinza."""
    w, h = size
    img = gradient(size, dark, "#2b2b2b", random.choice([35, 115, 150]))
    d = ImageDraw.Draw(img, "RGBA")
    kind = kind % 5
    if kind == 0:  # barras diagonais cortadas (eco dos terminais do F)
        step = w // 9
        for i in range(-h, w + h, step):
            g = random.choice(["#3a3a3a", "#565656", accent])
            d.polygon([(i, h), (i + h, 0), (i + h + step // 3, 0), (i + step // 3, h)], fill=g)
        d.polygon([(0, h), (w // 3, h), (w // 2, h - h // 4), (0, h - h // 4)], fill=dark)
    elif kind == 1:  # bloco L monumental
        m = w // 8
        d.rectangle([m, m, m + w // 5, h - m], fill=light)
        d.rectangle([m, h - m - h // 6, w - m * 2, h - m], fill=light)
        d.polygon([(w - m * 2, h - m - h // 6), (w - m, h - m - h // 6 - 40), (w - m * 2, h - m)], fill=light)
        d.rectangle([m + w // 3, m, w - m, m + 8], fill="#4a4a4a")
    elif kind == 2:  # grid modernista
        cols, rows = 6, 4
        cw, ch = (w - 160) // cols, (h - 160) // rows
        for r in range(rows):
            for c in range(cols):
                x, y = 80 + c * cw, 80 + r * ch
                if random.random() < .28:
                    d.rectangle([x + 6, y + 6, x + cw - 6, y + ch - 6],
                                fill=random.choice([light, "#4a4a4a", accent]))
                else:
                    d.rectangle([x + 6, y + 6, x + cw - 6, y + ch - 6], outline="#333333", width=2)
    elif kind == 3:  # quadrados concêntricos deslocados
        cx, cy = w // 2, h // 2
        for i, r in enumerate(range(min(w, h) // 2 - 60, 40, -70)):
            off = i * 14
            d.rectangle([cx - r + off, cy - r, cx + r + off, cy + r],
                        outline=light if i % 2 else "#4f4f4f", width=4)
        d.rectangle([cx - 34, cy - 34, cx + 34, cy + 34], fill=light)
    else:  # meio-tom (halftone) em faixa diagonal
        for y in range(60, h - 40, 46):
            for x in range(60, w - 40, 46):
                t = (x + y * 1.4) / (w + h * 1.4)
                r = max(2, int(16 * (1 - abs(t - .5) * 2.2)))
                if r > 2:
                    d.ellipse([x - r, y - r, x + r, y + r], fill=light if t < .5 else "#5a5a5a")
    return grain(img)


def save(img, folder, name):
    dest = settings.upload_dir / folder
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{name}.webp"
    img.save(path, "WEBP", quality=84, method=6)
    return f"{folder}/{name}.webp"


CASES = [
    ("Solaris Festival", "solaris", "key-visual", ["key visual", "campanha", "ia"], "2026",
     "Key Visual e sistema de campanha para um festival de música: conceito gerado com IA, refinado à mão e desdobrado em OOH, social e palco.",
     "Key Visual and campaign system for a music festival: AI-assisted concept, hand-refined and rolled out to OOH, social and stage."),
    ("Aurora Health", "aurora", "branding", ["branding", "identidade"], "2025",
     "Identidade visual completa para healthtech — do símbolo ao design system digital.",
     "Complete visual identity for a healthtech — from symbol to digital design system."),
    ("Verde Cosmética", "verde", "social-media", ["social media", "conteúdo"], "2025",
     "Direção criativa e social media para marca de cosméticos naturais.",
     "Creative direction and social media for a natural cosmetics brand."),
    ("Porto Bank", "porto", "digital-ui", ["ui design", "produto"], "2024",
     "Interface do app e sistema visual do banco digital.",
     "App interface and visual system for a digital bank."),
    ("Brasa Motors", "brasa", "motion-video", ["motion", "vídeo", "3d"], "2024",
     "Filme de lançamento e pacote de motion para campanha automotiva.",
     "Launch film and motion package for an automotive campaign."),
    ("Areia Editorial", "areia", "fotografia", ["fotografia", "editorial"], "2023",
     "Fotografia editorial de moda — direção, captação e tratamento.",
     "Fashion editorial photography — direction, shooting and retouching."),
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    run_seeds(db)
    cats = {c.slug: c for c in db.query(Category).all()}

    from app.services.images import slugify

    for i, (title, pal, cat_slug, tag_names, year, sum_pt, sum_en) in enumerate(CASES):
        slug = slugify(title)
        if db.query(Case).filter_by(slug=slug).first():
            print(f"· {title} já existe, pulando")
            continue
        accent, dark, light = PALETTES[pal][0]
        cover = art((1600, 1200), accent, dark, light, i % 5)
        cover_rel = save(cover, slug, "cover")

        case = Case(
            slug=slug, title_pt=title, title_en=title,
            subtitle_pt=PALETTES[pal][1], subtitle_en=sum_en.split(":")[0],
            client=title.split(" ")[0], year=year,
            role_pt="Direção de Arte, Design, Motion", role_en="Art Direction, Design, Motion",
            body_pt=sum_pt, body_en=sum_en,
            cover_image=cover_rel, accent="",
            category_id=cats.get(cat_slug).id if cats.get(cat_slug) else None,
            featured=i < 4, published=True, sort=i,
        )
        for name in tag_names:
            tslug = name.replace(" ", "-")
            tag = db.query(Tag).filter_by(slug=tslug).first() or Tag(slug=tslug, name=name)
            case.tags.append(tag)

        # galeria: 4-5 imagens variadas (full / half / tall)
        layouts = ["full", "half", "half", "full", "tall"]
        random.shuffle(layouts)
        for n in range(random.randint(4, 5)):
            layout = layouts[n % len(layouts)]
            size = {"full": (2000, 1200), "half": (1200, 900), "tall": (1100, 1400)}[layout]
            g = art(size, accent, dark, light, (i + n + 1) % 5)
            rel = save(g, slug, f"g{n}")
            case.media.append(MediaItem(kind="image", src=rel, thumb=rel, layout=layout, sort=n))

        db.add(case)
        print(f"✔ {title} ({len(case.media)} imagens)")

    db.commit()
    db.close()
    print("\nCases demo criados. Apague-os pelo admin quando subir os reais.")


if __name__ == "__main__":
    main()
