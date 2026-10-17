# ERPIE — Relevé de notes (transcript)

An A4 portrait transcript in the same family as the master diploma. It's monochrome: only the logo and the cachet are in colour.

See `exports/releve-sample.pdf` for the sample.

## Files

| File | What it is |
|---|---|
| `build.py` | Renders a transcript from a JSON data file. |
| `sample-data.json` | Example: M. Aboubacar Togola, Master en Génie Logiciel. |
| `releve-sample.html` | The rendered sample. |
| `exports/releve-sample.pdf` | The sample printed to PDF. |
| `../tools/print-pdf.js` | Prints any ERPIE document HTML to PDF with Chromium. |

## Generating a transcript

```sh
pip install segno                                  # QR code
python3 build.py student.json -o releve.html
node ../tools/print-pdf.js releve.html releve.pdf  # needs the playwright package
```

## What is computed

`build.py` calculates these from the grades, so they can never contradict the table:

- the average for each level and the overall average, weighted by ECTS credits (LMD standard), rounded to two decimals;
- the credits earned (a module counts once its grade is 10/20 or higher);
- the mention: Très Bien ≥ 16, Bien ≥ 14, Assez Bien ≥ 12, Passable ≥ 10.

Only the jury's honours line (`jury_honours`, e.g. "Avec les félicitations du jury") is typed in, because it is a jury decision.

## Data

Each module is a row: `[code, title, subtitle, ects, grade, appreciation]`. The subtitle is optional (use `""`), for a thesis topic for example.

Leave `school_address` and `school_contact` empty to hide them. Leave `school_stamp` empty, or point it to a missing file, to print without the cachet. The cachet image is not stored in git.
