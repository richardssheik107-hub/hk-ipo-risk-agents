# Competition data (local only)

Place the competition data files directly in this directory, or keep them
elsewhere and pass that directory through `--data-root` or the
`IPO_RISK_COMPETITION_DATA_ROOT` environment variable.

Expected files:

```text
2020_138份/
2021_88份/
2022_87份/
2023_63份/
2024_73份/
2025_116份/
hkcompanyinfo.csv
hksharedescription.csv
hkshareeodprices.csv
HKCompanyInfo_数据字典.pdf
HKShareDescription_数据字典.pdf
HKshareEODPrices_数据字典.pdf
```

Each yearly directory must contain the extracted prospectus PDFs. Keep the
directory and filenames unchanged so the manifest can preserve source lineage.

Raw archives, PDFs and CSV data in this directory are ignored by Git. Do not
force-add them. Only generated catalogs, small test fixtures and documentation
belong in the repository.
