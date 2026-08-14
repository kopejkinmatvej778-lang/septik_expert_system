# DOCX/PDF rendering

## Primary renderer

Use this path when approved DOCX templates exist:

```text
Python + python-docx -> DOCX
LibreOffice headless -> PDF
```

Backend API:

```text
POST /api/render/contract
```

## Existing project pattern

The current project already has working scripts that:

- open a reference DOCX with `Document(reference_path)`;
- replace title, date, buyer, address, totals;
- rebuild materials and works tables;
- save DOCX;
- create PDFs either through conversion or ReportLab fallback.

Keep this pattern for template fidelity.

## Fallback renderer

Use `scripts/render_contract_pdf.py` when:

- DOCX template is not available;
- only PDF is needed;
- quick MVP testing is required.

It uses:

```text
Python + ReportLab
```

## VPS dependencies

```text
python3
python3-venv
python-docx
reportlab
LibreOffice headless
poppler-utils
Times-compatible fonts
```

## Required output checks

For DOCX:

- file exists;
- size > 0;
- contains contract number, buyer, address, total.

For PDF:

- file exists;
- size > 0;
- can be opened/rendered;
- extracted text contains contract number, buyer, address, total;
- page count > 0.

## Do not

- Do not hide missing passport data with blanks unless the user explicitly asks for a blank draft.
- Do not overwrite legal template text casually.
- Do not remove appendices for materials and works unless template says so.
- Do not store only PDF when DOCX is available.
