#!/usr/bin/env python3
"""Build an ERPIE transcript (relevé de notes) from a JSON data file.

Averages, credit totals and mentions are computed here from the grades, never typed in,
so the document cannot contradict itself.

Run:  python3 build.py [data.json] [-o releve.html] [--preview-out preview.html]
Then print the HTML to PDF with ../tools/print-pdf.js (A4 portrait).
Needs `segno` (pip install segno) for the verification QR code.
"""
import base64
import html
import io
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


def qr_svg(url):
    import segno
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", border=0, dark="#16191d", xmldecl=False, svgns=True, nl=False)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+SC:wght@600;700'
         '&family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Jost:wght@400;500;600&display=swap">')

CSS = """
/* A4 portrait, 16 mm content margins inside a fine double rule. Monochrome: only the logo and the cachet carry colour. */
.releve {
  --paper: #ffffff; --ink: #14171a; --ink-2: #3a4047; --muted: #6b727a; --rule: #c9cdd2; --band: #f2f3f4; --head: #1d2125;
  --f-display: 'Cormorant SC', Garamond, 'Times New Roman', serif;
  --f-body: 'EB Garamond', Garamond, 'Times New Roman', serif;
  --f-meta: 'Jost', 'Futura', 'Century Gothic', 'Helvetica Neue', Arial, sans-serif;
  position: relative; width: 210mm; height: 297mm; overflow: hidden; box-sizing: border-box;
  padding: 13.5mm 15mm 12mm; background: var(--paper); color: var(--ink);
  font-family: var(--f-body); font-size: 3.1mm; line-height: 1.3;
  -webkit-print-color-adjust: exact; print-color-adjust: exact; font-kerning: normal;
  display: flex; flex-direction: column;
}
.releve *, .releve *::before, .releve *::after { box-sizing: border-box; }
.releve p, .releve h1, .releve h2, .releve table { margin: 0; }
.releve::before, .releve::after { content: ""; position: absolute; pointer-events: none; }
.releve::before { inset: 7mm; border: .45mm solid var(--head); }
.releve::after { inset: 8.3mm; border: .15mm solid var(--head); }

/* Header: school left, State right */
.hd { display: grid; grid-template-columns: 1fr auto; align-items: start; gap: 6mm; }
.hd-school { display: flex; align-items: center; gap: 3.2mm; }
.hd-school img { width: 31mm; height: 14mm; object-fit: contain; object-position: left center; flex: none; }
.hd-school-name { font-family: var(--f-display); font-weight: 700; font-size: 3.55mm; line-height: 1.15; letter-spacing: .02em; max-width: 54mm; }
.hd-school-meta { font-family: var(--f-meta); font-size: 1.95mm; color: var(--muted); margin-top: .8mm; letter-spacing: .02em; }
.hd-state { text-align: center; }
.hd-country { font-family: var(--f-display); font-weight: 700; font-size: 3.7mm; letter-spacing: .14em; margin-right: -.14em; }
.hd-motto { font-style: italic; font-size: 2.8mm; color: var(--ink-2); }
.hd-rule { width: 18mm; height: .15mm; background: var(--ink); margin: 1mm auto; }
.hd-authority { font-style: italic; font-size: 2.6mm; color: var(--ink-2); max-width: 74mm; line-height: 1.2; text-wrap: balance; }
.decrees { margin-top: 2.4mm; padding-top: 1.3mm; border-top: .15mm solid var(--rule); font-family: var(--f-meta); font-size: 1.85mm;
  letter-spacing: .01em; color: var(--muted); text-align: center; }
.decrees b { font-weight: 500; color: var(--ink-2); }
.decrees span + span::before { content: "·"; margin: 0 1.6mm; }

/* Title */
.ttl { display: grid; grid-template-columns: 1fr auto 1fr; align-items: end; margin-top: 3.4mm; }
.ttl h1 { grid-column: 2; font-family: var(--f-display); font-weight: 700; font-size: 7.6mm; letter-spacing: .14em; margin-right: -.14em; line-height: 1; text-align: center; }
.ttl-sub { grid-column: 2; text-align: center; font-style: italic; font-size: 3.5mm; color: var(--ink-2); margin-top: .8mm !important; }
.ttl-no { grid-column: 3; grid-row: 1; justify-self: end; font-family: var(--f-meta); font-size: 2.2mm; letter-spacing: .1em; color: var(--ink-2); font-variant-numeric: tabular-nums; }

/* Student identification */
.id { margin-top: 3mm; display: grid; grid-template-columns: repeat(3, 1fr); border: .2mm solid var(--ink); }
.id > div { padding: 1.5mm 2.6mm; border-left: .15mm solid var(--rule); border-top: .15mm solid var(--rule); min-width: 0; }
.id > div:nth-child(3n+1) { border-left: 0; }
.id > div:nth-child(-n+3) { border-top: 0; }
.id dt { font-family: var(--f-meta); font-size: 1.75mm; font-weight: 500; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
.id dd { margin: .3mm 0 0; font-size: 3.2mm; line-height: 1.2; }
.id dd.name { font-family: var(--f-display); font-weight: 700; font-size: 3.9mm; letter-spacing: .04em; }
.id .wide { grid-column: span 2; }

/* Grade tables */
.lvl { margin-top: 3.4mm; }
table.notes { width: 100%; border-collapse: collapse; table-layout: fixed; }
.notes caption { caption-side: top; text-align: left; background: var(--head); color: #fff; padding: 1mm 2.2mm; font-family: var(--f-meta);
  font-size: 2.35mm; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; }
.notes caption span { font-weight: 400; letter-spacing: .06em; text-transform: none; opacity: .8; margin-left: 2mm; }
.notes th { font-family: var(--f-meta); font-size: 1.8mm; font-weight: 500; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-2);
  background: var(--band); padding: .8mm 2.2mm; border-bottom: .2mm solid var(--ink); text-align: left; white-space: nowrap; }
.notes td { padding: .92mm 2.2mm; border-bottom: .12mm solid var(--rule); vertical-align: top; font-size: 2.85mm; line-height: 1.18; }
.notes .c-code { width: 15mm; }
.notes td.c-code { font-family: var(--f-meta); font-size: 2.1mm; letter-spacing: .03em; color: var(--ink-2); padding-top: 1.25mm; }
.notes .c-ects, .notes .c-note { width: 13mm; text-align: center; font-variant-numeric: tabular-nums lining-nums; }
.notes td.c-note { font-weight: 600; }
.notes .c-app { width: 58mm; }
.notes td.c-app { font-style: italic; color: var(--ink-2); font-size: 2.65mm; }
.notes .sub { display: block; font-style: italic; font-size: 2.5mm; color: var(--muted); }
.notes tfoot td { border-bottom: .2mm solid var(--ink); border-top: .2mm solid var(--ink); background: var(--band); padding: 1mm 2.2mm; font-size: 2.85mm; }
.notes tfoot .lbl { font-family: var(--f-meta); font-size: 2.05mm; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; }
.notes tfoot .c-note { font-size: 3.2mm; }

/* Summary */
.sum { margin-top: 3mm; display: grid; grid-template-columns: 1fr 1fr 1.5fr; border: .35mm solid var(--ink); }
.sum > div { padding: 1.4mm 3mm; border-left: .15mm solid var(--rule); }
.sum > div:first-child { border-left: 0; }
.sum dt { font-family: var(--f-meta); font-size: 1.8mm; font-weight: 500; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
.sum dd { margin: .5mm 0 0; font-family: var(--f-display); font-weight: 700; font-size: 4.6mm; line-height: 1.1; font-variant-numeric: lining-nums; }
.sum dd small { font-family: var(--f-body); font-weight: 400; font-size: 3mm; color: var(--ink-2); }
.sum .honours { display: block; font-family: var(--f-body); font-style: italic; font-weight: 400; font-size: 3mm; color: var(--ink-2); margin-top: .4mm; }

/* Footer */
.ft { margin-top: auto; padding-top: 3mm; display: grid; grid-template-columns: 30mm 1fr; gap: 6mm; align-items: end; }
.verify { text-align: center; }
.verify img { display: block; width: 19mm; height: 19mm; margin: 0 auto; }
.verify p { font-family: var(--f-meta); font-size: 1.6mm; letter-spacing: .06em; color: var(--muted); margin-top: 1.2mm !important; line-height: 1.3; word-break: break-all; }
.verify b { display: block; font-weight: 600; color: var(--ink-2); letter-spacing: .1em; }
.place { font-style: italic; font-size: 3.1mm; color: var(--ink-2); text-align: left; padding-left: 2mm; }
.sigs { position: relative; display: grid; grid-template-columns: 1fr 1fr; gap: 8mm; margin-top: 2.2mm; }
.sig { text-align: center; }
.sig-role { font-family: var(--f-meta); font-size: 2.05mm; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; }
.sig-space { height: 15mm; }
.sig-line { width: 44mm; margin: 0 auto; border-top: .2mm solid var(--ink-2); }
.sig-name { margin-top: 1mm; font-size: 3.2mm; font-weight: 500; }
.stamp { position: absolute; width: 27mm; height: 27mm; right: 2mm; top: -4.2mm; transform: rotate(-10deg); opacity: .93; pointer-events: none; }
.stamp img { width: 100%; height: 100%; display: block; }
.legend { margin-top: 5.5mm; padding-top: 1.3mm; border-top: .15mm solid var(--rule); display: flex; justify-content: space-between; gap: 4mm;
  font-family: var(--f-meta); font-size: 1.75mm; letter-spacing: .03em; color: var(--muted); }
.legend b { font-weight: 600; color: var(--ink-2); }
"""


