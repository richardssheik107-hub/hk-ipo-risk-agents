# Competition-data test fixture

The B1 unit tests build a miniature competition-data tree under pytest's
temporary directory. It contains tiny generated PDFs and small GB18030 CSVs,
so tests never read or copy the multi-gigabyte competition dataset.

The miniature tree covers:

- a regular 2020 development case;
- the 2410.HK development exception in 2024;
- a 2025 blind-test case;
- one case without EOD coverage;
- a malformed security-master record that must be quarantined.
