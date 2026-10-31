# 风格登记

《读画》的成片风格写在计划的 `style` 里。这里只登记风格，不另建技能。机器可读的同一份名单是 [style-registry.json](style-registry.json)，`scripts/validate_plan.py` 读取它。新增或改名时，JSON、本页和对应说明一起改。

| id | 名称 | 何时使用 |
| --- | --- | --- |
| `ken-burns` | 经典读画 | 默认。原画静帧缓推、局部讲解，生成片段只作短气氛。 |
| `evidence-dialogue` | 可视证据对白 | 约 60 秒的中国画短片。Seedance 承担主要运动画面。说明见 [可视证据对白](styles/evidence-dialogue.md)。 |

## 经典读画 `ken-burns`

不写 `style`，或明确写成 `ken-burns`，都按这一档检查。检查项与原先相同：结构、时间覆盖、`analysis` 必须引用原画、生成画面必须有非空 `ai_label`。

这一档不要求 `idea`、`beat`、`camera` 或 `generator`。已有的溪山、早春、雪中猎人、汉宫、富春山居、千里江山计划不必补字段。计划里如果多写了这些字段，经典检查会忽略它们，不因此失败。

原画缓推仍用静帧和时间线位移。它不是 Seedance 成片，也不把生成画面当作笔法证据。

## 可视证据对白 `evidence-dialogue`

向 Arte《À musée vous, à musée moi》借节奏，改成约 60 秒、以馆藏原图和 Seedance 运动镜头完成的中国画短片。字段、节拍和禁止事项见 [风格说明](styles/evidence-dialogue.md)。计划检查只在 `style` 写成这一 id 时加严；写错 id 会失败，不会被悄悄当成经典读画。
