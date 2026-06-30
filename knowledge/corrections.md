# Knowledge Base — Algerian Document Extraction
_Appended by Claude after each successful run. Read this before extracting any fields._

---

## Form Role Logic — CRITICAL

The Vendor Registration Form is filled by the buyer **about** the supplier. All contacts in the form body are **supplier-side** people. The internal company contact appears **only** in Schedule E as Internal Contact Point — nowhere else, no signature.

| supplier_type | requestor (B5) | finance_manager (D12) | signatures (B28/D28) | lge_contact (Sched.E) |
|---|---|---|---|---|
| `personne_morale_two` | commercial contact | finance contact | each signs their block | LG liaison |
| `personne_morale_one` | only contact available | same person | same person signs twice | LG liaison |
| `auto_entrepreneur` | the physical person | same | same person signs | LG liaison |

**Representative** (D10) = owner/CEO/director extracted from the RC's **المُمَثِّل / المُمَثِّلُون table** (directors/shareholders table). Always scan this table in the RC first — take the gérant or PDG (highest role). Transliterate from Arabic if no French name present. Fall back to Agrément or other official docs only if the RC table is unreadable.

**Contact Person** (B13) = same as requestor (supplier's contact at LG).

**Finance Manager** (D12) = supplier's finance person. If none provided, default to requestor.

**Internal Contact Point** (Schedule E only) = the buyer-side colleague who liaised. No signature. Name only usually — phone/email filled manually.

---

## General Rules

- Always prefer the **French text block** on bilingual RC documents. Use Arabic only for `nom_ar`.
- When multiple addresses appear across documents, use:
  - `adresse` → registered address from NIF or RC (siège social)
  - `bank_address` → operational address from the RIB header
- SPA companies (Société Par Actions) rarely have an official Arabic name. Set `nom_ar = null` instead of guessing.
- The **NIS document** (إشعار بالتعريف — Office National des Statistiques) contains useful cross-validation data (RC number, address, activity code) but is NOT a source for NIF or bank fields.
- The **Certif existence** (Certificat d'Existence, DGI) is a reliable source for `activite` and `date_immatriculation` when the RC is unclear or fully in Arabic.

---

## Bank-Specific Patterns

| Bank | SWIFT | RIB Format Notes |
|---|---|---|
| BNP Paribas El Djazaïr | BNPADZALXXX | 3+5+7+3+2 = 20 digits: BBB GGGGG AAAAAAA OOO CC |
| BEA | BEAADZAL | — |
| CPA | CPAAADZAL | — |
| BADR | BADRDZ21 | — |
| BNA | BNADDZAL | — |

---

## RC Number Formats

The RC appears in Arabic with "ب" between year and number. Read it as:
`YY[B]NNNNNNN-WW/TT` where ب = B

- Correct format: `03B0963512-16/00`
  - `03` = year (2003)
  - `B` = letter (Arabic ب)
  - `0963512` = registration number
  - `16` = wilaya (Alger)
  - `00` = type
- Validator regex: `\d{2}[A-Z]\d+[-/]\d{2}[/]\d{2}`
- RC wilaya code `16` = Alger.
- Do NOT rewrite as `16/0963512B/03` — that is wrong order.

---

## Field Discrepancies — Known Cases

| Situation | Rule |
|---|---|
| NIS shows "SUPERIEURES" but NIF shows "SPÉCIALISÉES" | Trust NIF — DGI is authoritative for legal name |
| Bank stamp address ≠ RIB header address | RIB header address = operational/account address; use for `bank_address` |
| RIB guichet code 00780 → BNP Paribas Bab Ezzouar (BBZ) | Bab Ezzouar is the siège social branch for this client |
| Certif existence shows a third address (BARAKI) | Default: tax inspection address — do NOT use. BUT if a 2026 Agrément or RC modification also shows Baraki, the company has moved and Baraki IS the current `adresse`. Always cross-check with most recent RC/Agrément. |

---

## Runs Log

| Date | Supplier | Notes |
|---|---|---|
| 2026-06-30 | — | RC fully in Arabic — Certif existence used for activite and date_immatriculation. NIS used for RC number cross-check only. Address discrepancy across 3 docs — Agrément is authoritative for current headquarters. |
| 2026-06-30 | — | Address confirmed via 2026 Agrément when Certif existence showed a newer address. Representative from Agrément fallback when RC table unreadable. Name mismatch false positive: NIF uses accented characters (SPÉCIALISÉES), RIB drops accents (SPECIALISEES) — validator normalizes before comparing. |
| 2026-06-30 | — | User-provided signataire autorisé overrides RC/Agrément representative. CC'd contacts on email are not form contacts. RIB may be issued at a different branch than the account branch — use guichet code to identify correct branch. |
