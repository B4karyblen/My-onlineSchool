#!/usr/bin/env python3
"""Build an ERPIE transcript (relevé de notes) from a JSON data file.

Averages, credit totals and mentions are computed here from the grades, never typed in,
so the document cannot contradict itself.

Run:  python3 build.py [data.json] [-o releve.html] [--preview-out preview.html]
Then print the HTML to PDF with ../tools/print-pdf.js (A4 portrait).
"""
import base64
import html
import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Standard French/LMD scale. Below 10 the module is not validated.
MENTIONS = [(16, "Très Bien"), (14, "Bien"), (12, "Assez Bien"), (10, "Passable")]


def mention(avg):
    return next((name for floor, name in MENTIONS if avg >= floor), "Ajourné")


def avg2(total, credits):
    return (Decimal(str(total)) / Decimal(credits)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def fr(num, places=2):
    """18.25 -> '18,25' (French decimal comma)."""
    q = Decimal(str(num)).quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP)
    return f"{q}".replace(".", ",")


def e(s):
    return html.escape(str(s), quote=True)


def compute(data):
    levels, all_cred, all_pts = [], 0, Decimal(0)
    for lv in data["levels"]:
        cred = sum(m[3] for m in lv["modules"])
        pts = sum(Decimal(str(m[4])) * m[3] for m in lv["modules"])
        acquired = sum(m[3] for m in lv["modules"] if m[4] >= 10)
        a = avg2(pts, cred)
        levels.append({**lv, "credits": cred, "acquired": acquired, "avg": a, "mention": mention(a)})
        all_cred += cred
        all_pts += pts
    overall = avg2(all_pts, all_cred)
    acquired = sum(lv["acquired"] for lv in levels)
    return levels, {"credits": all_cred, "acquired": acquired, "avg": overall, "mention": mention(overall)}


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Arimo:ital,wght@0,400;0,700;1,400&display=swap">')

