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

示例见简化的 [xishan-plan.json](../examples/xishan-plan.json)、保留25镜头时间线的 [early-spring-plan.json](../examples/early-spring-plan.json)，以及 [雪中猎人竖版计划](../examples/hunters-in-snow-portrait-plan.json)。同一作品的不同方向各存一个计划，避免覆盖原版。复制后修改作品、时间、来源与文件路径，不能把案例坐标和素材当作其他画作的依据。

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
