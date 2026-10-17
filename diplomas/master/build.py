#!/usr/bin/env python3
"""Build the ERPIE master diploma.

Generates the engraved frame and security background as vector SVG, then writes:
  diploma-master.html   standalone template with {{FIELD}} tokens (print / PDF engine input)
  sample-data.json      example values for every field
  preview.html          interactive preview fragment (sample data, embedded assets)

Run:  python3 build.py            (writes next to this file)
      python3 build.py --preview-out /path/to/preview.html
"""
import base64
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
W, H = 297.0, 210.0          # A4 landscape, 1 SVG user unit = 1 mm
CX = W / 2

# ── Frame geometry (mm from page edge) ──────────────────────────────
EDGE = 2.4                   # solid green border, printed to the trimmed edge
OUTER = 3.0                  # hairline
STRUCT = 3.8                 # structural line
BAND0, BAND1 = 4.6, 12.6     # guilloche band
INNER = 13.4                 # inner structural line
CONTENT = 14.4               # inner hairline / content box
DECO = 16.4                  # concave-cornered decorative line
DECO_R = 6.0
BAND_C = (BAND0 + BAND1) / 2
MED_CY = 118.0               # centre of the security medallion (under the name)


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def polyline(points):
    it = iter(points)
    x, y = next(it)
    d = [f"M{f(x)} {f(y)}"]
    d += [f"L{f(x)} {f(y)}" for x, y in it]
    return "".join(d)


def polar(cx, cy, rfun, t0, t1, steps):
    return polyline(
        (cx + rfun(t) * math.cos(t), cy + rfun(t) * math.sin(t))
        for t in (t0 + (t1 - t0) * i / steps for i in range(steps + 1))
    )


def sector_rosette(gid, cx, cy, sym, curves, steps):
    """Guilloche with `sym`-fold symmetry: draw one sector, rotate copies."""
    span = 2 * math.pi / sym
    paths = "".join(f'<path d="{polar(cx, cy, r, 0, span, steps)}"/>' for r in curves)
    uses = "".join(
        f'<use href="#{gid}" transform="rotate({f(360 * i / sym)} {f(cx)} {f(cy)})"/>'
        for i in range(1, sym)
    )
    return f'<g id="{gid}">{paths}</g>{uses}'


def wave(axis_len, amp, freq, phase, centre, steps, horizontal=True):
    pts = []
    for i in range(steps + 1):
        s = axis_len * i / steps
        o = centre + amp * math.sin(2 * math.pi * freq * s / axis_len + phase)
        pts.append((s, o) if horizontal else (o, s))
    return polyline(pts)


def braid_band(gid, x, y, horizontal, length):
    """Rope braid along a band: one wavelength drawn once, repeated with <use>.
    Kept as plain vector copies (no SVG <pattern>), because Chrome rasterises patterns in PDF output."""
    periods = round(length / 6.0)
    lam = length / periods
    c = (BAND1 - BAND0) / 2
    main = "".join(
        f'<path d="{wave(lam, 3.05, 1, k * math.pi / 3, c, 64, horizontal)}"/>' for k in range(6)
    )
    fine = "".join(
        f'<path d="{wave(lam, 1.45, 2, k * math.pi / 2 + math.pi / 4, c, 64, horizontal)}"/>'
        for k in range(4)
    )
    tile = (
        f'<g id="{gid}"><g fill="none" stroke="var(--engrave)" stroke-width=".1">{main}</g>'
        f'<g fill="none" stroke="var(--green)" stroke-width=".06" opacity=".75">{fine}</g></g>'
    )
    uses = "".join(
        f'<use href="#{gid}" x="{f(x + i * lam if horizontal else x)}" y="{f(y if horizontal else y + i * lam)}"/>'
        for i in range(periods)
    )
    return tile, uses


def concave_rect(i, r):
    x0, y0, x1, y1 = i, i, W - i, H - i
    return (
        f"M{f(x0 + r)} {f(y0)}H{f(x1 - r)}A{f(r)} {f(r)} 0 0 0 {f(x1)} {f(y0 + r)}"
        f"V{f(y1 - r)}A{f(r)} {f(r)} 0 0 0 {f(x1 - r)} {f(y1)}"
        f"H{f(x0 + r)}A{f(r)} {f(r)} 0 0 0 {f(x0)} {f(y1 - r)}"
        f"V{f(y0 + r)}A{f(r)} {f(r)} 0 0 0 {f(x0 + r)} {f(y0)}Z"
    )


def rect(i):
    return f'<rect x="{f(i)}" y="{f(i)}" width="{f(W - 2 * i)}" height="{f(H - 2 * i)}"/>'


def lozenge(cx, cy, hw, hh):
    def poly(s):
        return f"M{f(cx)} {f(cy - hh * s)}L{f(cx + hw * s)} {f(cy)}L{f(cx)} {f(cy + hh * s)}L{f(cx - hw * s)} {f(cy)}Z"
    return (
        f'<path d="{poly(1)}" fill="var(--paper)" stroke="var(--engrave)" stroke-width=".3"/>'
        f'<path d="{poly(.7)}" fill="none" stroke="var(--engrave)" stroke-width=".12"/>'
        f'<path d="{poly(.42)}" fill="none" stroke="var(--green)" stroke-width=".1"/>'
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r=".85" fill="var(--red)"/>'
    )