CSS = """
/* A4 portrait, plain administrative layout: Arial-metric font, spreadsheet grid, greys only.
   Colour comes only from the logo and the cachet. */
.releve {
  --paper: #ffffff; --ink: #000000; --ink-2: #262626; --muted: #4d4d4d; --grid: #8c8c8c;
  --row-level: #bfbfbf; --row-head: #d9d9d9; --row-sum: #eeeeee; --box: #ececec;
  --f: 'Arimo', Arial, 'Liberation Sans', Helvetica, sans-serif;
  position: relative; width: 210mm; height: 297mm; overflow: hidden; box-sizing: border-box;
  padding: 10mm 15mm 8mm; background: var(--paper); color: var(--ink);
  font-family: var(--f); font-size: 2.9mm; line-height: 1.3;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
  display: flex; flex-direction: column;
}
.releve *, .releve *::before, .releve *::after { box-sizing: border-box; }
.releve p, .releve h1, .releve table, .releve dl, .releve dd { margin: 0; }

.hd { display: flex; justify-content: space-between; align-items: flex-start; }
.hd-school img { display: block; width: 34mm; height: 15.5mm; object-fit: contain; object-position: left center; }
.hd-school p { margin-top: 1.2mm; font-size: 2.6mm; font-weight: 700; max-width: 62mm; line-height: 1.25; }
.hd-school .meta { font-weight: 400; color: var(--ink-2); margin-top: .4mm; }
.hd-state { text-align: right; font-size: 2.6mm; line-height: 1.35; }
.hd-state b { font-size: 3mm; letter-spacing: .04em; }
.hd-state i { color: var(--ink-2); }

.ttl { text-align: center; margin-top: 2.5mm; }
.ttl h1 { font-size: 6.2mm; font-weight: 700; line-height: 1.1; }
.ttl p { font-size: 3.9mm; margin-top: .9mm !important; }
.ttl .small { font-size: 3.1mm; margin-top: .5mm !important; }

.id { margin-top: 3mm; background: var(--box); padding: 2mm 5mm; display: grid; grid-template-columns: 1fr 1fr; column-gap: 8mm; font-size: 3.1mm; line-height: 1.45; }
.id .name { font-size: 3.7mm; font-weight: 700; }

table.notes { margin-top: 3mm; width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 2.62mm; line-height: 1.17; }
.notes th, .notes td { border: .14mm solid var(--grid); padding: .5mm 1.4mm; vertical-align: middle; }
.notes thead th { background: var(--row-head); font-weight: 700; text-align: center; font-size: 2.55mm; white-space: nowrap; }
.notes .c-code { width: 14.5mm; white-space: nowrap; }
.notes .c-ects { width: 10.5mm; text-align: center; }
.notes .c-note { width: 15mm; text-align: center; font-variant-numeric: tabular-nums; }
.notes .c-res { width: 15mm; text-align: center; }
.notes .c-app { width: 54mm; }
.notes tbody td.c-app { color: var(--ink-2); font-style: italic; font-size: 2.45mm; }
.notes .sub { display: block; font-style: italic; color: var(--ink-2); font-size: 2.45mm; }
.notes tr.level td { background: var(--row-level); font-weight: 700; }
.notes tr.level td.c-app, .notes tr.avg td.c-app { font-style: normal; color: var(--ink); }
.notes tr.level td:nth-child(2) { text-transform: uppercase; }
.notes tr.avg td { background: var(--row-sum); font-weight: 700; }
.notes td.ok { font-weight: 700; }

table.sum { margin-top: 3mm; width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 2.7mm; }
.sum th, .sum td { border: .12mm solid var(--grid); padding: .8mm 2mm; text-align: center; }
.sum thead th { background: var(--row-level); font-weight: 700; font-size: 2.65mm; }
.sum caption { caption-side: top; text-align: left; font-weight: 700; padding-bottom: 1mm; font-size: 3.1mm; }
.sum td { font-size: 3.1mm; font-weight: 700; }
.sum td small { font-weight: 400; font-size: 2.65mm; color: var(--ink-2); }

.note { margin-top: 2mm; font-size: 2.55mm; color: var(--ink-2); line-height: 1.4; }
.note i { color: var(--ink); }

.ft { margin-top: 4mm; display: grid; grid-template-columns: 1fr 70mm; align-items: start; }
.place { font-size: 3.1mm; padding-top: .3mm; }
.sig { position: relative; text-align: center; font-size: 3.1mm; }
.sig-role { font-weight: 700; }
.sig-space { height: 17mm; }
.sig-name { font-weight: 700; }
.stamp { position: absolute; width: 27mm; height: 27mm; left: 38mm; top: -2.5mm; transform: rotate(-10deg); opacity: .93; pointer-events: none; }
.stamp img { width: 100%; height: 100%; display: block; }

.bottom { margin-top: auto; padding-top: 3mm; text-align: center; font-size: 2.35mm; color: var(--ink-2); line-height: 1.45; }
.bottom .legal { border-top: .12mm solid var(--grid); padding-top: 1.6mm; }
.bottom .page { margin-top: 1.2mm !important; color: var(--ink); }
"""


