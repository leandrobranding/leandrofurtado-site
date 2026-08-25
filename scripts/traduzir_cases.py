#!/usr/bin/env python3
"""Preenche `title_en` e `subtitle_en` dos cases.

    python3 scripts/traduzir_cases.py            # simula
    python3 scripts/traduzir_cases.py --gravar   # grava

Por que existe: em 23/08/2026 os 33 cases tinham os dois campos VAZIOS, e
`app/i18n.py::field` cai no português quando o inglês falta. Resultado: o site
em /en servia título e subtítulo em português — não é defeito de SEO, é
conteúdo faltando, e some no dia em que alguém traduz.

Só grava onde o campo está vazio. Um texto que o Leandro tenha escrito depois
fica onde está — este script preenche lacuna, não sobrescreve trabalho.

Critérios das traduções, para quem for revisar:
  - nome de marca, produto e evento não se traduz: Klabin, Electrolux,
    Linha Celebre, Corrida Positivo, Zack Delícias, Aruki.
  - nome de filme usa o título ORIGINAL, não a versão brasileira:
    "Divertidamente" é "Inside Out" em inglês, e um leitor de fora não
    reconheceria a palavra em português.
  - "DAF Caminhões" vira "DAF Trucks", que é como a marca se chama fora do
    Brasil.
  - "Secretariado" vira "Administrative Professionals", o nome da data
    equivalente em inglês, e não a tradução literal do cargo.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal        # noqa: E402
from app.models import Case                  # noqa: E402

# slug: (title_en, subtitle_en)
TRADUCOES = {
    # ---------------------------------------------------------- com página --
    "junte-seus-herois-marvel": (
        "Assemble Your Marvel Heroes",
        "Coca-Cola and Marvel activation at the Shell Convention"),
    "museu-do-silencio": (
        "Museum of Silence",
        "You never needed to see it to know what it was."),
    "primeira-conta": (
        "First Account",
        "First Account is a travelling event that turns opening a first bank "
        "account into a real ceremony."),
    "wandy-luz": (
        "Wandy Luz",
        "Visual identity and personal brand"),
    "maratona-internacional-do-parana": (
        "Paraná International Marathon Medals",
        "AI-generated films for the 5k, 10k, 21k and 42k medals."),
    "sucesso-sem-fronteiras": (
        "Success Without Borders",
        "Key visual for the DAF Trucks live marketing event"),
    "sucesso-sem-fronteiras-video": (
        "Success Without Borders ·︎ Video",
        "Promotional video for the DAF Trucks live marketing event"),
    "acao-cinema-divertidamente": (
        "Cinema Activation ·︎ Inside Out",
        "A Cinemark activation about emotions."),
    "pesquisa-de-satisfacao": (
        "Satisfaction Survey",
        "Internal survey across Colégios Maristas schools in Brazil, 2024"),
    "dia-do-profissional-do-secretariado": (
        "Administrative Professionals Day",
        "Campaign for Administrative Professionals Day at Hospital Marcelino "
        "Champagnat"),
    "leandro-elias-oppenheimer": (
        "Leandro Elias ·︎ Oppenheimer",
        "A cover of actor Cillian Murphy from the film Oppenheimer."),
    "congresso-agronegocio-global": (
        "Global Agribusiness Congress",
        "From law to field: a four-dimensional view of agribusiness."),
    "posts-instagram-aruki-delivery": (
        "Aruki Delivery",
        "Social media for Aruki, an Asian restaurant."),
    "invite-stay": (
        "Invite Stay",
        "Brand creation, visual identity and full branding."),
    "nao-somos-todo-mundo": (
        "We Are Not Everyone",
        "Enrolment campaign for Tistu Escola."),
    "move-impress": (
        "Move Impress",
        "Navigate the new."),
    "expo-telemaco-2025": (
        "Expo Telêmaco 2025",
        "Brand experience stand for Klabin."),
    "kto-em-curitiba": (
        "KTO in Curitiba",
        "The brand's arrival in the city."),
    "masterkey-masterboard-club": (
        "Masterkey | Masterboard Club",
        "Key visual for the Masterboard Club product."),
    "convencao-piemonte-poty": (
        "Piemonte Poty Convention",
        "Launch event for the Poty development at the Oscar Niemeyer Museum."),
    "corrida-positivo-2025": (
        "Corrida Positivo 2025",
        "OOH motion pieces for Corrida Positivo. Supported by Posigraf."),
    "realizar-o-sonho-da-facul-nao-e-sorte-e-escolha": (
        "Making the college dream happen is not luck, it is a choice.",
        "Brand experience campaign for Pravaler, student financing."),
    "zack-delicias": (
        "Zack Delícias",
        "Branding for the açaí brand Zack."),
    "linha-celebre": (
        "Linha Celebre 100 Years",
        "100 years of the Electrolux Linha Celebre range."),

    # ------------------------------------ categoria Sites (sem página própria) --
    "site": (
        "Klabin Website",
        "Corporate website for the pulp and packaging company"),
    "associacao-comercial-do-parana": (
        "Associação Comercial do Paraná Website",
        "Corporate portal for ACP"),
    "rottas-construtora": (
        "Rottas Construtora Website",
        "Corporate website and property showcase"),
    "coevo-construtora": (
        "Coevo Construtora",
        "Website for residential developments"),
    "assai-atacadista": (
        "Assaí Atacadista",
        "Website for the wholesale supermarket chain"),
    "mart-minas": (
        "Mart Minas Website",
        "Portal for the supermarket chain."),
    "brainbox": (
        "Brainbox Website",
        "Portal for the design studio."),
    "grupo-om": (
        "Grupo OM Website",
        "Website for the marketing and communications agency."),
    "saastec": (
        "Saastec",
        "ERP and business management"),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gravar", action="store_true")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        cases = {c.slug: c for c in db.query(Case).all()}

        sem_traducao = [s for s in cases if s not in TRADUCOES]
        sobrando = [s for s in TRADUCOES if s not in cases]
        if sem_traducao:
            print("SEM TRADUÇÃO (ficam em português):")
            for s in sem_traducao:
                print("  ", s, "|", cases[s].title_pt)
            print()
        if sobrando:
            print("SLUG QUE NÃO EXISTE MAIS no banco:")
            for s in sobrando:
                print("  ", s)
            print()

        mudaram = 0
        for slug, (t_en, s_en) in TRADUCOES.items():
            case = cases.get(slug)
            if case is None:
                continue
            novo_t = t_en if not (case.title_en or "").strip() else None
            novo_s = s_en if not (case.subtitle_en or "").strip() else None
            if novo_t is None and novo_s is None:
                continue
            mudaram += 1
            print(f"{slug}")
            if novo_t:
                print(f"    {case.title_pt}")
                print(f"  → {novo_t}")
            if novo_s:
                print(f"    {case.subtitle_pt}")
                print(f"  → {novo_s}")
            print()
            if args.gravar:
                if novo_t:
                    case.title_en = novo_t
                if novo_s:
                    case.subtitle_en = novo_s

        if args.gravar:
            db.commit()
        print(f"{len(cases)} cases · {mudaram} preenchidos · "
              f"{len(sem_traducao)} sem tradução")
        print("GRAVADO." if args.gravar else "Simulação. Use --gravar.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
