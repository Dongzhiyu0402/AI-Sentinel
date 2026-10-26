# 验证台账

> 用途：误报率、召回率与试用反馈的原始记录。答辩时可复现，禁止编造数据。

## 目录

| 文件 | 内容 |
|---|---|
| `false-positives.csv` | 误报抽检（50 条命中，双人判定 + 第三人裁定） |
| `recall-cases.md` | 10 篇公开处罚案例的召回测试 |
| `trials.csv` | 有效试用记录（匿名编号，不含个人信息与原文） |

## 判定规则（写死，避免上线后各自解释）

- **误报**：随机抽 50 条命中；两名评审独立判定"该命中在原语境是否成立（有明确依据且确实构成风险）"；不一致由第三人裁定。误报率 = 不成立条数 / 50。
- **召回**：取 10 篇公开处罚案例中的违规表述，逐篇体检；命中 ≥1 条 high 记为通过，目标 ≥7/10。
- **有效试用**：24 小时内提交 ≥2 次检测，且至少 1 次复制了建议或标记"已按此修改"。
- **免检口径**：被豁免规则降级（`downgraded_by_exempt=true`）的条目单独统计，不计入误报率，避免把"引用法条被降级"误算成误报。
- **隐私**：只记录匿名编号、时间、计数与判定；不记录原文、不记录 IP、不记录联系方式。

## 表头

`false-positives.csv`

```csv
id,date,rule_id,category,matched,context_hash,reviewer_a,reviewer_b,arbiter,downgraded_by_exempt,final_verdict,note
```

`trials.csv`

```csv
participant_id,date,checks_24h,copied_or_adopted,feedback_useful,feedback_false_positive,willingness_to_pay,note
```

`recall-cases.md`

```markdown
## 案例 01
- 来源：
- 违规表述：
- 期望命中规则：
- 实际命中：
- 结果：通过 / 未通过
```
