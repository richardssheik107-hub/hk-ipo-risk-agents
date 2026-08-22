"""Read-only Oracle Gold coverage and eligibility audit for the evaluation-only lane.

Explains the case-packet -> pass1 -> officially-buildable Oracle funnel, reports the
per-split Oracle coverage that the PR-E O / OM arms depend on, and compares each
Oracle artifact's self-declared identity against the authoritative official bridge.
It reads only reviewed annotation artifacts and governed official metadata; it never
runs the production pipeline, reads market values or outcome labels, or touches the
2025 blind cohort.
"""
from __future__ import annotations
import argparse, csv, json
from collections import Counter
from pathlib import Path
from ipo_risk.modeling.oracle_document import build_oracle_document_features, load_risk_gold
from ipo_risk.providers.competition_market import CompetitionCSVMarketDataProvider
from ipo_risk.schemas.market import expected_market_split

AUDIT_VERSION = 'oracle_gold_coverage_audit_v1'
BLIND_COHORT_YEAR = 2025
FIELDS = ['case_id', 'packet_present', 'audit_present', 'pass1_present', 'in_official_universe',
          'official_cohort_year', 'official_dataset_split', 'annotation_source_year', 'annotation_dataset_split',
          'identity_mismatch', 'oracle_buildable', 'failure_reason', 'effective_annotation_hash', 'content_hash']
# join_oracle_outcome() compares exactly these artifact fields against the outcome label,
# so a disagreement with the official bridge becomes a hard join failure at PR-D / PR-E.
IDENTITY_FIELDS = ('cohort_year', 'dataset_split')


def _packet_metadata(root: Path, case_id: str) -> dict[str, str]:
    path = root / 'docs' / 'annotation' / 'gpt_expert_v1_1' / 'case_packets' / case_id / 'case_metadata.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


def _reason(exc: Exception) -> str:
    """Collapse the repeated per-risk validation codes into one readable reason."""
    text = str(exc)
    head, _, tail = text.partition(': ')
    codes = sorted({code.strip() for code in tail.split(';') if code.strip()})
    return f'{type(exc).__name__}: {head}: {",".join(codes)}' if codes else f'{type(exc).__name__}: {text}'


