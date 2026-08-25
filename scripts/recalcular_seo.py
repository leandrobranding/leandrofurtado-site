#!/usr/bin/env python3
"""Recalcula `seo_title` e `seo_desc` de todos os cases com a fórmula atual.

    python3 scripts/recalcular_seo.py            # simula, não grava
    python3 scripts/recalcular_seo.py --gravar   # grava

Por que existe: o SEO do case é DERIVADO do conteúdo e recalculado a cada save
no painel (ver `apply_case_form`). Quando a fórmula muda — como em 22/08/2026,
quando o cliente passou a entrar no título e a descrição deixou de ser só o
subtítulo — os cases já cadastrados continuam com o texto antigo até alguém
reabrir e salvar cada um. Este script faz isso de uma vez.

Não vira migração de propósito: migração roda a cada boot e sobrescreveria uma
edição futura sem avisar. Aqui é uma decisão explícita, tomada quando a fórmula
muda, e o resultado continua editável pelo painel do jeito de sempre.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal            # noqa: E402
from app.models import Case, Category            # noqa: E402
from app.services import seo                     # noqa: E402
from app.services.seo import _visivel            # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gravar", action="store_true",
                    help="grava no banco (sem isto, só mostra o que mudaria)")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        categorias = {c.id: c.name_pt for c in db.query(Category).all()}
        mudaram = 0
        total = 0

        for case in db.query(Case).order_by(Case.id).all():
            total += 1
            titulo = seo.titulo_para_busca(case.title_pt or "", case.client or "")[:200]
            desc = seo.descricao_para_busca(
                seo.resumo_do_case(case),
                categorias.get(case.category_id, ""),
                case.client or "",
                case.year or "",
            )[:320]

            if titulo == (case.seo_title or "") and desc == (case.seo_desc or ""):
                continue

            mudaram += 1
            print(f"\n{case.slug}")
            if titulo != (case.seo_title or ""):
                print(f"  título  {_visivel(case.seo_title or ''):3} -> {_visivel(titulo):3}")
                print(f"    antes: {case.seo_title or '(vazio)'}")
                print(f"    novo : {titulo}")
            if desc != (case.seo_desc or ""):
                print(f"  descr.  {_visivel(case.seo_desc or ''):3} -> {_visivel(desc):3}")
                print(f"    antes: {case.seo_desc or '(vazio)'}")
                print(f"    novo : {desc}")

            if args.gravar:
                case.seo_title, case.seo_desc = titulo, desc

        if args.gravar:
            db.commit()

        print(f"\n{total} cases lidos, {mudaram} com texto novo.")
        print("GRAVADO." if args.gravar else "Simulação: nada foi gravado. Use --gravar.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
