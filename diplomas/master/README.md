# ERPIE — Master diploma template

Official diploma template for ERPIE. A4 landscape (297 × 210 mm), print-ready, and exports to vector PDF.

![Sample](exports/diploma-sample.jpg)

## Files

| File | What it is |
|---|---|
| `diploma-master.html` | The template. Every dynamic value is a `{{FIELD}}` token. |
| `sample-data.json` | Example values for every field. |
| `build.py` | Generates the template: engraved frame, guilloche, microtext, seal. Edit this, not the HTML. |
| `assets/` | Logo, watermark emblem, sample QR. |
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

## Fields

| Field | Notes |
|---|---|
| `SCHOOL_LOGO` | Image URL or `data:` URI |
| `SCHOOL_NAME` | Shown at the bottom of the institutional header |
| `COUNTRY` | Country / jurisdiction |
| `AUTHORITY` | *Optional.* Supervising education authority. Fill only with a real, verifiable authority. |
| `ACCREDITATION` | *Optional.* Authorisation or accreditation number. Real values only. |
| `CERTIFICATE_NUMBER` | e.g. `00000001` |
| `SERIAL_NUMBER` | *Optional* |
| `DOCUMENT_TITLE` | `Diplôme` / `Certificat` |
| `QUALIFICATION` | e.g. `de Master Professionnel` |
| `RECIPIENT_HONORIFIC` | *Optional.* `M.` / `Mme` |
| `RECIPIENT_NAME` | Rendered in small caps |
| `PROGRAM_NAME` | |
| `DISTINCTION` | *Optional.* Mention |
| `SPECIALIZATION` | Domaine |
| `PROGRAM_DURATION` | |
| `ACADEMIC_YEAR` | |
| `ISSUE_DATE` | |
| `ISSUE_CITY` | |
| `PROGRAM_REFERENCE` | *Optional* |
| `DIRECTOR_TITLE`, `DIRECTOR_NAME` | Left signature |
| `ACADEMIC_OFFICIAL_TITLE`, `ACADEMIC_OFFICIAL_NAME` | Centre signature |
| `AUTHORIZED_SIGNATORY_TITLE`, `AUTHORIZED_SIGNATORY_NAME` | Right signature |
| `SEAL` | *Optional.* Image of the official seal. Leave it empty to keep the engraved placeholder ring. |
| `QR_CODE` | QR image that encodes the verification URL |
| `VERIFICATION_URL` | |
| `CREDENTIAL_ID` | |
| `SECURITY_CODE` | *Optional* |

## Rebuilding

```sh
python3 build.py                      # rewrites diploma-master.html and sample-data.json
python3 build.py --preview-out x.html # also writes the interactive preview
```

The preview needs `segno` (`pip install segno`) to draw the sample QR code.

The frame and background are plain vector SVG. They don't use SVG `<pattern>`, because Chromium flattens patterns into 72 dpi images in PDF output.