def render_page(d, logo, stamp):
    levels, total = compute(d)
    admitted = total["acquired"] == total["credits"]
    meta = " · ".join(x for x in (d.get("school_address", ""), d.get("school_contact", "")) if x)
    rows = []
    for lv in levels:
        lv_ok = lv["acquired"] == lv["credits"]
        rows.append(f'<tr class="level"><td class="c-code"></td><td>{e(lv["title"])} — {e(lv["semesters"])}</td>'
                    f'<td class="c-ects">{lv["credits"]}</td><td class="c-note"></td>'
                    f'<td class="c-res"></td><td class="c-app"></td></tr>')
        for code, title, sub, ects, note, app in lv["modules"]:
            ok = note >= 10
            rows.append(f'<tr><td class="c-code">{e(code)}</td><td>{e(title)}{f"<span class=sub>{e(sub)}</span>" if sub else ""}</td>'
                        f'<td class="c-ects">{ects if ok else 0}</td><td class="c-note">{fr(note)}</td>'
                        f'<td class="c-res">{"Acquis" if ok else "Non acquis"}</td><td class="c-app">{e(app)}</td></tr>')
        short = lv["title"].split("(")[-1].rstrip(")")
        rows.append(f'<tr class="avg"><td class="c-code"></td><td>Moyenne {e(short)} (pondérée par les crédits)</td>'
                    f'<td class="c-ects">{lv["acquired"]}</td><td class="c-note">{fr(lv["avg"])}</td>'
                    f'<td class="c-res">{"Validé" if lv_ok else "Non validé"}</td><td class="c-app">Mention {e(lv["mention"])}</td></tr>')
    decrees = " ; ".join(f"{e(k)} {e(v)}" for k, v in d["decrees"])
    return f"""<article class="releve" lang="fr" aria-label="Relevé de notes">
<header class="hd">
  <div class="hd-school"><img src="{e(logo)}" alt="{e(d['school_short'])}">
    <p>{e(d['school_name'])}{f'<span class="meta"><br>{e(meta)}</span>' if meta else ''}</p></div>
  <div class="hd-state"><b>{e(d['country'].upper())}</b><br><i>{e(d['motto'])}</i><br>{e(d['authority'])}</div>
</header>
<div class="ttl">
  <h1>Relevé de notes</h1>
  <p>{e(d['degree'])}{f" — parcours {e(d['specialization'])}" if d.get('specialization') else ''}</p>
  <p class="small">Bulletin {e(d.get('bulletin', 'annuel'))} {e(d['academic_year'])}</p>
  <p class="small">N° {e(d['document_number'])}</p>
</div>
<div class="id">
  <div><span class="name">{e(d['recipient_name'].upper())}</span><br>Matricule : {e(d['student_id'])}<br>
    {e(d['recipient_born'])} le {e(d['recipient_birth_date'])} à {e(d['recipient_birth_place'])}</div>
  <div>Programme : {e(d['degree'])}<br>Crédits du programme : {d['total_credits']} ECTS<br>Année académique : {e(d['academic_year'])}</div>
</div>
<table class="notes">
  <thead><tr><th class="c-code">Code</th><th>Intitulé du module</th><th class="c-ects">ECTS</th><th class="c-note">Note / 20</th><th class="c-res">Résultat</th><th class="c-app">Appréciation</th></tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>
<table class="sum">
  <caption>Bilan général du diplôme</caption>
  <thead><tr><th>Crédits validés</th><th>Moyenne générale finale</th><th style="width:40%">Mention</th><th>Décision du jury</th></tr></thead>
  <tbody><tr><td>{total['acquired']} / {total['credits']} ECTS</td><td>{fr(total['avg'])} / 20</td>
    <td>{e(total['mention'])}{f"<br><small>{e(d['jury_honours'])}</small>" if d.get('jury_honours') else ''}</td><td>{"Admis" if admitted else "Ajourné"}</td></tr></tbody>
</table>
<p class="note">Moyennes pondérées par les crédits ECTS. Un module est acquis à partir de 10 / 20.
  Mentions : Très Bien ≥ 16 · Bien ≥ 14 · Assez Bien ≥ 12 · Passable ≥ 10.<br><i>Ce document est à conserver. Il est délivré en un seul exemplaire ; toute rature ou surcharge l’annule.</i></p>
<div class="ft">
  <p class="place">Fait à {e(d['issue_city'])}, le {e(d['issue_date'])}</p>
  <div class="sig"><div class="sig-space"></div><div class="sig-role">{e(d['signatory_title'])}</div>{f'<div class="sig-name">{e(d["signatory_name"])}</div>' if d.get('signatory_name') else ''}
    {f'<div class="stamp"><img src="{e(stamp)}" alt="Cachet de l’établissement"></div>' if stamp else ''}</div>
</div>
<div class="bottom">
  <p class="legal">{e(d['school_short'])}, établissement privé d’enseignement supérieur — {decrees}.</p>
  <p class="page">Page 1 / 1</p>
</div>
</article>"""


