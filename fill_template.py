#!/usr/bin/env python3
"""Fill vendor onboarding Excel template from a JSON fields file.

Usage: python fill_template.py <fields.json> <supplier_name> [<source_folder>]

Supplier types handled:
  - personne_morale_two  : company with separate commercial + finance contacts
  - personne_morale_one  : company with only one contact (fills both roles)
  - auto_entrepreneur    : physical person, single name everywhere
"""
import json
import re
import sys
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl not found — run: pip install openpyxl")

BASE        = Path(__file__).parent
TEMPLATE    = BASE / "templates" / "vendor_onboarding_template.xlsx"
OUTPUT_DIR  = BASE / "output"
ARCHIVE_DIR = BASE / "archive"

DATE_STR   = datetime.now().strftime("%Y-%m")
TODAY_DDMM = datetime.now().strftime("%d/%m/%Y")


def routing_from_rib(rib: str) -> str:
    """First 8 digits of RIB = bank code (3) + guichet (5)."""
    return (rib or "")[:8]


def business_number(rc: str, nif: str) -> str:
    parts = []
    if rc:  parts.append(f"RC: {rc}")
    if nif: parts.append(f"NIF: {nif}")
    return " | ".join(parts)


def resolve_contacts(fields: dict) -> dict:
    """
    Determine who fills requestor, finance_manager, and contact_person slots.

    supplier_type:
      personne_morale_two  → commercial_name + finance_name (different people)
      personne_morale_one  → only one person, fills all supplier-side roles
      auto_entrepreneur    → physical person, name only
    """
    t = fields.get("supplier_type", "personne_morale_one")

    if t == "personne_morale_two":
        requestor        = fields.get("commercial_name", "")
        finance_manager  = fields.get("finance_name", "")
        requestor_tel    = fields.get("commercial_tel",   fields.get("tel", ""))
        requestor_email  = fields.get("commercial_email", fields.get("email", ""))
        finance_tel      = fields.get("finance_tel",      fields.get("tel", ""))
        finance_email    = fields.get("finance_email",    fields.get("email", ""))

    elif t == "auto_entrepreneur":
        name             = fields.get("nom_fr") or fields.get("nom", "")
        requestor        = name
        finance_manager  = name
        requestor_tel    = fields.get("tel", "")
        requestor_email  = fields.get("email", "")
        finance_tel      = requestor_tel
        finance_email    = requestor_email

    else:  # personne_morale_one — same person fills both sides
        one              = fields.get("requestor_name", "")
        requestor        = one
        finance_manager  = one
        requestor_tel    = fields.get("tel", "")
        requestor_email  = fields.get("email", "")
        finance_tel      = requestor_tel
        finance_email    = requestor_email

    return {
        "requestor":       requestor,
        "finance_manager": finance_manager,
        "tel":             requestor_tel,
        "email":           requestor_email,
        "finance_tel":     finance_tel,
        "finance_email":   finance_email,
    }