def frame_svg():
    band_h = BAND1 - BAND0
    hl, vl = BAND1 * 2, BAND1 * 2
    defs = [
    ]
    tile_h, top = braid_band("braidH", BAND1, BAND0, True, W - hl)
    _, bottom = braid_band("braidH", BAND1, H - BAND1, True, W - hl)
    tile_v, left = braid_band("braidV", BAND0, BAND1, False, H - vl)
    _, right = braid_band("braidV", W - BAND1, BAND1, False, H - vl)
    defs += [tile_h, tile_v]
    # corner rosette (drawn once at origin, reused at the four band crossings)
    ros = "".join(
        f'<path d="{polar(0, 0, lambda t, k=k: 2.45 + .85 * math.sin(10 * t + k * math.pi / 5), 0, 2 * math.pi, 220)}"/>'
        for k in range(5)
    )
    defs.append(
        f'<g id="cornerRosette"><circle r="3.7" fill="var(--paper)" stroke="var(--engrave)" stroke-width=".25"/>'
        f'<circle r="3.25" fill="none" stroke="var(--engrave)" stroke-width=".08"/>'
        f'<g fill="none" stroke="var(--green)" stroke-width=".07">{ros}</g>'
        f'<circle r=".75" fill="var(--red)"/></g>'
    )
    # inner corner ornament, authored for the top-left corner and mirrored
    d0, r = DECO, DECO_R
    ornament = (
        f'<g fill="none" stroke="var(--engrave)">'
        f'<path stroke-width=".14" d="M{f(d0 + 3.6)} {f(d0)}A3.6 3.6 0 0 1 {f(d0)} {f(d0 + 3.6)}"/>'
        f'<path stroke-width=".1" d="M{f(d0 + 4.6)} {f(d0)}A4.6 4.6 0 0 1 {f(d0)} {f(d0 + 4.6)}"/>'
        # scrolls along the top edge and down the left edge
        f'<path stroke-width=".22" d="M{f(d0 + r)} {f(d0)}C{f(d0 + r + 2.6)} {f(d0 + 3)},{f(d0 + r + 6.8)} {f(d0 + 3.3)},{f(d0 + r + 9.4)} {f(d0 + 1.7)}'
        f'C{f(d0 + r + 11.4)} {f(d0 + .4)},{f(d0 + r + 13.6)} {f(d0 + 1.1)},{f(d0 + r + 14.1)} {f(d0 + 2.5)}'
        f'C{f(d0 + r + 14.5)} {f(d0 + 3.6)},{f(d0 + r + 13.2)} {f(d0 + 4.1)},{f(d0 + r + 12.6)} {f(d0 + 3.2)}"/>'
        f'<path stroke-width=".22" d="M{f(d0)} {f(d0 + r)}C{f(d0 + 3)} {f(d0 + r + 2.6)},{f(d0 + 3.3)} {f(d0 + r + 6.8)},{f(d0 + 1.7)} {f(d0 + r + 9.4)}'
        f'C{f(d0 + .4)} {f(d0 + r + 11.4)},{f(d0 + 1.1)} {f(d0 + r + 13.6)},{f(d0 + 2.5)} {f(d0 + r + 14.1)}'
        f'C{f(d0 + 3.6)} {f(d0 + r + 14.5)},{f(d0 + 4.1)} {f(d0 + r + 13.2)},{f(d0 + 3.2)} {f(d0 + r + 12.6)}"/>'
        f'<path stroke-width=".1" d="M{f(d0 + r + 1.2)} {f(d0 + .2)}C{f(d0 + r + 4)} {f(d0 + 1.9)},{f(d0 + r + 7)} {f(d0 + 1.6)},{f(d0 + r + 9)} {f(d0 + .4)}"/>'
        f'<path stroke-width=".1" d="M{f(d0 + .2)} {f(d0 + r + 1.2)}C{f(d0 + 1.9)} {f(d0 + r + 4)},{f(d0 + 1.6)} {f(d0 + r + 7)},{f(d0 + .4)} {f(d0 + r + 9)}"/>'
        f"</g>"
        # lozenge with a fine ring in the corner pocket
        + f'<circle cx="{f(d0 + 1.75)}" cy="{f(d0 + 1.75)}" r="1.5" fill="none" stroke="var(--engrave)" stroke-width=".1"/>'
        + f'<path d="M{f(d0 + 1.75)} {f(d0 + .75)}l1 1-1 1-1-1z" fill="var(--red)"/>'
    )
    defs.append(f'<g id="cornerOrnament">{ornament}</g>')

    corners = [(BAND_C, BAND_C), (W - BAND_C, BAND_C), (BAND_C, H - BAND_C), (W - BAND_C, H - BAND_C)]
    mirrors = ["", f"translate({f(W)} 0) scale(-1 1)", f"translate(0 {f(H)}) scale(1 -1)",
               f"translate({f(W)} {f(H)}) scale(-1 -1)"]
    body = [
        f'<path fill="var(--engrave)" fill-rule="evenodd" d="M0 0H{f(W)}V{f(H)}H0Z'
        f'M{f(EDGE)} {f(EDGE)}V{f(H - EDGE)}H{f(W - EDGE)}V{f(EDGE)}Z"/>'
        f'<path fill="none" stroke="var(--green)" stroke-width=".12" d="M{f(EDGE / 2)} {f(EDGE / 2)}H{f(W - EDGE / 2)}V{f(H - EDGE / 2)}H{f(EDGE / 2)}Z" opacity=".8"/>'
        f'<g fill="none" stroke="var(--engrave)">'
        f'<g stroke-width=".18">{rect(OUTER)}</g>'
        f'<g stroke-width=".45">{rect(STRUCT)}{rect(INNER)}</g>'
        f'<g stroke-width=".15">{rect(CONTENT)}</g>'
        f"</g>",
        top, bottom, left, right,
        # band edge hairlines
        f'<g fill="none" stroke="var(--engrave)" stroke-width=".1">{rect(BAND0)}{rect(BAND1)}</g>',
        f'<path d="{concave_rect(DECO, DECO_R)}" fill="none" stroke="var(--engrave)" stroke-width=".22"/>',
        f'<path d="{concave_rect(DECO + .8, DECO_R + .8)}" fill="none" stroke="var(--red)" stroke-width=".1" opacity=".7"/>',
    ]
    body += [f'<use href="#cornerRosette" transform="translate({f(x)} {f(y)})"/>' for x, y in corners]
    body += [f'<use href="#cornerOrnament" transform="{m}"/>' for m in mirrors]
    body += [
        lozenge(CX, BAND_C, 6.2, 4.2), lozenge(CX, H - BAND_C, 6.2, 4.2),
        lozenge(BAND_C, H / 2, 4.2, 6.2), lozenge(W - BAND_C, H / 2, 4.2, 6.2),
    ]
    return (
        f'<svg class="layer frame" viewBox="0 0 {f(W)} {f(H)}" aria-hidden="true">'
        f'<defs>{"".join(defs)}</defs>{"".join(body)}</svg>'
    )