def data_uri(path, mime):
    return f"data:{mime};base64,{base64.b64encode(Path(path).read_bytes()).decode()}"


def main():
    args = sys.argv[1:]
    src = Path(args[0]) if args and not args[0].startswith("-") else HERE / "sample-data.json"
    out = Path(args[args.index("-o") + 1]) if "-o" in args else HERE / "releve-sample.html"
    d = json.loads(src.read_text(encoding="utf-8"))
    base = src.parent
    stamp_path = base / d["school_stamp"] if d.get("school_stamp") else None
    stamp = d["school_stamp"] if stamp_path and stamp_path.exists() else ""
    page = render_page(d, d["school_logo"], stamp)
    out.write_text(f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relevé de notes · {e(d['recipient_name'])}</title>{FONTS}
<style>@page {{ size: 210mm 297mm; margin: 0; }} html, body {{ margin: 0; background: #e8e9eb; }}
@media screen {{ body {{ padding: 10mm; }} .releve {{ margin: 0 auto; box-shadow: 0 2mm 8mm rgba(0,0,0,.18); }} }}
@media print {{ html, body {{ background: none; }} }}{CSS}</style></head>
<body>{page}</body></html>
""", encoding="utf-8")
    print("wrote", out)
    if "--preview-out" in args:
        prev = Path(args[args.index("--preview-out") + 1])
        logo = data_uri(base / d["school_logo"], "image/webp")
        st = data_uri(stamp_path, "image/webp") if stamp else ""
        prev.write_text(preview(render_page(d, logo, st), d), encoding="utf-8")
        print("wrote", prev)


def preview(page, d):
    return f"""<title>ERPIE Relevé de Notes</title>
<meta name="claude:viewport-fit-sides" content="cover">
{FONTS}
<style>
:root {{ --desk: #e6e7e9; --chrome: #1d2125; --chrome-dim: #5d646c; color-scheme: light; }}
body {{ background: var(--desk); color: var(--chrome); font-family: 'Arimo', Arial, sans-serif; }}
.page {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 18px 32px; }}
.bar {{ max-width: 900px; margin: 0 auto 14px; display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; }}
.bar h1 {{ margin: 0; font-size: 18px; font-weight: 700; }}
.bar p {{ margin: 0; font-size: 12px; color: var(--chrome-dim); letter-spacing: .04em; }}
.sheet {{ position: relative; margin: 0 auto; box-shadow: 0 1px 2px rgba(0,0,0,.15), 0 14px 40px rgba(0,0,0,.18); }}
.sheet .releve {{ position: absolute; top: 0; left: 0; transform-origin: 0 0; }}
{CSS}
</style>
<div class="page">
  <div class="bar"><h1>ERPIE · Relevé de notes</h1><p>A4 portrait · exemple : {e(d['recipient_name'])}, {e(d['student_id'])}</p></div>
  <div class="sheet" id="sheet">{page}</div>
</div>
<script>
(function () {{
  var MM = 96 / 25.4, W = 210 * MM, H = 297 * MM, sheet = document.getElementById('sheet'), page = sheet.firstElementChild;
  function fit() {{
    var avail = Math.min(sheet.parentElement.clientWidth - 32, 900), s = Math.min(1.25, avail / W);
    sheet.style.width = W * s + 'px'; sheet.style.height = H * s + 'px'; page.style.transform = 'scale(' + s + ')';
  }}
  fit(); window.addEventListener('resize', fit);
}})();
</script>
"""


if __name__ == "__main__":
    main()
