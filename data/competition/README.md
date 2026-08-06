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
HK_Official_Merged_565_First_with_IPO.xlsx
HKCompanyInfo_数据字典.pdf
HKShareDescription_数据字典.pdf
HKshareEODPrices_数据字典.pdf
```

Each yearly directory must contain the extracted prospectus PDFs. Keep the
directory and filenames unchanged so the manifest can preserve source lineage.

`scripts/build_competition_manifest.py` requires the six extracted yearly
directories, the three CSV files and the official merged workbook. The data
dictionaries are retained for field interpretation and unit confirmation.

The official merged workbook is a separately governed bridge built from IPO,
institution and delisting sources. It supplements the truncated
`hksharedescription.csv`; it does not repair or replace that raw file. Unmatched
and missing official fields must remain explicit rather than being inferred.

For low-disk shadow testing, keep the yearly ZIP archives outside Git and stage
only the selected PDFs needed by `scripts/run_shadow_tests.py`. Do not extract
all 565 prospectuses into a repository checkout merely to run the 24-case
shadow suite.

Raw archives, PDFs and CSV data in this directory are ignored by Git. Do not
force-add them. Only generated catalogs, small test fixtures and documentation
belong in the repository.
