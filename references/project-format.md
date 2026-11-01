# 可选计划文件

`scripts/validate_plan.py` 只读检查以下轻量格式。它不是 Open Montage 或剪映的输入 schema；既有工程可以保留自己的格式，不必为了本 skill 重建。下列时间单位均为秒。

| 字段 | 含义 |
| --- | --- |
| `schema_version` | 当前为 `1` |
| `artwork` | 对象，`title` 与 `sources`（公开资料 URL 数组） |
| `video` | `width`、`height`、`fps`、`duration_seconds`；可选 `orientation` 为 `landscape`、`portrait` 或 `square`，须与宽高一致 |
| `cover` | 可选；`width`、`height`，单独指定比例 |
| `assets` | 对象数组；`id` 唯一，`kind` 是 `original`、`ai-image`、`ai-video`、`audio` 或 `graphic`；可选 `path`、`source_url`、`notes` |
| `shots` | 对象数组；`id` 唯一，`start`、`end`、`asset_id`、`purpose`（`analysis`、`atmosphere`、`title`）；生成画面增加非空 `ai_label` |
| `deliverables` | 可选；`video` 与 `cover` 的本地路径 |

素材路径和交付路径相对于计划文件目录解析，也接受执行者自己的绝对路径。计划中不要放密钥、临时签名 URL；公开案例仅含公开资料链接。

每个 `shot` 表示主画面，允许为转场短暂重叠；字幕、图形叠加和声音轨仍保留在实际编辑工程中。时间线不得有未覆盖的空段。`analysis` 指对原作视觉证据的讲解，引用 `original`；生成画面应用于延展。脚本检查这种标记关系，不判断讲解事实是否正确。

尺幅示意镜头记成时间线上的一镜：`asset_id` 仍引用原画全幅的 `original` 素材，`purpose` 为 `analysis`。成人、门或手机轮廓在实际编辑工程中叠加；可将轮廓另列为 `graphic` 素材，但不要把它用作该分析镜头的主素材。在所引用 `original` 的 `notes` 写明尺幅镜头 ID、叠加方式和馆方尺寸页面。计划检查不判断对照是否符合厘米比例，也不能代替 [画面与脚本](art-direction.md) 里的尺幅要求。

示例见简化的 [xishan-plan.json](../examples/xishan-plan.json)、保留25镜头时间线的 [early-spring-plan.json](../examples/early-spring-plan.json)，[雪中猎人竖版计划](../examples/hunters-in-snow-portrait-plan.json)，[汉宫春晓图20镜计划](../examples/hangong-chunxiao-plan.json)，实际132秒的 [富春山居图22镜计划](../examples/fuchun-shanju-plan.json)，以及尚未制作的 [千里江山图12镜计划](../examples/qianli-jiangshan-plan.json)。长卷开场的原画慢移可记作 `title`，尺幅及后续原作讲解仍为 `analysis`；平移本身不属于 AI 动态。同一作品的不同方向各存一个计划，避免覆盖原版。复制后修改作品、时间、来源与文件路径，不能把案例坐标和素材当作其他画作的依据。

```bash
python3 scripts/validate_plan.py examples/xishan-plan.json
python3 scripts/validate_plan.py /path/to/project.json --check-files
python3 scripts/validate_plan.py /path/to/project.json --check-files --probe
```

- 默认只检查结构、主画面覆盖、引用、原画分析标记和 AI 标记，输出 JSON，包含错误、警告及视频 / 封面比例。缺少本地路径可在计划阶段保留为警告。
- `--check-files` 要求每个已列素材都有存在的本地文件；配置了交付路径时也检查存在。远程 URL 不会自动下载。
- `--probe` 隐含 `--check-files`，调用 `ffprobe` 检查交付视频的实际分辨率、帧率、时长，以及封面像素。要求交付视频路径；配置了封面尺寸时也要求封面路径。
- 视频时长容差为 0.25 秒，帧率容差为 0.02 fps，允许常见封装尾部。它不检查像素宽高比、声音内容、解码完整性、字幕或图像语义，完整验收仍按 [剪辑与交付](editing-delivery.md) 进行。
- 返回码 `0` 表示这些检查没有发现错误，`1` 表示存在错误；警告不阻止计划继续完善。没有输出“整片验收通过”的含义。

## 可选人物喜剧记录

选择 [名画喜剧模式](talking-painting-comedy.md) 时，在同一个计划增加 `performance`，基础素材、镜头和交付字段不变。它是独立的表演记录，不用新增顶层 `style`，也不套用可视证据对白的节拍。现有计划不需要补字段；普通 `validate_plan.py` 不检查人物表演。

| `performance` 字段 | 含义 |
| --- | --- |
| `mode` | `talking-painting-comedy` |
| `premise`、`detail`、`conflict`、`payoff` | 一句情境、原画细节、人物目的如何相撞、如何回扣；均为非空文字 |
| `characters` | 至少两名角色，各有唯一 `id`、`painting_location`、`want`、`tactic`、`voice`；身份和动机的虚构范围另写清 |
| `facts` | 至少一个知识点，各有唯一 `id`、`claim`、公开 `source_url`、`accessed_on`（YYYY-MM-DD）、`original_location`、`evidence_shot_id`；证据镜头引用 `original` 且为 `analysis` |
| `lines` | 每句有唯一 `id`、`shot_id`、`speaker`（角色 id）、`text`、`delivery`、全片秒数 `start` / `end`、`kind`（`fiction` / `fact`）、`framing`（`on-screen` / `off-screen`）；事实句另列非空 `fact_ids` |

一句话同时含事实与包袱时标 `fact` 并列出事实引用；这不表示包袱也有史料依据。仅虚构的句子标 `fiction`。每条已列事实至少关联一句台词；片头尺寸等资料卡仍在镜头 `notes` 记录来源、访问日期和布局。

台词时间须落在其镜头内；当前检查器按一镜一句的工作流拒绝对白重叠。至少两名角色须有 `on-screen` 台词，对应 `ai-video` / `atmosphere`，不能在原画证据上假做口型。生成主画面标记需包含可读的 `AI 想象演绎` 或 `AI dramatization`；实际剪辑再叠加“原创虚构对白”。未改动原画可承接 `off-screen` 角色声音。

```bash
python3 scripts/validate_comedy.py examples/american-gothic-comedy-plan.json
python3 scripts/validate_comedy.py /path/to/project.json --check-files --probe
```

独立检查器复用基础计划检查，并增加上述表演关系检查；参数、路径解析与退出码沿用基础检查器。它不下载、生成或渲染媒体，不核实来源网页内容，也不证明幽默、音色、口型、标记可读性或实际节奏合格。
