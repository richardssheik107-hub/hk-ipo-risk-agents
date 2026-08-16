# Retriever V3 Phase C — Table Retrieval Lane

PHASE R3-C RESULT:

PASS

New Lane:
Lightweight table-block retrieval

Development cases:
50

Locked cases:
10

Locked metrics opened:
NO

## Remaining Complete Misses Before Table

Total remaining: 30

- Query Coverage: 10
- Table: 8
- Authority: 6
- Neighbor: 4
- Multipage: 2

重新 audit 后：6 条是真正表格，2 条重分类为普通叙述证据。

## Table Miss Recovery

| Metric | Result |
|---|---:|
| Original taxonomy Table misses | 8 |
| Genuine Table misses | 6 |
| Recovered@10 | 0 |
| Recovered@20 | 0 |
| Recovered@50 | 4 |
| Still Missing | 2 |

原始8条（含2条误分类）的恢复：@10=0，@20=0，@50=4。

### Table Lane raw recall（all Development Gold）

| @10 | @20 | @50 |
|---:|---:|---:|
| 54.69% | 63.19% | 72.40% |

## Variant comparison

| Variant | Policy | Genuine@50 | Overall unique@50 |
|---|---|---:|---:|
| TABLE-A | page_filter | 1 | 4 |
| TABLE-B | block_max | 3 | 6 |
| TABLE-C | block_coverage | 4 | 7 |

Frozen variant: **TABLE-C**。查询与 BM25-B 的 tokenizer/k1/b 均未修改。

## Stage1 Ceiling

| Candidate Sources | Oracle@20 | Oracle@50 | Oracle@100/native |
|---|---:|---:|---:|
| V1∪V2∪V2.1∪BM25 | 83.33% | 91.32% | 94.79% |
| + Table Lane | 85.94% | 93.92% | 96.01% |

Oracle Coverage ≠ Fused Recall；它只表示至少一个 Lane 看到了 Gold。

## Unique Table Contribution

Unique Gold found only after Table Lane: 7

Across IPO cases: 7

Across risks: 2

## Equal-weight RRF

| Fusion | R@5 | R@20 | R@50 | R@100 |
|---|---:|---:|---:|---:|
| Before Table | 53.82% | 73.61% | 86.28% | 93.23% |
| After Table | 54.51% | 75.35% | 87.15% | 94.79% |

Fusion 使用固定 equal-weight RRF，没有按 Gold 调权重。

### Bounded candidate pool

- Mean: 100
- Median: 100
- P95: 100
- Max: 100（cap=100）

Newly recovered Gold in bounded Top100: 12
Lost previous Gold in bounded Top100: 3
Net Gold gain: 9

## Remaining complete candidate misses

Remaining: 23
- QUERY_COVERAGE_MISS: 8
- TABLE_FRAGMENTATION: 2
- SECTION_AUTHORITY_MISS: 7
- NEIGHBOR_PAGE_MISS: 4
- MULTIPAGE_FRAGMENTATION: 2
- OTHER_UNKNOWN: 0

## Cost

- Implementation complexity: MEDIUM
- Runtime overhead: one case-local table-block index; three variants only in this offline experiment
- Memory overhead: case-local only; released after each PDF
- Disk overhead: summary/audit metadata only

## Disk

- Available disk before: 7.83 GiB
- Peak temporary disk: 1358.4 MiB
- Available disk after: 7.83 GiB
- Persistent Table index: NO
- Persistent BM25 index: NO
- Model download: NO
- Temporary PDFs remaining: 0
- Temporary year ZIPs remaining: 0
- Temporary directories: CLEAN

## LOCKED VALIDATION STATUS

Cases: 10

Metrics opened: NO

Gold inspected: NO

Used for tuning: NO

Used for Table design: NO

## Strategic decision

CANDIDATE EXPANSION RECOMMENDATION: **STOP_AND_MOVE_TO_RANKING**

当前 Stage1 Candidate Recall 已达到至少95%，剩余错误少且分散；下一阶段应开始设计 LTR。

Push: NO

Remote GitHub modified: NO

## 简单结论

TABLE LANE PASS。

BM25之后还剩30条正确 Evidence 完全找不到，其中确认有6条属于真正表格问题。轻量 Table Lane 在Top50找回4条，来自4家IPO、覆盖2个risk。Stage1 Oracle native ceiling 从94.79%提高到96.01%。