MICRO_MEDALLION = "ERPIE · DIPLÔME AUTHENTIQUE · AUTHENTIC ACADEMIC CREDENTIAL · "


def ring_text(pid, cx, cy, r, text, size, repeat):
    circ = 2 * math.pi * r
    return (
        f'<path id="{pid}" fill="none" d="M{f(cx - r)} {f(cy)}a{f(r)} {f(r)} 0 1 1 {f(2 * r)} 0a{f(r)} {f(r)} 0 1 1 {f(-2 * r)} 0"/>'
        f'<text font-size="{f(size)}" class="micro"><textPath href="#{pid}" textLength="{f(circ - .6)}" '
        f'lengthAdjust="spacing">{text * repeat}</textPath></text>'
    )


def background_svg(emblem_href):
    cx, cy = CX, MED_CY
    rings = [(8, .12), (12, .2), (20.4, .12), (21.2, .3), (34.4, .12), (36, .25), (44, .1),
             (45.3, .2), (60.6, .15), (63.9, .15), (66.2, .3), (72, .1), (76.5, .2), (80, .08)]
    band = sector_rosette(
        "gRing", cx, cy, 24,
        [lambda t, k=k: 52.6 + 5.6 * math.sin(24 * t + k * math.pi / 3) for k in range(6)], 90)
    rosette = sector_rosette(
        "gRose", cx, cy, 12,
        [lambda t, k=k: 27.6 + 5.2 * math.sin(12 * t + k * math.pi / 8) + 1.4 * math.sin(36 * t + k * math.pi / 4)
         for k in range(8)], 140)
    outer = sector_rosette(
        "gOuter", cx, cy, 60,
        [lambda t, k=k: 69.1 + 1.25 * math.sin(60 * t + k * 2 * math.pi / 3) for k in range(3)], 24)
    defs = (
        f'<image id="emblemMark" href="{emblem_href}" width="8" height="6"/>'
        f'<clipPath id="contentClip"><path d="{concave_rect(DECO, DECO_R)}"/></clipPath>'
    )
    cw = W - 2 * DECO
    ch = H - 2 * DECO
    return (
        f'<svg class="layer security" viewBox="0 0 {f(W)} {f(H)}" aria-hidden="true">'
        f"<defs>{defs}</defs>"
        f'<g clip-path="url(#contentClip)">'
        f'<g opacity=".028">'
        + "".join(f'<use href="#emblemMark" x="{f(x)}" y="{f(y)}"/>'
                  for row in range(8) for col in range(9)
                  for x, y in [(11 + 34 * col + (17 if row % 2 else 0), 6 + 13 * row)]
                  if DECO - 8 < x < W - DECO and DECO - 6 < y < H - DECO)
        + "</g>"
        f'<g class="medallion">'
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r="16.6" fill="none" stroke="var(--green)" stroke-width="8.4" '
        f'stroke-dasharray=".06 .3" opacity=".7"/>'
        f'<circle cx="{f(cx)}" cy="{f(cy)}" r="68.3" fill="none" stroke="var(--green)" stroke-width="3.6" '
        f'stroke-dasharray=".05 .42" opacity=".5"/>'
        f'<g fill="none" stroke="var(--green)">'
        + "".join(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" stroke-width="{f(w)}"/>' for r, w in rings)
        + f'</g><g fill="none" stroke="var(--green)" stroke-width=".1">{band}</g>'
        f'<g fill="none" stroke="var(--engrave)" stroke-width=".09">{rosette}</g>'
        f'<g fill="none" stroke="var(--green)" stroke-width=".08">{outer}</g>'
        + ring_text("mtMed", cx, cy, 62.15, MICRO_MEDALLION, 1.25, 7)
        + f'<image href="{emblem_href}" x="{f(cx - 13)}" y="{f(cy - 9.8)}" width="26" height="19.6" opacity=".14"/>'
        "</g>" + laurel_svg(cx, 123, 30) + "</g></svg>"
    )


def laurel_svg(cx, cy, r):
    """Engraved laurel wreath: two branches of paired leaves rising from a knot at the bottom."""
    leaf = (
        '<g id="leaf"><path d="M0 0C2.1 -1.75 5 -1.85 7 0C5 1.85 2.1 1.75 0 0Z"/>'
        '<path d="M.4 0H6.2" stroke-width=".06"/></g>'
    )
    leaves, n = [], 17
    for i in range(n):
        a = math.radians(102 + i * (252 - 102) / (n - 1))
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        tan = math.degrees(math.atan2(math.cos(a), -math.sin(a)))
        k = 1.3 - .6 * i / (n - 1)
        for off, d in ((30, 1.7), (-30, -1.7)):
            ox, oy = px + d * math.cos(a), py + d * math.sin(a)
            leaves.append(f'<use href="#leaf" transform="translate({f(ox)} {f(oy)}) rotate({f(tan + off)}) scale({f(k)})"/>')
    tip_a = math.radians(255)
    tx, ty = cx + r * math.cos(tip_a), cy + r * math.sin(tip_a)
    leaves.append(f'<use href="#leaf" transform="translate({f(tx)} {f(ty)}) rotate({f(math.degrees(math.atan2(math.cos(tip_a), -math.sin(tip_a))))}) scale(.85)"/>')
    stem = polyline((cx + r * math.cos(math.radians(t)), cy + r * math.sin(math.radians(t)))
                    for t in [98 + j * 1.5 for j in range(104)])
    branch = f'<g id="laurelBranch"><path d="{stem}" stroke-width=".5"/>{"".join(leaves)}</g>'
    by = cy + r + .6
    bow = (
        f'<path stroke-width=".22" d="M{f(cx)} {f(by)}c-2.2 -2.6 -6.2 -2.2 -5.2 .2c.8 1.8 3.6 .9 5.2 -.2'
        f'c2.2 -2.6 6.2 -2.2 5.2 .2c-.8 1.8 -3.6 .9 -5.2 -.2"/>'
        f'<path stroke-width=".22" d="M{f(cx - .3)} {f(by + .3)}l-2.6 4.2l1.3 -.3l.5 1.1M{f(cx + .3)} {f(by + .3)}l2.6 4.2l-1.3 -.3l-.5 1.1"/>'
        f'<circle cx="{f(cx)}" cy="{f(by)}" r=".9" stroke-width=".22"/>'
    )
    return (
        f'<g class="laurel" fill="var(--green)" fill-opacity=".22" stroke="var(--engrave)" stroke-width=".16"><defs>{leaf}</defs>'
        f'{branch}<use href="#laurelBranch" transform="translate({f(2 * cx)} 0) scale(-1 1)"/>{bow}</g>'
    )


def rule_svg(width, flip=False):
    """Hairline ending in a lozenge, used either side of the recipient name."""
    t = ' transform="scale(-1 1)" transform-origin="center"' if flip else ""
    return (
        f'<svg class="name-rule" viewBox="0 0 {width} 4" aria-hidden="true"><g{t}>'
        f'<path d="M0 2H{width - 4}" stroke="var(--engrave)" stroke-width=".18"/>'
        f'<path d="M3 2.9H{width - 5}" stroke="var(--green)" stroke-width=".08"/>'
        f'<path d="M{width - 3.2} 2l1.2-1.2 1.2 1.2-1.2 1.2z" fill="var(--red)"/>'
        f'<circle cx="{width - .4}" cy="2" r=".35" fill="var(--engrave)"/></g></svg>'
    )


TITLE_RULE = (
    '<svg class="title-rule" viewBox="0 0 80 4" aria-hidden="true">'
    '<path d="M2 2H34M46 2H78" stroke="var(--engrave)" stroke-width=".18"/>'
    '<path d="M10 2.75H32M48 2.75H70" stroke="var(--green)" stroke-width=".08"/>'
    '<path d="M40 .4l1.6 1.6-1.6 1.6-1.6-1.6z" fill="var(--red)"/>'
    '<path d="M36.2 2l1.1-1.1 1.1 1.1-1.1 1.1zM41.6 2l1.1-1.1 1.1 1.1-1.1 1.1z" fill="none" stroke="var(--engrave)" stroke-width=".14"/>'
    '<circle cx="1.4" cy="2" r=".4" fill="var(--engrave)"/><circle cx="78.6" cy="2" r=".4" fill="var(--engrave)"/>'
    "</svg>"
)

# ── Fields ──────────────────────────────────────────────────────────
SAMPLE = {
    "SCHOOL_LOGO": "assets/erpie-logo.webp",
    "COUNTRY": "République du Mali",
    "MOTTO": "Un Peuple – Un But – Une Foi",
    "STATE_EMBLEM": "assets/mali-armoiries.png",
    "AUTHORITY": "Ministère de l’Enseignement Supérieur et de la Recherche Scientifique",
    "SCHOOL_NAME": "École Rationnelle Privée d’Informatique et d’Électronique",
    "SCHOOL_STATUS": "",
    "CERTIFICATE_NUMBER": "00000001",
    "SERIAL_NUMBER": "A-2026",
    "DOCUMENT_TITLE": "Diplôme",
    "QUALIFICATION": "de Master",
    "DECREE_CREATION": "N° 2018-0001575/MESRS-SG du 3 septembre 2018",
    "DECREE_OPENING": "N° 2022-4383/MESRS-SG du 21 septembre 2022",
    "DECREE_HABILITATION": "N° 2024-3794/MESRS-SG du 8 octobre 2024",
    "RECIPIENT_HONORIFIC": "M.",
    "RECIPIENT_NAME": "Aboubacar Togola",
    "RECIPIENT_BORN": "né",
    "RECIPIENT_REF": "l’intéressé",
    "RECIPIENT_BIRTH_DATE": "15 juillet 1997",
    "RECIPIENT_BIRTH_PLACE": "Bamako",
    "DEGREE": "Master",
    "PROGRAM_NAME": "Génie Logiciel",
    "SPECIALIZATION": "Transformation numérique",
    "ACADEMIC_YEAR": "2020 – 2022",
    "DISTINCTION": "Très Bien",
    "ISSUE_CITY": "Bamako",
    "ISSUE_DATE": "16 novembre 2024",
    "DIRECTOR_TITLE": "Le Directeur des Études",
    "DIRECTOR_NAME": "Dr Sekou TANGARA",
    "AUTHORIZED_SIGNATORY_TITLE": "Le Directeur Général",
    "AUTHORIZED_SIGNATORY_NAME": "Ing. Lassana SISSOKO",
    "DIRECTOR_SIGNATURE": "",
    "AUTHORIZED_SIGNATORY_SIGNATURE": "",
    "SCHOOL_STAMP": "assets/erpie-cachet.webp",
}
IMAGE_FIELDS = {"SCHOOL_LOGO", "STATE_EMBLEM", "SCHOOL_STAMP", "DIRECTOR_SIGNATURE", "AUTHORIZED_SIGNATORY_SIGNATURE"}
OPTIONAL = {"AUTHORITY", "MOTTO", "STATE_EMBLEM", "SCHOOL_STATUS", "SERIAL_NUMBER", "RECIPIENT_HONORIFIC", "SPECIALIZATION", "DISTINCTION",
            "SCHOOL_STAMP", "DIRECTOR_SIGNATURE", "AUTHORIZED_SIGNATORY_SIGNATURE"}


def t(key):
    return f'<span data-field="{key}">{{{{{key}}}}}</span>'


def opt(key):
    return f' data-optional="{key}"' if key in OPTIONAL else ""


def diploma_markup(emblem_href):
    sigs = [("DIRECTOR_TITLE", "DIRECTOR_NAME", "DIRECTOR_SIGNATURE"),
            ("AUTHORIZED_SIGNATORY_TITLE", "AUTHORIZED_SIGNATORY_NAME", "AUTHORIZED_SIGNATORY_SIGNATURE")]
    return f"""<article class="diploma" id="diploma" lang="fr" aria-label="Diplôme">
{background_svg(emblem_href)}
{frame_svg()}

<header class="z z-school">
  <img class="school-logo" data-field="SCHOOL_LOGO" src="{{{{SCHOOL_LOGO}}}}" alt="Logo de l’établissement">
  <div class="school-name">{t("SCHOOL_NAME")}</div>
  <div class="school-status"{opt("SCHOOL_STATUS")}>{t("SCHOOL_STATUS")}</div>
</header>

<header class="z z-state">
  <img class="state-emblem" data-field="STATE_EMBLEM" data-optional="STATE_EMBLEM" src="{{{{STATE_EMBLEM}}}}" alt="Armoiries">
  <div class="inst-country">{t("COUNTRY")}</div>
  <div class="inst-motto"{opt("MOTTO")}>{t("MOTTO")}</div>
  <svg class="inst-rule" viewBox="0 0 24 2" aria-hidden="true"><path d="M0 1H10M14 1H24" stroke="var(--engrave)" stroke-width=".15"/><path d="M12 .2l.8.8-.8.8-.8-.8z" fill="var(--red)"/></svg>
  <div class="inst-authority"{opt("AUTHORITY")}>{t("AUTHORITY")}</div>
</header>

<div class="z z-number">
  <div class="cert-no"><span class="no-mark">N°</span> {t("CERTIFICATE_NUMBER")}</div>
  <div class="serial"{opt("SERIAL_NUMBER")}>Série {t("SERIAL_NUMBER")}</div>
</div>

<section class="z z-title">
  <h1 class="doc-title">{t("DOCUMENT_TITLE")}</h1>
  {TITLE_RULE}
  <div class="qualification">{t("QUALIFICATION")}</div>
</section>

<section class="z z-visas">
  <ul class="visas">
    <li>Vu la décision de création <span class="ref">{t("DECREE_CREATION")}</span> ;</li>
    <li>Vu l’arrêté d’ouverture <span class="ref">{t("DECREE_OPENING")}</span> ;</li>
    <li>Vu l’arrêté d’habilitation <span class="ref">{t("DECREE_HABILITATION")}</span> ;</li>
    <li>Vu les pièces justificatives produites par <span{opt("RECIPIENT_HONORIFIC")}>{t("RECIPIENT_HONORIFIC")} </span><span class="ref sc">{t("RECIPIENT_NAME")}</span>,
      {t("RECIPIENT_BORN")} le <span class="ref">{t("RECIPIENT_BIRTH_DATE")}</span> à <span class="ref">{t("RECIPIENT_BIRTH_PLACE")}</span>, en vue de son inscription à la formation ;</li>
    <li>Vu les procès-verbaux du jury attestant que {t("RECIPIENT_REF")} a satisfait au contrôle des connaissances et des aptitudes prévu par les textes réglementaires ;</li>
  </ul>
</section>

<section class="z z-deliver">
  <p class="deliver-lead">Le diplôme de <b>{t("DEGREE")}</b> en <b>{t("PROGRAM_NAME")}</b><span{opt("SPECIALIZATION")}>, parcours <b>{t("SPECIALIZATION")}</b></span>, est délivré à</p>
  <div class="name-row">
    {rule_svg(30, flip=True)}
    <div class="recipient" id="recipient"><span class="honorific"{opt("RECIPIENT_HONORIFIC")}>{t("RECIPIENT_HONORIFIC")}</span> <span class="recipient-name">{t("RECIPIENT_NAME")}</span></div>
    {rule_svg(30)}
  </div>
  <p class="deliver-year">au titre de l’année universitaire {t("ACADEMIC_YEAR")}</p>
  <p class="mention"{opt("DISTINCTION")}><span class="mention-label">Mention</span> {t("DISTINCTION")}</p>
  <p class="deliver-close">pour en jouir avec les droits et prérogatives qui y sont attachés.</p>
</section>

<p class="z z-place">Fait à {t("ISSUE_CITY")}, le {t("ISSUE_DATE")}</p>

<section class="z z-sigs">
  <div class="sig">
    <div class="sig-role">Le titulaire</div>
    <div class="sig-space"></div>
    <div class="sig-line"></div>
    <div class="sig-name sig-name--holder">&nbsp;</div>
  </div>
{"".join(f'''  <div class="sig">
    <div class="sig-role">{t(role)}</div>
    <div class="sig-space"><img class="sig-img" data-field="{sign}" data-optional="{sign}" src="{{{{{sign}}}}}" alt=""></div>
    <div class="sig-line"></div>
    <div class="sig-name">{t(name)}</div>
  </div>
''' for role, name, sign in sigs)}</section>

<div class="z z-stamp"{opt("SCHOOL_STAMP")}><img data-field="SCHOOL_STAMP" src="{{{{SCHOOL_STAMP}}}}" alt="Cachet de l’établissement"></div>
</article>"""


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,400;1,500;1,600'
         '&family=Cormorant+SC:wght@500;600&family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Jost:wght@400;500&display=swap">')

