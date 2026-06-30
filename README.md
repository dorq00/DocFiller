# DocFiller

Fills the LGEAS vendor onboarding Excel (MDMS) from Algerian supplier documents — RC, NIF, RIB, Certif existence — using Claude's vision to read and extract fields, with a human confirmation step before any file is written.

## How it works

```
Drop docs into suppliers/incoming/<SUPPLIER>/
        ↓
/fill-mdms suppliers/incoming/<SUPPLIER>        ← Claude Code slash command
        ↓
Claude reads every PDF/image, extracts fields, shows confirmation table
        ↓
User says "go"
        ↓
python3 fill_template.py fields.json <NAME> <folder>
        ↓
archive/<YYYY-MM>_<SUPPLIER>/
├── docs/                   ← original scans
├── MDMS_REG_<NAME>.xlsx    ← filled Excel
└── SUMMARY.md              ← extracted fields log
```

## Sheets filled

| Sheet | What gets filled |
|---|---|
| Vendor Registration Form | Company info, contacts, bank details, signatures |
| Schedule E – Payment | Bank details + LGE contact point |
| Pledge Letter | Date, company name, RC + NIF |

## Setup

```bash
pip install openpyxl
```

Place the onboarding template at:
```
templates/LGEAS_Vendor_Onboarding_TEMPLATE_v1.1.xlsx
```

## Document types supported

RC (Registre de Commerce) · NIF · RIB · Certif existence · NIS · Agrément · CIN · Carte auto-entrepreneur

Handles fully Arabic RCs, bilingual docs, and multi-document field conflicts. Field extraction rules and bank SWIFT codes accumulate in `knowledge/corrections.md` after each run.
