# ERPIE — Master diploma template

Official diploma template for ERPIE. A4 landscape (297 × 210 mm), print-ready, and exports to vector PDF.

The design is **full bleed**: the green border runs to the edge of the page. A print shop should print it on larger paper and trim to A4. A desktop printer will leave a thin white margin.

![Sample](exports/diploma-sample.jpg)

## Files

| File | What it is |
|---|---|
| `diploma-master.html` | The template. Every dynamic value is a `{{FIELD}}` token. |
| `sample-data.json` | Example values for every field. |
| `build.py` | Generates the template: engraved frame, guilloche, microtext. Edit this, not the HTML. |
| `assets/` | Logo and watermark emblem. |
| `exports/diploma-sample.pdf` | The template filled with sample data and printed to PDF. |

The logo files are in `brand/logo/` at the repo root.

## Filling the template

Use either of these methods:

1. **Server-side:** replace each `{{FIELD}}` token in `diploma-master.html` with its value (HTML-escape the values), then print to PDF.
2. **In the browser:** set `window.DIPLOMA_DATA = {...}` before the page loads, or call `ERPIE_DIPLOMA.fill(data)`. Empty optional fields hide their rows, and long names shrink to fit.

PDF export with Playwright/Chromium:

```js
await page.pdf({ width: '297mm', height: '210mm', printBackground: true });
```

## Structure

The layout follows the French national diploma model:

1. State header: country, ministry, then the school.
2. Title.
3. Visas, left-aligned with one per line: creation decision, opening order, habilitation order, supporting documents (with the student's birth details), and the jury minutes.
4. Award sentence: "Le diplôme de Master en …, parcours …, est délivré à", then the name, academic year and mention, ending with "pour en jouir avec les droits et prérogatives qui y sont attachés."
5. "Fait à …, le …"
6. Signatures: the holder (*Le titulaire*), the Director of Studies, and the Director General.

## Fields

| Field | Notes |
|---|---|
| `SCHOOL_LOGO` | Image URL or `data:` URI |
| `COUNTRY` | `République du Mali` |
| `AUTHORITY` | *Optional.* Supervising ministry |
| `SCHOOL_NAME` | `ERPIE` |
| `SCHOOL_STATUS` | *Optional.* e.g. `Établissement privé d’enseignement supérieur` |
| `CERTIFICATE_NUMBER` | e.g. `00000001` |
| `SERIAL_NUMBER` | *Optional* |
| `DOCUMENT_TITLE` | `Diplôme` |
| `QUALIFICATION` | `de Master` / `de Licence` |
| `DECREE_CREATION` | `N° 2018-0001575/MESRS-SG du 3 septembre 2018` |
| `DECREE_OPENING` | `N° 2022-4383/MESRS-SG du 21 septembre 2022` |
| `DECREE_HABILITATION` | `N° 2024-3794/MESRS-SG du 8 octobre 2024` (covers Licence and Master) |
| `RECIPIENT_HONORIFIC` | *Optional.* `M.` / `Mme` |
| `RECIPIENT_NAME` | |
| `STUDENT_ID` | *Optional.* Matricule, shown in the supporting-documents visa, e.g. `MS-GL-2020-0001` |
| `RECIPIENT_BORN` | `né` / `née` |
| `RECIPIENT_REF` | `l’intéressé` / `l’intéressée` |
| `RECIPIENT_BIRTH_DATE` | e.g. `12 mars 2001` |
| `RECIPIENT_BIRTH_PLACE` | e.g. `Bamako` |
| `DEGREE` | `Master` / `Licence` |
| `PROGRAM_NAME` | e.g. `Génie Logiciel` |
| `SPECIALIZATION` | *Optional.* Track (parcours), e.g. `Transformation numérique` |
| `ACADEMIC_YEAR` | e.g. `2025 – 2026` |
| `DISTINCTION` | *Optional.* e.g. `Très Bien` |
| `JURY_HONOURS` | *Optional.* e.g. `avec les félicitations du jury`, shown after the mention |
| `ISSUE_CITY` | |
| `ISSUE_DATE` | |
| `DIRECTOR_TITLE`, `DIRECTOR_NAME` | Centre signature |
| `AUTHORIZED_SIGNATORY_TITLE`, `AUTHORIZED_SIGNATORY_NAME` | Right signature |
| `DIRECTOR_SIGNATURE`, `AUTHORIZED_SIGNATORY_SIGNATURE` | *Optional.* Transparent PNG of the signature, placed above the signature line |
| `SCHOOL_STAMP` | *Optional.* School cachet image, stamped over the right half of the Director General block. Leave empty to print without it. |

The holder's signature block on the left is fixed and has no field.

## Rebuilding

```sh
python3 build.py                      # rewrites diploma-master.html and sample-data.json
python3 build.py --preview-out x.html # also writes the interactive preview
```

The frame and background are plain vector SVG. They don't use SVG `<pattern>`, because Chromium flattens patterns into 72 dpi images in PDF output.
