# MDMS Vendor Onboarding — Fill Template

Fill the LGEAS Vendor Onboarding Excel template from a folder of supplier documents.

**Supplier folder:** $ARGUMENTS

---

## Step 0 — Read the knowledge base first

Before touching any document, read `knowledge/corrections.md`.
Apply every rule and pattern in it during extraction. It contains bank SWIFT codes, address priority rules, RC number format decisions, form role logic, and field discrepancy rules learned from prior runs.

---

## Use case — detect first

| `use_case` value | When |
|---|---|
| `new_vendor` | Standard new supplier onboarding (default) |
| `bank_change` | Existing supplier changing their bank account |

For `bank_change`: extract **old** bank fields (`old_nom_compte`, `old_banque`, `old_agence`, `old_rib`, `old_currency`, `old_swift`, `old_iban`, `old_bank_address`) from any prior RIB or letter the user provides, alongside the new RIB. The Bank Account Change Request sheet will be filled with the before/after comparison. Ask the user if no old bank document is provided.

For `new_vendor`: the Bank Account Change Request sheet is left blank in the output.

---

## Supplier type — detect first, before contacts

| Type | Signs | JSON key |
|---|---|---|
| Company, 2 contacts | User gives commercial name + finance name | `personne_morale_two` |
| Company, 1 contact | Only one person available at the supplier | `personne_morale_one` |
| Auto-entrepreneur | CIN + Carte auto-entrepreneur, no RC | `auto_entrepreneur` |

**Role mapping:**

| Form field | `personne_morale_two` | `personne_morale_one` | `auto_entrepreneur` |
|---|---|---|---|
| Requestor B5 | `commercial_name` | `requestor_name` | `nom` |
| Finance Manager D12 | `finance_name` | `requestor_name` (same) | `nom` (same) |
| Contact Person B13 | `commercial_name` | `requestor_name` (same) | `nom` (same) |
| Signatures B28/D28 | each signs their block | same person signs twice | single signature |
| Representative D10 | owner/CEO from RC (المُمَثِّل) | same | N/A (physical person) |
| LGE Contact (Sched.E only) | `lge_contact_name` | `lge_contact_name` | `lge_contact_name` |

**The LG person (Hadjer etc.) appears ONLY in Schedule E as LGE contact. Nowhere else. No signature.**

---

## Steps

1. Run `ls "$ARGUMENTS"` to list all files
2. Read each file using the Read tool (supports PDF, PNG, JPG, WEBP)
3. For each file, detect the document type and extract the fields below
4. Merge all extracted fields into one flat JSON — later docs override earlier ones for the same field
5. Validate every field against the rules below and flag MISSING / WARN issues
6. **⛔ STOP — display the confirmation table (see format below) and wait for the user to say "go" or correct any field. Do NOT write any file until confirmed.**
7. Apply any corrections the user gives, then write confirmed fields to `/tmp/mdms_fields.json`
8. Run: `python fill_template.py /tmp/mdms_fields.json <supplier_name> "$ARGUMENTS"`
   - `<supplier_name>` = basename of the supplier folder (spaces → underscores)
   - The third argument triggers auto-archiving of docs + Excel
9. Print the full completion report (see format below)

---

## Step 10 — Append to knowledge base

After a successful run, append a one-line entry to the **Runs Log** table in `knowledge/corrections.md`:
`| <date> | <supplier> | <one-line note about anything surprising or new> |`

If you discovered a new pattern (new bank, new doc format, new address rule), add it to the appropriate section in `knowledge/corrections.md` as well.

---

## Document types and fields to extract

### RC (Registre de Commerce)
**CRITICAL:** Extract from the **French text block only**. Use Arabic only for `nom_ar`.
If the RC is fully in Arabic, use `Certif existence.pdf` for `activite` and `date_immatriculation`.

**Representative extraction — priority order (highest wins):**
1. **User-provided** — if the user's message names a "signataire autorisé" or representative, use that. It overrides everything.
2. **RC المُمَثِّل/المُمَثِّلُون table** — always look for this table in the RC first. In Arabic RCs it is headed:
   - **المُمَثِّل** (singular — one director/gérant)
   - **المُمَثِّلُون** (plural — multiple shareholders/directors)

   Scan this table and take the **gérant** or **PDG** (highest role). Transcribe the name in Latin characters (transliterate from Arabic if no French version present). If the table lists multiple people, take the one with the top role (gérant/PDG/président).
3. **Agrément or other official docs** — fallback only if RC table is fully unreadable.

| JSON key | Format | Example |
|---|---|---|
| `rc_number` | `YYBnnnnnnn-WW/TT` | `03B0963512-16/00` |
| `wilaya` | French name | `Alger` |
| `nom_fr` | Company name in French | `SPA CENTRE D'ETUDES SPECIALISEES INDUSTRIELLES` |
| `nom_ar` | Arabic company name | `شركة المثال` (null if SPA/French company) |
| `forme_juridique` | SARL / EURL / SPA / EPIC / SNC | `SPA` |
| `activite` | Activity in French | `FORMATION ET ACCOMPAGNEMENT` |
| `date_immatriculation` | `DD/MM/YYYY` | `22/06/2003` |
| `representative` | Full name (Latin) | `BELHOUL MOURAD` — from RC table; user-provided contact overrides |