DIPLOMA_CSS = """
/* Grid: 297 × 210 mm full bleed, centre axis 148.5 mm; frame bands to 16.4 mm; every zone is placed in mm. */
.diploma {
  --paper: #fdfdf9; --ink: #0e1a12; --ink-soft: #22342a; --muted: #3c4d42;
  --green: #0b8a3e; --engrave: #0c5530; --red: #a5171b;
  --f-display: 'Cormorant SC', 'Cormorant Garamond', Garamond, 'Times New Roman', serif;
  --f-serif: 'Cormorant Garamond', Garamond, 'Times New Roman', serif;
  --f-body: 'EB Garamond', Garamond, 'Times New Roman', serif;
  --f-meta: 'Jost', 'Futura', 'Century Gothic', 'Helvetica Neue', Arial, sans-serif;
  position: relative; width: 297mm; height: 210mm; overflow: hidden; box-sizing: border-box;
  background: var(--paper);
  color: var(--ink); font-family: var(--f-body); font-size: 3mm; line-height: 1.35;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
  font-kerning: normal; text-rendering: geometricPrecision;
}
.diploma *, .diploma *::before, .diploma *::after { box-sizing: border-box; }
.diploma p, .diploma h1, .diploma dl, .diploma dd { margin: 0; }
.diploma .layer { position: absolute; inset: 0; width: 297mm; height: 210mm; }
.diploma .micro { font-family: var(--f-meta); font-weight: 500; fill: var(--engrave); letter-spacing: .02em; }
.diploma .medallion { opacity: .11; }
.diploma .laurel { opacity: .2; }
.diploma .z { position: absolute; }
.diploma [data-hidden] { display: none !important; }

/* Header: the school on the left, the State on the right, the title between them. */
.z-school { left: 22mm; width: 82mm; top: 19mm; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 1.6mm; }
.school-logo { display: block; width: 44mm; height: 20mm; object-fit: contain; }
.school-name { font-family: var(--f-display); font-weight: 700; font-size: 4.6mm; line-height: 1.15; letter-spacing: .03em; color: var(--red); text-wrap: balance; }
.school-status { font-family: var(--f-meta); font-size: 2mm; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }

.z-state { left: 193mm; width: 82mm; top: 19mm; display: flex; flex-direction: column; align-items: center; text-align: center; gap: .9mm; }
.state-emblem { display: block; width: 14mm; height: 14mm; object-fit: contain; margin-bottom: .4mm; }
.inst-country { font-family: var(--f-display); font-weight: 700; font-size: 4.6mm; letter-spacing: .14em; margin-right: -.14em; line-height: 1.1; color: var(--ink); }
.inst-motto { font-family: var(--f-serif); font-style: italic; font-weight: 600; font-size: 3.5mm; line-height: 1.1; color: var(--ink-soft); }
.inst-rule { width: 24mm; height: 2mm; display: block; }
.inst-authority { font-family: var(--f-serif); font-style: italic; font-weight: 500; font-size: 3.2mm; line-height: 1.2; color: var(--ink-soft); text-wrap: balance; }

/* Registration number, bottom left as on French national diplomas. */
.z-number { left: 26mm; top: 180.5mm; text-align: left; font-family: var(--f-meta); color: var(--ink); }
.cert-no { font-size: 2.9mm; font-weight: 500; letter-spacing: .12em; font-variant-numeric: tabular-nums; }
.no-mark { color: var(--red); letter-spacing: .04em; }
.serial { font-size: 1.9mm; letter-spacing: .18em; text-transform: uppercase; color: var(--muted); margin-top: .5mm; }

.z-title { left: 48.5mm; width: 200mm; top: 55mm; text-align: center; display: flex; flex-direction: column; align-items: center; }
.doc-title { font-family: var(--f-display); font-weight: 600; font-size: 12.5mm; line-height: .95; letter-spacing: .16em; margin-right: -.16em;
  color: var(--engrave); }
.title-rule { width: 58mm; height: 3mm; display: block; margin: 1.1mm 0 .6mm; }
.qualification { font-family: var(--f-serif); font-style: italic; font-weight: 600; font-size: 8mm; line-height: 1.1; color: var(--green); }

.z-visas { left: 18.5mm; width: 260mm; top: 83mm; display: flex; justify-content: center; }
.visas { list-style: none; margin: 0; padding: 0; font-size: 3.45mm; line-height: 1.42; color: var(--ink-soft); text-align: left; }
.visas .ref { font-weight: 500; color: var(--ink); white-space: nowrap; font-variant-numeric: lining-nums; }
.visas .sc { font-variant: small-caps; letter-spacing: .03em; }

.z-deliver { left: 23.5mm; width: 250mm; top: 109.6mm; text-align: center; display: flex; flex-direction: column; align-items: center; }
.deliver-lead { font-size: 4.5mm; line-height: 1.3; color: var(--ink); }
.deliver-lead b { font-family: var(--f-serif); font-weight: 700; font-size: 5.6mm; color: var(--engrave); letter-spacing: .01em; }
.name-row { width: 100%; height: 16mm; display: flex; align-items: center; justify-content: center; gap: 4mm; margin-top: .4mm; }
.name-rule { width: 30mm; height: 4mm; flex: none; display: block; }
.recipient { max-width: 178mm; white-space: nowrap; text-align: center; color: var(--ink); line-height: 1; }
.honorific { font-family: var(--f-serif); font-style: italic; font-weight: 600; font-size: 6.6mm; color: var(--green); margin-right: 1.4mm; }
.recipient-name { font-family: var(--f-display); font-weight: 600; font-size: 11mm; letter-spacing: .06em; }
.deliver-year { font-size: 4.1mm; color: var(--ink); margin-top: .4mm !important; }
.mention { margin-top: 1.4mm !important; font-family: var(--f-meta); font-size: 3.2mm; font-weight: 500; letter-spacing: .16em; text-transform: uppercase; color: var(--red); }
.mention-label { color: var(--ink-soft); font-weight: 500; margin-right: 1.2mm; }
.mention-label::after { content: " ·"; color: var(--red); }
.deliver-close { margin-top: 1.4mm !important; font-style: italic; font-size: 3.9mm; color: var(--ink-soft); }

.z-place { left: 63mm; top: 152.6mm; text-align: left; font-style: italic; font-size: 3.9mm; color: var(--ink-soft); white-space: nowrap; }

.z-sigs { left: 55.5mm; width: 186mm; top: 159mm; display: grid; grid-template-columns: repeat(3, 58mm); column-gap: 6mm; }
.sig { display: flex; flex-direction: column; align-items: center; text-align: center; min-width: 0; }
.sig-role { font-family: var(--f-meta); font-weight: 500; font-size: 2.8mm; letter-spacing: .12em; text-transform: uppercase; color: var(--engrave); line-height: 1.3; min-height: 3.6mm; }
.sig-space { height: 15mm; width: 100%; position: relative; }
.sig-img { position: absolute; left: 50%; bottom: -2mm; transform: translateX(-50%); max-width: 44mm; max-height: 19mm; object-fit: contain; }
/* School stamp, inked over the right half of the Director General block: "GÉNÉRAL" and the surname stay under it, the left half stays free to sign. */
.z-stamp { left: 212mm; top: 154mm; width: 37mm; height: 37mm; transform: rotate(-11deg); opacity: .93; pointer-events: none; }
.z-stamp img { display: block; width: 100%; height: 100%; }
.sig-line { width: 48mm; border-top: .2mm solid var(--ink-soft); }
.sig-name { margin-top: 1.3mm; font-family: var(--f-body); font-weight: 500; font-size: 3.9mm; letter-spacing: .02em; color: var(--ink); white-space: nowrap; }
"""

