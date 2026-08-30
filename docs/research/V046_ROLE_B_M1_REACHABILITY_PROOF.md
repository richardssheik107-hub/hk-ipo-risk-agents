# Role-B M1 可达性治理证明

状态：`INTERNAL_G2_PROVENANCE_CEILING_CONFIRMED`

## 结论

在当前冻结的 Existing-Gold Metric-v2 与 Catalog 文档版本绑定下：

```text
M1 总单元                         = 102
80% 门槛所需正确数                = 82
已证明受来源版本绑定影响的 M1 单元 = 21
最大合法正确数                    = 81
最大合法比例                      = 79.41%
内部 G2 的 80% 目标可达            = false
```

这是一项项目内部冻结协议下的 provenance 结论，不表示赛事方已独立裁定官方指标上限。当前 G2 仍以已冻结实测结果为准：Real-LLM M1 为 `61/102 = 59.80%`，offline M1 为 `70/102 = 68.63%`，均未通过。

## 证据链

14 个 2022 Development 案例的 Catalog 绑定文档为繁体中文版本，而 Existing-Gold 的 27 条 primary Evidence anchor 来自对应英文版本。官方 HKEX 中英版本关系已在 `v046_source_unlock_provenance.json` 中记录。

需要区分两个事实：

- 21 个风险事实本身可从中文来源恢复，不能说“中文文档没有这些风险”；
- 冻结 Metric-v2 要求 M1 正确单元至少命中一条 Existing-Gold Evidence，而这 27 条英文 exact anchor 不存在于当前绑定的中文字节中。

因此，在不更换 Catalog 来源版本、不修改 Existing Gold、不翻译或注入 Gold 文本的前提下，这 21 个 M1 单元不能满足当前冻结的 exact-Evidence 绑定条件。

最终发布产物也与该判断一致：

| 冻结结果 | 受影响 M1 单元 | 正确 | Evidence hit |
|---|---:|---:|---:|
| Real-LLM gated | 21 | 0 | 0 |
| Deterministic offline | 21 | 0 | 0 |

## 受影响单元

| 案例 | Primary M1 单元 |
|---|---:|
| `ipo_2022_00314` | 1 |
| `ipo_2022_00816` | 1 |
| `ipo_2022_01204` | 1 |
| `ipo_2022_01406` | 1 |
| `ipo_2022_01880` | 2 |
| `ipo_2022_02145` | 1 |
| `ipo_2022_02372` | 1 |
| `ipo_2022_02407` | 1 |
| `ipo_2022_02602` | 2 |
| `ipo_2022_06610` | 3 |
| `ipo_2022_06698` | 2 |
| `ipo_2022_06922` | 2 |
| `ipo_2022_09863` | 1 |
| `ipo_2022_09886` | 2 |
| **合计** | **21** |

## 计算

当前冻结 M1 分母为 102，80% 通过线需要至少 82 个正确单元：

```text
ceil(102 * 0.80) = 82
102 - 21 = 81
81 / 102 = 79.4117647%
```

没有把任何不确定单元当作不可能，也没有把 11 个 concentration implementation gap 从上限中扣除。后者仍属于实现可恢复问题，但 submission freeze 下不得继续修改算法。

## 治理边界

如在赛后或经正式治理批准重新评价，只有以下两类动作能解决来源绑定问题：

1. 把对应官方多语言版本作为独立、可追溯文档重新冻结，并重新生成 parser/evidence provenance；
2. 更正 Existing-Gold 的 evaluation provenance，使 anchor 与其实际标注来源版本一致。

当前提交冻结不执行上述动作。禁止用翻译 Evidence、Gold-text runtime injection、公司/股票/页码特判或放松 Verifier 伪造通过。

机器可读证明位于 `docs/research/v046_role_b_governance/m1_reachability_proof.json`。