### NIF (Attestation d'Immatriculation Fiscale — DGI)
Authoritative source for the **legal company name** and NIF number.

| JSON key | Format | Notes |
|---|---|---|
| `nif` | 15 or 20 digits | Accept both (pre/post ALCES 2024) |
| `nom` | Legal entity name | Override `nom_fr` if different from RC |
| `adresse` | Registered address (siège social) | Use as primary `adresse` |
| `regime_fiscal` | IFU / Réel / Forfait | |
| `date_delivrance` | `DD/MM/YYYY` | |

### RIB (Relevé d'Identité Bancaire)

| JSON key | Format | Notes |
|---|---|---|
| `nom_compte` | Account holder name | |
| `banque` | Bank name | BNP Paribas / BEA / CPA / BADR / BNA … |
| `agence` | Branch name + code | e.g. `Bab Ezzouar (00780)` |
| `rib` | 20 digits | Reconstruct: BBB+GGGGG+AAAAAAA+OOO+CC |
| `iban` | `DZ` + 22 digits | null if absent |
| `swift` | String | Check knowledge base for known SWIFTs |
| `bank_address` | Address from RIB header | Distinct from `adresse` |
| `currency` | 3-letter code | Almost always `DZD` |

### Certif existence / Attestation Fiscale (DGI)

| JSON key | Format | Notes |
|---|---|---|
| `statut_fiscal` | `à jour` or `en défaut` | |
| `activite` | Activity string | Use if RC unclear |
| `date_immatriculation` | `DD/MM/YYYY` | Cross-validate with RC |

### NIS (Numéro d'Identification Statistique — ONS)
Use only for cross-validation. Do NOT use NIS address as primary `adresse`.

| JSON key | Notes |
|---|---|
| `rc_number` | Cross-check against RC |
| `adresse` | Secondary only — NIF/RC address takes priority |

### CIN (Carte Nationale d'Identité — natural persons only)

| JSON key | Format |
|---|---|
| `nom` | Family name |
| `prenom` | First name |
| `date_naissance` | `DD/MM/YYYY` |
| `numero_cin` | String |

### Carte Auto-Entrepreneur

| JSON key | Format |
|---|---|
| `numero_carte` | String |
| `nif` | 15–20 digits |
| `nom` | Name |
| `activite` | Activity |
| `date_validite` | `DD/MM/YYYY` |

---

## Validation rules

| Field | Rule | On fail |
|---|---|---|
| `nif` | `\d{15}` or `\d{20}` | ❌ WARN |
| `rc_number` | `\d{2}[A-Z]\d+-\d{2}/\d{2}` | ⚠️ WARN |
| `rib` | exactly 20 digits | ❌ WARN |
| `iban` | `DZ\d{22}` | ⚠️ WARN |
| Any date field | `DD/MM/YYYY` | ⚠️ WARN |
| `nom_fr`, `nif`, `rib`, `banque` | non-null | ❌ MISSING |

Put `null` in JSON for failed validations — never silently write a bad value.

---

## Confirmation table format (shown BEFORE writing anything)

```
## ⚠️ Please confirm before I write the Excel

Supplier: CESI_ALGERIE

| Field | Value | Source | Status |
|---|---|---|---|
| nom_fr | SPA CENTRE D'ETUDES... | NIF.pdf | ✅ |
| nif | 000316096351244 | NIF.pdf | ✅ |
| rib | 02700780000160600178 | RIB.pdf | ✅ |
| banque | BNP PARIBAS EL DJAZAÏR | RIB.pdf | ✅ |
| adresse | RUE ABEDKADER KADOUCH... | NIS.pdf | ✅ |
| nom_ar | — | — | ⚠️ not found |
| iban | — | — | ⚠️ not on RIB |

Say **"go"** to write the Excel, or correct any field (e.g. "fix adresse to X" or "nom_ar is شركة المثال").
```

---

## Completion report format

After running fill_template.py, print:

```
## Extracted Fields

| Field | Value | Source | Status |
|---|---|---|---|
| nom_fr | SPA CENTRE D'ETUDES... | NIF.pdf | ✅ |
| nif | 000316096351244 | NIF.pdf | ✅ |
| rib | 02700780000160600178 | RIB.pdf | ✅ |
| ... | ... | ... | ... |

## Documents Processed
- RC CESI ALGERIE 2026.pdf → RC (fully Arabic — used Certif existence for activite)
- NIF.pdf → NIF ✅
- BRN30055CA77712_005815.pdf → RIB ✅
- ...

## Archive
✅ archive/2026-06_CESI_ALGERIE/
   ├── docs/ (6 files)
   ├── MDMS_REG_CESI_ALGERIE_2026-06.xlsx
   └── SUMMARY.md

```