FILL_JS = r"""
/* Fill the template from a data object: ERPIE_DIPLOMA.fill({RECIPIENT_NAME: "…", …}).
   Text fields replace their {{TOKEN}}; image fields take a URL; empty optional fields hide their row. */
(function () {
  function fitName(root) {
    var el = root.querySelector('.recipient-name'); var box = root.querySelector('.recipient');
    if (!el || !box) return;
    el.style.fontSize = '';
    var size = parseFloat(getComputedStyle(el).fontSize), max = box.parentElement.clientWidth * 0.7;
    while (box.scrollWidth > max && size > 18) { size -= 0.5; el.style.fontSize = size + 'px'; }
  }
  function fill(data, root) {
    root = root || document.getElementById('diploma');
    root.querySelectorAll('[data-field]').forEach(function (node) {
      var key = node.getAttribute('data-field'), v = data[key];
      if (v === undefined) return;
      if (node.tagName === 'IMG') {
        if (v) node.src = v;
      } else { node.textContent = v; }
    });
    root.querySelectorAll('[data-optional]').forEach(function (node) {
      var v = data[node.getAttribute('data-optional')];
      if (v === undefined) return;
      if (v === '') node.setAttribute('data-hidden', ''); else node.removeAttribute('data-hidden');
    });
    fitName(root);
  }
  window.ERPIE_DIPLOMA = { fill: fill, fitName: fitName };
  if (window.DIPLOMA_DATA) document.addEventListener('DOMContentLoaded', function () { fill(window.DIPLOMA_DATA); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { var d = document.getElementById('diploma'); if (d) fitName(d); });
})();
"""