def render_page(d, logo, stamp, qr):
    levels, total = compute(d)
    meta = " · ".join(x for x in (d.get("school_address", ""), d.get("school_contact", "")) if x)
    out = [f'<article class="releve" lang="fr" aria-label="Relevé de notes">']
    out.append(f"""<header class="hd">
  <div class="hd-school"><img src="{e(logo)}" alt="{e(d['school_short'])}">
    <div><div class="hd-school-name">{e(d['school_name'])}</div>{f'<div class="hd-school-meta">{e(meta)}</div>' if meta else ''}</div></div>
  <div class="hd-state"><div class="hd-country">{e(d['country'])}</div><div class="hd-motto">{e(d['motto'])}</div>
    <div class="hd-rule"></div><div class="hd-authority">{e(d['authority'])}</div></div>
</header>
<p class="decrees">{''.join(f'<span><b>{e(k)}</b> {e(v)}</span>' for k, v in d['decrees'])}</p>
<div class="ttl"><h1>Relevé de notes</h1><div class="ttl-no">N° {e(d['document_number'])}</div>
  <p class="ttl-sub">{e(d['degree'])}{f", parcours {e(d['specialization'])}" if d.get('specialization') else ''} · {d['total_credits']} crédits ECTS</p></div>
<dl class="id">
  <div class="wide"><dt>Nom et prénom</dt><dd class="name">{e(d['recipient_honorific'])} {e(d['recipient_name'])}</dd></div>
  <div><dt>Matricule</dt><dd>{e(d['student_id'])}</dd></div>
  <div class="wide"><dt>{e(d['recipient_born'])} le / à</dt><dd>{e(d['recipient_birth_date'])} à {e(d['recipient_birth_place'])}</dd></div>
  <div><dt>Année académique</dt><dd>{e(d['academic_year'])}</dd></div>
</dl>""")
    for lv in levels:
        rows = "".join(
            f'<tr><td class="c-code">{e(code)}</td><td>{e(title)}{f"<span class=sub>{e(sub)}</span>" if sub else ""}</td>'
            f'<td class="c-ects">{ects}</td><td class="c-note">{fr(note)}</td><td class="c-app">{e(app)}</td></tr>'
            for code, title, sub, ects, note, app in lv["modules"])
        out.append(f"""<section class="lvl"><table class="notes">
  <caption>{e(lv['title'])}<span>{e(lv['semesters'])}</span></caption>
  <thead><tr><th class="c-code">Code</th><th>Intitulé du module</th><th class="c-ects">ECTS</th><th class="c-note">Note / 20</th><th class="c-app">Appréciation</th></tr></thead>
  <tbody>{rows}</tbody>
  <tfoot><tr><td colspan="2" class="lbl">Moyenne {e(lv['title'].split('(')[-1].rstrip(')'))} · pondérée par les crédits</td>
    <td class="c-ects">{lv['acquired']}</td><td class="c-note">{fr(lv['avg'])}</td><td>Mention <b>{e(lv['mention'])}</b> · {lv['acquired']} ECTS acquis</td></tr></tfoot>
</table></section>""")
    out.append(f"""<dl class="sum">
  <div><dt>Crédits validés</dt><dd>{total['acquired']} <small>/ {total['credits']} ECTS</small></dd></div>
  <div><dt>Moyenne générale</dt><dd>{fr(total['avg'])} <small>/ 20</small></dd></div>
  <div><dt>Mention</dt><dd>{e(total['mention'])}{f"<span class=honours>{e(d['jury_honours'])}</span>" if d.get('jury_honours') else ''}</dd></div>
</dl>
<footer class="ft">
  <div class="verify">{f'<img src="{qr}" alt="QR code de vérification">' if qr else ''}<p><b>Vérification</b>{e(d['verification_url'].split('://')[-1])}</p></div>
  <div>
    <p class="place">Fait à {e(d['issue_city'])}, le {e(d['issue_date'])}</p>
    <div class="sigs">
      <div class="sig"><div class="sig-role">{e(d['director_title'])}</div><div class="sig-space"></div><div class="sig-line"></div><div class="sig-name">{e(d['director_name'])}</div></div>
      <div class="sig"><div class="sig-role">{e(d['signatory_title'])}</div><div class="sig-space"></div><div class="sig-line"></div><div class="sig-name">{e(d['signatory_name'])}</div></div>
      {f'<div class="stamp"><img src="{e(stamp)}" alt="Cachet de l’établissement"></div>' if stamp else ''}
    </div>
  </div>
</footer>
<p class="legend"><span><b>Mentions</b> Très Bien ≥ 16 · Bien 14–15,99 · Assez Bien 12–13,99 · Passable 10–11,99</span>
  <span>Moyennes pondérées par les crédits ECTS · Document délivré en un seul exemplaire · Toute rature ou surcharge l’annule</span></p>
</article>""")
    return "\n".join(out)


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
    qr = qr_svg(d["verification_url"]) if d.get("verification_url") else ""
    page = render_page(d, d["school_logo"], stamp, qr)
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
        prev.write_text(preview(render_page(d, logo, st, qr), d), encoding="utf-8")
        print("wrote", prev)


def preview(page, d):
    return f"""<title>ERPIE Relevé de Notes</title>
<meta name="claude:viewport-fit-sides" content="cover">
{FONTS}
<style>
:root {{ --desk: #e6e7e9; --chrome: #1d2125; --chrome-dim: #5d646c; color-scheme: light; }}
body {{ background: var(--desk); color: var(--chrome); font-family: 'Jost', system-ui, sans-serif; }}
.page {{ padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 18px 32px; }}
.bar {{ max-width: 900px; margin: 0 auto 14px; display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; }}
.bar h1 {{ margin: 0; font-family: 'Cormorant SC', serif; font-size: 22px; letter-spacing: .1em; }}
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