def fill(fields: dict, supplier_name: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    dest = OUTPUT_DIR / f"VENDOR_REG_{supplier_name}_{DATE_STR}.xlsx"
    shutil.copy(TEMPLATE, dest)

    wb = openpyxl.load_workbook(dest)

    if "CHECK LIST FOR VENDOR'S BANK AC" in wb.sheetnames:
        del wb["CHECK LIST FOR VENDOR'S BANK AC"]

    c  = resolve_contacts(fields)

    # ── Vendor Registration Form ──────────────────────────────────────────────
    vr = wb["Vendor Registration Form"]

    # Application header
    vr["B4"]  = "Vendor Registration"
    vr["D4"]  = TODAY_DDMM

    # Requestor = supplier's contact who initiated
    vr["B5"]  = c["requestor"]                      # merged B5:D5

    # Company information (supplier)
    vr["B8"]  = fields.get("nom_fr") or fields.get("nom")
    vr["D8"]  = fields.get("nom_ar")
    vr["B9"]  = fields.get("adresse")               # merged B9:D9
    vr["B10"] = fields.get("forme_juridique")
    vr["D10"] = fields.get("representative")         # owner/CEO from RC (المُمَثِّل)

    # Business Number = RC + NIF combined
    vr["B11"] = business_number(fields.get("rc_number"), fields.get("nif"))
    vr["D11"] = fields.get("date_immatriculation")

    # Row 12 = dark split header (labels only, no data written)
    # Parallel contact blocks — Requestor (left) | Finance Team Manager (right)
    vr["B13"] = c["requestor"]                       # contact person name
    vr["D13"] = c["finance_manager"]                 # finance name
    vr["B14"] = c["email"]                           # e-mail
    vr["D14"] = c["finance_email"]                   # finance e-mail
    vr["B15"] = c["tel"]                             # office tel
    vr["D15"] = c["finance_tel"]                     # finance tel

    # Bank information
    vr["B17"] = fields.get("nom_compte")
    vr["D17"] = fields.get("nom_compte")             # local = same as English
    vr["B18"] = fields.get("banque")
    vr["D18"] = fields.get("banque")
    vr["B19"] = fields.get("agence")
    vr["D19"] = fields.get("agence")

    routing   = fields.get("routing_no") or routing_from_rib(fields.get("rib", ""))
    vr["B20"] = routing                              # merged B20:D20

    vr["B21"] = fields.get("rib")
    vr["D21"] = fields.get("currency", "DZD")
    vr["B22"] = fields.get("swift")
    vr["D22"] = None                                 # no IBAN in Algeria (domestic)
    vr["B23"] = fields.get("bank_address")           # merged B23:D23

    # Signature section — supplier signs both blocks
    # (same person if only one contact, different if two)
    vr["B28"] = c["requestor"]
    vr["D28"] = c["finance_manager"]
    requestor_pos = fields.get("requestor_position", "")
    finance_pos   = fields.get("finance_position") or requestor_pos  # mirror if same person
    vr["B29"] = requestor_pos
    vr["D29"] = finance_pos

    # ── Schedule E – Payment ──────────────────────────────────────────────────
    se = wb["Schedule E – Payment"]

    se["B4"]  = fields.get("nom_fr") or fields.get("nom")
    se["B5"]  = fields.get("nom_compte")             # MUST come from RIB
    se["B6"]  = fields.get("banque")
    se["B7"]  = fields.get("agence")
    se["B8"]  = fields.get("rib")

    # Internal contact point (not the supplier)
    se["B14"] = fields.get("lge_contact_name",  "")
    se["B15"] = fields.get("lge_contact_email", "")
    se["B16"] = fields.get("lge_contact_dept",  "Finance")
    se["B17"] = fields.get("lge_contact_tel",   "")

    # ── Pledge Letter ─────────────────────────────────────────────────────────
    pl = wb["Pledge Letter"]

    pl["B14"] = TODAY_DDMM
    pl["B15"] = fields.get("nom_fr") or fields.get("nom")
    pl["B16"] = business_number(fields.get("rc_number"), fields.get("nif"))

    # ── Bank Account Change Request (only for bank-change use case) ───────────
    if fields.get("use_case") == "bank_change":
        bc = wb["Bank Account Change Request"]

        bc["B5"]  = fields.get("nom_fr") or fields.get("nom")
        bc["B21"] = TODAY_DDMM

        # Before column — old bank details
        bc["B10"] = fields.get("old_nom_compte")
        bc["B11"] = fields.get("old_banque")
        bc["B12"] = fields.get("old_agence")
        bc["B13"] = fields.get("old_rib")
        bc["B14"] = fields.get("old_currency", "DZD")
        bc["B15"] = fields.get("old_swift")
        bc["B16"] = fields.get("old_iban")
        bc["B17"] = fields.get("old_bank_address")

        # After column — new bank details (same source as main form)
        bc["C10"] = fields.get("nom_compte")
        bc["C11"] = fields.get("banque")
        bc["C12"] = fields.get("agence")
        bc["C13"] = fields.get("rib")
        bc["C14"] = fields.get("currency", "DZD")
        bc["C15"] = fields.get("swift")
        bc["C16"] = fields.get("iban")
        bc["C17"] = fields.get("bank_address")

    wb.save(dest)
    print(f"✅ Excel written: {dest}")
    return dest


def validate(fields: dict) -> list[str]:
    issues = []
    required = ["nom_fr", "nif", "rib", "banque"]
    for f in required:
        if not fields.get(f):
            issues.append(f"❌ MISSING: {f}")

    if fields.get("nif") and not re.fullmatch(r'\d{15}|\d{20}', fields["nif"]):
        issues.append(f"⚠️  NIF invalid: {fields['nif']}")

    if fields.get("rib") and not re.fullmatch(r'\d{20}', fields["rib"]):
        issues.append(f"⚠️  RIB must be 20 digits: {fields['rib']}")

    # RC format: YYBnnnnnnn-WW/TT  e.g. 03B0963512-16/00  (ب reads as B)
    if fields.get("rc_number") and not re.search(r'\d{2}[A-Z]\d+-\d{2}/\d{2}', fields["rc_number"]):
        issues.append(f"⚠️  RC format unexpected (expected YYBnnnnnnn-WW/TT): {fields['rc_number']}")

    # Beneficiary name (RIB) must roughly match company name (RC/NIF)
    def normalize(s):
        s = unicodedata.normalize("NFD", (s or "").upper())
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # strip accents
        return re.sub(r'\b(SPA|SARL|EURL|EPIC|SNC|SASU)\b', '', s).strip()
    nom_rc  = normalize(fields.get("nom_fr") or fields.get("nom"))
    nom_rib = normalize(fields.get("nom_compte"))
    if nom_rc and nom_rib and nom_rc not in nom_rib and nom_rib not in nom_rc:
        issues.append(
            f"❌ NAME MISMATCH — RC: '{fields.get('nom_fr')}' "
            f"vs RIB account: '{fields.get('nom_compte')}'"
        )

    for issue in issues:
        print(issue)
    return issues


def archive(source_folder: str, supplier_name: str, fields: dict, excel_path: Path) -> Path:
    tag      = f"{DATE_STR}_{supplier_name}"
    arch     = ARCHIVE_DIR / tag
    docs_dir = arch / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    src = Path(source_folder)
    for f in src.iterdir():
        if f.is_file() and not f.name.startswith("."):
            shutil.copy(f, docs_dir / f.name)

    final_excel = arch / excel_path.name
    shutil.move(str(excel_path), final_excel)

    # Clear incoming folder now that docs are safely in archive/docs/
    # Guard: never wipe the test folder
    if src.name != "test":
        shutil.rmtree(src)
        src.mkdir()
        print(f"🗑️  Cleared: {src}")

    required = {"nom_fr", "nif", "rib", "banque"}
    lines = [
        f"# Vendor Registration — {supplier_name} — {DATE_STR}\n",
        "## Extracted Fields\n",
        "| Field | Value | Status |",
        "|---|---|---|",
    ]
    for k, v in fields.items():
        status = "✅" if v else ("❌ MISSING" if k in required else "⚠️ empty")
        lines.append(f"| `{k}` | {v or '—'} | {status} |")
    lines += ["", "## Documents Processed"]
    for f in sorted(docs_dir.iterdir()):
        lines.append(f"- {f.name}")

    (arch / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Archived: {arch}")
    return arch


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python fill_template.py <fields.json> <supplier_name> [<source_folder>]")
        sys.exit(1)

    fields_path   = Path(sys.argv[1])
    supplier_name = sys.argv[2]
    source_folder = sys.argv[3] if len(sys.argv) > 3 else None

    fields = json.loads(fields_path.read_text(encoding="utf-8"))
    issues = validate(fields)
    if any(i.startswith("❌") for i in issues):
        sys.exit("Aborting — fix errors above before writing Excel.")
    excel = fill(fields, supplier_name)

    if source_folder:
        archive(source_folder, supplier_name, fields, excel)