def template_html():
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ERPIE · Diplôme — modèle maître</title>
{FONTS}
<style>
@page {{ size: 297mm 210mm; margin: 0; }}
html, body {{ margin: 0; padding: 0; background: #e9ece6; }}
@media screen {{ body {{ padding: 10mm; }} .diploma {{ margin: 0 auto; box-shadow: 0 2mm 8mm rgba(0,0,0,.18); }} }}
@media print {{ html, body {{ background: none; }} }}
{DIPLOMA_CSS}
</style>
</head>
<body>
<!--
  Fields: replace every {{{{FIELD}}}} token server-side, or call ERPIE_DIPLOMA.fill(data) in the page.
  SCHOOL_LOGO takes a URL or data: URI.
  Optional fields hide their row when set to "": {", ".join(sorted(OPTIONAL))}.
  See README.md and sample-data.json.
-->
{diploma_markup("assets/erpie-emblem.webp")}
<script>{FILL_JS}</script>
</body>
</html>
"""


def data_uri(path, mime):
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


PREVIEW_CSS = """
:root { --desk: #18201b; --desk-2: #222c25; --chrome: #e8eee9; --chrome-dim: #9fb0a5; --line: #34413a; --accent: #3fbf73; --red: #d2454a; color-scheme: dark; }
body { background: var(--desk); color: var(--chrome); font-family: 'Jost', system-ui, sans-serif; }
.page { padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 14px 32px; }
.bar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px 20px; margin-bottom: 16px; }
.bar h1 { margin: 0; font-family: 'Cormorant SC', serif; font-weight: 600; font-size: 22px; letter-spacing: .12em; line-height: 1.1; }
.bar h1 small { display: block; font-family: 'Jost', sans-serif; font-weight: 400; font-size: 11px; letter-spacing: .2em; text-transform: uppercase; color: var(--chrome-dim); margin-top: 4px; }
.controls { display: flex; flex-wrap: wrap; gap: 10px; }
.seg { display: inline-flex; border: 1px solid var(--line); border-radius: 999px; padding: 3px; background: var(--desk-2); }
.seg button { appearance: none; border: 0; background: none; color: var(--chrome-dim); font: 500 12px/1 'Jost', sans-serif; letter-spacing: .08em; text-transform: uppercase; padding: 8px 13px; border-radius: 999px; cursor: pointer; }
.seg button[aria-pressed="true"] { background: var(--chrome); color: var(--desk); }
.seg button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.viewport { overflow: auto; padding: 0; }
.sheet { position: relative; margin: 0 auto; }
.sheet .diploma { position: absolute; top: 0; left: 0; transform-origin: 0 0; }
.hint { color: var(--chrome-dim); font-size: 12px; letter-spacing: .04em; margin: 10px 2px 0; }
details { margin-top: 22px; border-top: 1px solid var(--line); padding-top: 14px; }
summary { cursor: pointer; font-size: 12px; letter-spacing: .2em; text-transform: uppercase; color: var(--chrome-dim); }
summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.fields { overflow-x: auto; margin-top: 12px; }
.fields table { border-collapse: collapse; width: 100%; font-size: 13px; }
.fields th, .fields td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
.fields th { font-weight: 500; font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--chrome-dim); }
.fields code { font-family: ui-monospace, 'SFMono-Regular', Menlo, monospace; font-size: 12px; color: var(--accent); white-space: nowrap; }
.fields .opt { color: var(--chrome-dim); font-size: 11px; }
/* variable mode: outline every live field */
.show-vars [data-field], .show-vars [data-optional] { outline: .25mm dashed rgba(165,23,27,.75); outline-offset: .3mm; }
.show-vars img[data-field] { background: rgba(165,23,27,.06); }
.show-grid .grid-overlay { display: block; }
.grid-overlay { display: none; position: absolute; inset: 0; width: 297mm; height: 210mm; pointer-events: none; }
@media (prefers-reduced-motion: no-preference) { .sheet { transition: width .25s ease, height .25s ease; } }
"""

GRID_OVERLAY = (
    '<svg class="grid-overlay" viewBox="0 0 297 210" aria-hidden="true"><g fill="none" stroke="#e0218a" stroke-width=".2">'
    '<path d="M148.5 14.4V195.6" stroke-dasharray="1 1"/><path d="M14.4 104H282.6" stroke-dasharray="1 1"/>'
    '<rect x="22" y="21" width="82" height="36"/><rect x="193" y="20" width="82" height="40"/>'
    '<rect x="48.5" y="41" width="200" height="26"/><rect x="18.5" y="70" width="260" height="25"/>'
    '<rect x="23.5" y="97.4" width="250" height="41"/><rect x="171.5" y="141.6" width="70" height="5"/>'
    '<rect x="55.5" y="151.5" width="58" height="26"/><rect x="119.5" y="151.5" width="58" height="26"/>'
    '<rect x="183.5" y="151.5" width="58" height="26"/></g></svg>'
)


BLANK = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="


def preview_html():
    assets = HERE / "assets"
    emblem = data_uri(assets / "erpie-emblem.webp", "image/webp")
    sample = dict(SAMPLE)
    sample["SCHOOL_LOGO"] = data_uri(assets / "erpie-logo.webp", "image/webp")
    sample["SCHOOL_STAMP"] = data_uri(assets / "erpie-cachet.webp", "image/webp")
    sample["STATE_EMBLEM"] = data_uri(assets / "mali-armoiries.png", "image/png")
    markup = (diploma_markup(emblem).replace("</article>", GRID_OVERLAY + "</article>", 1)
              .replace('src="{{SCHOOL_LOGO}}"', f'src="{sample["SCHOOL_LOGO"]}"')
              .replace('src="{{SCHOOL_STAMP}}"', f'src="{sample["SCHOOL_STAMP"]}"')
              .replace('src="{{STATE_EMBLEM}}"', f'src="{sample["STATE_EMBLEM"]}"')
              .replace('src="{{DIRECTOR_SIGNATURE}}"', f'src="{BLANK}"')
              .replace('src="{{AUTHORIZED_SIGNATORY_SIGNATURE}}"', f'src="{BLANK}"'))
    rows = "".join(
        f'<tr><td><code>{{{{{k}}}}}</code>{" <span class=opt>optionnel</span>" if k in OPTIONAL else ""}</td>'
        f'<td>{"image (URL ou data:)" if k in IMAGE_FIELDS else (v or "—")}</td></tr>'
        for k, v in SAMPLE.items()
    )
    return f"""<title>ERPIE Master Diploma</title>
<meta name="claude:viewport-fit-sides" content="cover">
{FONTS}
<style>{PREVIEW_CSS}{DIPLOMA_CSS}</style>
<div class="page">
  <div class="bar">
    <h1>ERPIE · Diplôme de Master<small>Modèle maître · A4 paysage 297 × 210 mm</small></h1>
    <div class="controls">
      <div class="seg" role="group" aria-label="Contenu">
        <button id="mode-sample" type="button" aria-pressed="true">Exemple</button>
        <button id="mode-vars" type="button" aria-pressed="false">Variables</button>
      </div>
      <div class="seg" role="group" aria-label="Zoom">
        <button id="zoom-fit" type="button" aria-pressed="true">Ajuster</button>
        <button id="zoom-1" type="button" aria-pressed="false">100 %</button>
        <button id="zoom-3" type="button" aria-pressed="false">300 %</button>
      </div>
      <div class="seg" role="group" aria-label="Repères">
        <button id="grid" type="button" aria-pressed="false">Grille</button>
      </div>
    </div>
  </div>
  <div class="viewport" id="viewport"><div class="sheet" id="sheet">
{markup}
  </div></div>
  <p class="hint">Exemple de présentation. Zoomez à 300 % pour voir les micro-textes, la guilloche et le filigrane.</p>
  <details>
    <summary>Champs du modèle ({len(SAMPLE)})</summary>
    <div class="fields"><table><thead><tr><th>Champ</th><th>Exemple</th></tr></thead><tbody>{rows}</tbody></table></div>
  </details>
</div>
<script>{FILL_JS}</script>
<script>
(function () {{
  var SAMPLE = {json.dumps(sample, ensure_ascii=False)};
  var root = document.getElementById('diploma'), sheet = document.getElementById('sheet'), vp = document.getElementById('viewport');
  var MM = 96 / 25.4, DW = 297 * MM, DH = 210 * MM, zoom = 'fit';
  var IMAGES = {json.dumps(sorted(IMAGE_FIELDS))};
  var VARS = {{}}; Object.keys(SAMPLE).forEach(function (k) {{ VARS[k] = IMAGES.indexOf(k) >= 0 ? SAMPLE[k] : '{{{{' + k + '}}}}'; }});
  function layout() {{
    var pad = parseFloat(getComputedStyle(vp).paddingLeft) * 2;
    var s = zoom === 'fit' ? (vp.clientWidth - pad) / DW : zoom;
    sheet.style.width = DW * s + 'px'; sheet.style.height = DH * s + 'px';
    root.style.transform = 'scale(' + s + ')';
  }}
  function press(ids, on) {{ ids.forEach(function (id) {{ document.getElementById(id).setAttribute('aria-pressed', String(id === on)); }}); }}
  function mode(m) {{
    press(['mode-sample', 'mode-vars'], m);
    root.classList.toggle('show-vars', m === 'mode-vars');
    ERPIE_DIPLOMA.fill(m === 'mode-vars' ? VARS : SAMPLE, root);
  }}
  document.getElementById('mode-sample').onclick = function () {{ mode('mode-sample'); }};
  document.getElementById('mode-vars').onclick = function () {{ mode('mode-vars'); }};
  [['zoom-fit', 'fit'], ['zoom-1', 1], ['zoom-3', 3]].forEach(function (p) {{
    document.getElementById(p[0]).onclick = function () {{ zoom = p[1]; press(['zoom-fit', 'zoom-1', 'zoom-3'], p[0]); layout(); }};
  }});
  document.getElementById('grid').onclick = function () {{
    var on = root.classList.toggle('show-grid'); this.setAttribute('aria-pressed', String(on));
  }};
  mode('mode-sample'); layout();
  if (window.ResizeObserver) new ResizeObserver(function () {{ if (zoom === 'fit') layout(); }}).observe(vp);
  else window.addEventListener('resize', layout);
}})();
</script>
"""


def main():
    out = HERE
    preview_out = out / "preview.html"
    if "--preview-out" in sys.argv:
        preview_out = Path(sys.argv[sys.argv.index("--preview-out") + 1])
    (out / "diploma-master.html").write_text(template_html(), encoding="utf-8")
    (out / "sample-data.json").write_text(json.dumps(SAMPLE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preview_out.write_text(preview_html(), encoding="utf-8")
    print("wrote", out / "diploma-master.html", out / "sample-data.json", preview_out)


if __name__ == "__main__":
    main()
