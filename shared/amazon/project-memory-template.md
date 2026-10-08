# Amazon Project Memory

## Mode
`SMART` <!-- AUTOPILOT | SMART | GUIDED (per agent if different) -->

## Marketplaces and templates
| Marketplace | Language | Currency | Template file (path + sha256) | Product Type | Template version |
|---|---|---|---|---|---|

## Pricing configuration
- Policy: `2026-10-08-v3` (Sale Price input; Standard = Sale/0.90; Business = Standard x 0.90; HALF_UP; precision per currency)
- Explicit overrides approved by the user: <none>
- User-decided extras (NOT policy v3, no defaults). The tier QUANTITY SET (2-4-6 / 2-4 / ...) is asked every run and is not stored as a default. Approved per product group: tier basis `<business|standard>` | discount percents `<qty:%,...>` | B2B minimum rule `<DEEPEST_TIER|none>` | B2B maximum `<+% over max(Business, Sale)|none>` | allowed price range `<-% / +% of Standard Price|none>` | tag `<CONFIRMED>` | date

## Unit economics (user-supplied per product group; re-confirm when fees change)
| Product group / SKUs | Landed unit cost | Referral fee % (+ per-item min) | FBA fee / MFN fee (per unit) | VAT % | Other % / fixed | Target margin % | Date | Tag |
|---|---|---|---|---|---|---|---|---|

## GTIN exemption scope
| Marketplace | Brand | Category / Product Type | Account | Effective date | Source |
|---|---|---|---|---|---|

## Brand approvals / restrictions
| Marketplace | Brand | Status | Note |
|---|---|---|---|

## User override rules (USER_OVERRIDE_RULE)
| rule_id | Scope (marketplace / product type / template version) | Rule | Precedence | Date | Tag |
|---|---|---|---|---|---|

## Locked fields (DO_NOT_CHANGE)
| Field | Scope | Reason | Locked by | Date |
|---|---|---|---|---|

## Glossary / forbidden terms / competitor brands
| Term | Rule / approved localization |
|---|---|

## SEO sources
| Marketplace | Source (Cerebro/Magnet/file) | Date | Version |
|---|---|---|---|

## Decisions
| Date | Agent | Scope (project / SKU) | Decision | Tag |
|---|---|---|---|---|

## Batches and deliveries
| Date | Agent | Batch ID | Files (path + hash) | Status | Commit SHA / source ref |
|---|---|---|---|---|---|

## Open issues