def audit(root: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Build the per-case coverage rows plus the funnel and identity summary."""
    provider = CompetitionCSVMarketDataProvider(root, catalog_dir=root / 'data' / 'catalog')
    official = {item.case_id: item for item in provider.iter_listing_metadata()}
    # The governed universe is 2020-2024 by construction; the filter stays explicit so the
    # audit can record that no blind-cohort row was ever considered.
    blind_excluded = sorted(case for case, item in official.items() if item.cohort_year >= BLIND_COHORT_YEAR)
    for case_id in blind_excluded:
        del official[case_id]
    packets = {path.name for path in (root / 'docs' / 'annotation' / 'gpt_expert_v1_1' / 'case_packets').iterdir() if path.is_dir()}
    pass1 = {path.parents[1].name for path in (root / 'expert_results').glob('*/pass1/expert_annotation_v1.json')}
    audits = {path.parents[1].name for path in (root / 'expert_results').glob('*/audit/financial_resolution_v1.json')}
    rows: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    for case_id in sorted(set(official) | packets | pass1):
        metadata = official.get(case_id)
        packet = _packet_metadata(root, case_id)
        row: dict[str, object] = {
            'case_id': case_id, 'packet_present': case_id in packets, 'audit_present': case_id in audits,
            'pass1_present': case_id in pass1, 'in_official_universe': metadata is not None,
            'official_cohort_year': metadata.cohort_year if metadata else '',
            'official_dataset_split': expected_market_split(metadata.cohort_year).value if metadata else '',
            'annotation_source_year': packet.get('source_year', ''),
            'annotation_dataset_split': packet.get('dataset_split', ''),
            'identity_mismatch': '', 'oracle_buildable': False,
            'failure_reason': '' if case_id in pass1 else 'no_reviewed_gold',
            'effective_annotation_hash': '', 'content_hash': '',
        }
        if case_id in pass1:
            try:
                view = load_risk_gold(root, case_id)
                artifact = build_oracle_document_features(root, case_id)
                row.update(oracle_buildable=True, effective_annotation_hash=view.effective_annotation_hash,
                           content_hash=artifact['content_hash'],
                           identity_mismatch=','.join(_identity_mismatch(artifact, metadata)))
            except Exception as exc:  # noqa: BLE001 - every failure reason is recorded, never dropped
                row['failure_reason'] = _reason(exc)
                failures.append({'case_id': case_id, 'error': row['failure_reason']})
        elif metadata is not None and packet:
            # Not yet annotated: report the mismatch the artifact *would* carry if it were.
            row['identity_mismatch'] = ','.join(_packet_identity_mismatch(packet, metadata))
        rows.append(row)
    return rows, _summarize(rows, blind_excluded, failures)


def _identity_mismatch(artifact: dict[str, object], metadata) -> list[str]:
    if metadata is None:
        return ['not_in_official_universe']
    official = {'cohort_year': metadata.cohort_year, 'dataset_split': expected_market_split(metadata.cohort_year).value}
    return [field for field in IDENTITY_FIELDS if artifact.get(field) != official[field]]


def _packet_identity_mismatch(packet: dict[str, str], metadata) -> list[str]:
    official = {'cohort_year': metadata.cohort_year, 'dataset_split': expected_market_split(metadata.cohort_year).value}
    candidate = {'cohort_year': int(packet['source_year']) if packet.get('source_year') else None,
                 'dataset_split': packet.get('dataset_split')}
    return [field for field in IDENTITY_FIELDS if candidate[field] != official[field]]


def _summarize(rows: list[dict[str, object]], blind_excluded: list[str], failures: list[dict[str, str]]) -> dict[str, object]:
    official = [row for row in rows if row['in_official_universe']]
    buildable = [row for row in official if row['oracle_buildable']]
    packets_official = [row for row in official if row['packet_present']]
    unannotated = [row for row in packets_official if not row['pass1_present']]
    return {
        'audit_version': AUDIT_VERSION,
        'official_universe_count': len(official),
        'blind_2025_accessed': False,
        'blind_2025_rows_excluded': len(blind_excluded),
        'funnel': {
            'case_packets': sum(row['packet_present'] for row in rows),
            'case_packets_in_official_universe': len(packets_official),
            'pass1_present': sum(row['pass1_present'] for row in rows),
            'pass1_present_in_official_universe': sum(row['pass1_present'] for row in official),
            'audit_overlay_present': sum(row['audit_present'] for row in rows),
            'oracle_buildable': sum(row['oracle_buildable'] for row in rows),
            'oracle_buildable_in_official_universe': len(buildable),
        },
        'no_reviewed_gold_count': sum(not row['pass1_present'] for row in official),
        'oracle_coverage_by_official_split': _counts(buildable, 'official_dataset_split'),
        'oracle_coverage_by_official_year': _counts(buildable, 'official_cohort_year'),
        'packet_coverage_by_official_split': _counts(packets_official, 'official_dataset_split'),
        'annotation_opportunity': {
            'official_packets_without_pass1': len(unannotated),
            'by_official_split': _counts(unannotated, 'official_dataset_split'),
            'case_ids': sorted(str(row['case_id']) for row in unannotated),
        },
        'oracle_identity_provenance': {
            'compared_fields': list(IDENTITY_FIELDS),
            'materialized_mismatch_count': sum(bool(row['identity_mismatch']) for row in buildable),
            'materialized_mismatches': {str(row['case_id']): str(row['identity_mismatch']) for row in buildable if row['identity_mismatch']},
            'latent_mismatch_if_annotated': {str(row['case_id']): str(row['identity_mismatch']) for row in unannotated if row['identity_mismatch']},
            'annotation_split_vocabulary': _counts(packets_official, 'annotation_dataset_split'),
        },
        'outside_official_universe': sorted(str(row['case_id']) for row in rows if not row['in_official_universe']),
        'build_failures': failures,
    }


def _counts(rows: list[dict[str, object]], key: str) -> dict[str, int]:
    return {str(value): count for value, count in sorted(Counter(row[key] for row in rows).items(), key=lambda item: str(item[0]))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--output-dir', type=Path, default=Path('reports/oracle_gold_audit'))
    args = parser.parse_args()
    rows, summary = audit(args.root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / 'oracle_gold_coverage.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / 'oracle_gold_coverage_summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    funnel, identity = summary['funnel'], summary['oracle_identity_provenance']
    print(f"packets={funnel['case_packets']} pass1={funnel['pass1_present']} "
          f"oracle_buildable_official={funnel['oracle_buildable_in_official_universe']} "
          f"no_reviewed_gold={summary['no_reviewed_gold_count']} "
          f"by_split={summary['oracle_coverage_by_official_split']} "
          f"identity_mismatch={identity['materialized_mismatch_count']} output={args.output_dir}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
