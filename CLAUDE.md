# DocFiller — LGEAS MDMS Vendor Onboarding
### v2.2 | Claude Code Skill

---

## What This Does

Drop supplier documents (PDFs or images) into `suppliers/incoming/<NAME>/`, run `/fill-mdms`, get:
- Filled MDMS Excel (Vendor Registration Form + Schedule E)
- Archived folder with original docs + Excel + SUMMARY.md

**No Gemini API. No Python pipeline. Claude reads the docs directly using its vision.**

---

## Usage

```bash
# In Claude Code, from this directory:
/fill-mdms suppliers/incoming/SARL_EXAMPLE
/fill-mdms suppliers/test
```

---

## File Map

| Path | Purpose |
|---|---|
| `.claude/commands/fill-mdms.md` | The slash command — extraction rules, field schemas, validation |
| `fill_template.py` | Excel writer + archiver |
| `knowledge/corrections.md` | Claude's growing memory — Algerian doc patterns, bank SWIFTs, field rules |
| `templates/LGEAS_Vendor_Onboarding_TEMPLATE_v1.1.xlsx` | Source template (never overwritten) |
| `suppliers/incoming/<NAME>/` | Drop supplier docs here per supplier |
| `suppliers/test/` | Sample docs for testing |
| `archive/<YYYY-MM>_<SUPPLIER>/` | Completed registrations |
| `archive/<YYYY-MM>_<SUPPLIER>/docs/` | Original scans |
| `archive/<YYYY-MM>_<SUPPLIER>/SUMMARY.md` | Extracted fields + notes |
| `output/` | Temp Excel before archiving |

---

## Workflow

```
Drop docs into suppliers/incoming/<NAME>/
        ↓
/fill-mdms suppliers/incoming/<NAME>
        ↓
Claude reads knowledge/corrections.md
        ↓
Claude reads each PDF/image → extracts + validates fields
        ↓
fill_template.py → Excel → archive/<YYYY-MM>_<NAME>/
        ↓
Claude appends to knowledge/corrections.md
```

---

## fill_template.py — Cell Mapping

### Vendor Registration Form

| JSON field | Cell | Notes |
|---|---|---|
| `nom_fr` | B8 | |
| `nom_ar` | D8 | null if French company |
| `adresse` | B9 | merged B9:D9 |
| `forme_juridique` | B10 | |
| `representative` | D10 | |
| `nif` | B11 | |
| `date_immatriculation` | D11 | |
| `contact_person` | B13 | merged B13:D13 |
| `email` | B14 | |
| `tel` | D14 | |
| `nom_compte` | B17 | |
| `nom_ar` / `nom_compte` | D17 | |
| `banque` | B18, D18 | |
| `agence` | B19, D19 | |
| `rib` | B21 | |
| `currency` | D21 | default DZD |
| `swift` | B22 | |
| `iban` | D22 | |
| `bank_address` | B23 | merged B23:D23 |

### Schedule E – Payment

| JSON field | Cell |
|---|---|
| `nom_fr` | B4 |
| `nom_compte` | B5 |
| `banque` | B6 |
| `agence` | B7 |
| `rib` | B8 |

---

## Supplier Type Logic

`fill_template.py` handles three supplier types via `supplier_type` field in JSON:

| Type | When | Key fields |
|---|---|---|
| `personne_morale_two` | Company with commercial + finance contacts | `commercial_name`, `finance_name` |
| `personne_morale_one` | Company with only one contact | `requestor_name` fills all roles |
| `auto_entrepreneur` | Physical person, no RC | `nom` fills all roles |

**Form role rules (LOCKED):**
- Requestor (B5), Finance Manager (D12), Contact Person (B13), Signatures (B28/D28) = all **supplier-side** people
- LG person (Hadjer etc.) = **Schedule E only** (B14) — no signature, nowhere else
- Representative (D10) = owner/CEO from RC المُمَثِّل table
- If only one supplier contact: same person fills all roles and signs twice

## Key Business Rules (LOCKED)

- **RC format**: `03B0963512-16/00` (YYBnnnnnnn-WW/TT) — Arabic ب reads as B. Never rewrite as `16/0963512B/03`
- **Business Number cell (B11)**: RC + NIF concatenated — `RC: 03B0963512-16/00 | NIF: 000316096351244`
- **Routing (B20)**: first 8 digits of RIB (bank code 3 + guichet 5)
- **IBAN**: always null for Algerian domestic suppliers
- **Bank name local**: same as English (D18 = B18)
- **Beneficiary (Schedule E B5)**: MUST come from RIB `nom_compte`, must fuzzy-match RC name — flag mismatch
- **No IBAN in Algeria** domestic context

## Dependency

```bash
pip install openpyxl   # only dependency
```
