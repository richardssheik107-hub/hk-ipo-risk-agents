## 变更范围

- [ ] Financial Agent
- [ ] Legal Agent
- [ ] Business Agent
- [ ] LLMProvider
- [ ] Verifier / Supervisor
- [ ] 工作流 / Service / UI
- [ ] 标注 / 评测 / 文档

## 契约检查

- [ ] `RiskAgent.analyze()` 仍返回 `list[RiskItem]`
- [ ] 风险码属于 v0.3 注册表且由唯一 owner 生成
- [ ] 正式风险有真实 Evidence；需要计算的风险有可追溯 Calculation
- [ ] 无风险输出有结构化诊断，异常没有被静默吞掉
- [ ] 未把自由文本或任意字典作为公共接口
- [ ] 未提交密钥、本地绝对路径、原始 PDF、缓存或生成结果
- [ ] 公共 Schema 变更仅为兼容扩展，或已说明迁移与审核结果

## 验证

```text
pytest -q：
python scripts/validate_project.py：
python -m compileall -q app src：
git diff --check：
黄金案例/真实案例：
```

## 影响与降级

说明配置注册名称、失败时的 partial/needs_review 行为、仍为 Mock/disabled 的模块，以及是否影响 v0.2 回归。
