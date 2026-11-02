# 音效选材、时码与来源台账

需要新环境音、具体事件拟音，或替换一段“不对劲”的声音时读本页。只改旁白发音或拼接已确认片头时，沿用现有素材，不重新搜音效。

## 从镜头开始选声音

先写声音的作用、真实来源或想象性质、远近、出现时刻与可用长度，再搜索。例：

| 镜头需要 | 可用检索方向 | 排除不合适的候选 |
| --- | --- | --- |
| 鹤群上空的疏远鹤鸣 | `distant crane calls`，再核对物种和录音描述 | 连续高声尖叫、配乐化长音；不能只凭“bird”标签认定是鹤 |
| 水墨山林里轻铺的风 | `gentle wind trees no voices` | 巨大呼啸、交通与人声；不能把普通风声说成宋代实地声景 |
| 人物把纸牌放到桌面 | `single playing card on wooden table` | 长串洗牌、厚重撞击；声音的落点应跟手牌接触桌面 |
| 统一片头字标 | 已确认的系列音效与音乐分轨 | 无需为每集重做或再叠一遍已经混入MP4的声音 |

先比较自己的已用素材和有来源记录的库；纸张、衣料、脚步、器物接触等短拟音，优先考虑合适的外录或自录；难以找到匹配素材、需要想象性音色或定制音乐时，可继续用获授权的生成工具。赏析保持少量声音与观看留白，小剧场可增加动作拟音，包袱也可以靠停顿。声音来源选择不改变用户指定的旁白、配乐或已批准片头。

通过当前可用检索工具或素材平台接口搜索，优先读素材详情页。下载量、评分人数、平均分只是辅助；录音来源、环境、处理方式、长度先决定是否匹配。设备型号不能证明音质好，素材库条目也不自动等于实地录音。若上传者说明为生成内容，保留生成性质。

检索结果少量预选，保留详情页和试听入口。没有听音能力时，可结合描述、波形与能量筛选，明确尚未试听；不要因技术检查通过就写“听起来自然”。需要用户选风格时集中给候选，已有自主制作授权时不把每个音效变成确认点。

## 落点与能量

使用[趣味艺术史剪辑](playful-editing.md)时，声音表对齐贴纸落点、箭头命中、画卡交换和包袱停顿；主击点可以更密，次级装饰不必逐个发声。先建立节奏和远近，再检查多声叠加峰值。

声音表用秒记录：镜头ID、时间窗、声音作用、远近、素材ID、源片段起止、增益、淡入淡出，以及旁白在场时的让位方式。声音允许跨镜头和互相叠加，不照搬主画面“不能留空”的规则；有意无声或不加新音效完全可以。

检查起音、主要能量和尾音，不能只看总时长。例如4秒音频可能前3秒都无声，不适合立即落桌的动作；短促声也不能靠拉长填满长镜头。长环境与BGM循环避开明显乐句中断，交叉淡化按实际片段选择。先试听或分析源片段，再检查混音中的效果；不要把源文件的RMS当作最终混音响度。

复核开头、AI演绎段和正文，按[声音制作](audio.md)检查人声优先、瞬态峰值、音乐避让与最终编码。每个画面平移或文字入场都配whoosh会破坏看画节奏，不作为默认做法。

## 来源与复用

项目内保存原始文件及台账，不依赖检索工具的全局缓存。每条已选声音至少记录：

- 标题、作者/供应商、稳定的素材详情页、取得日期、录音/生成性质；预览文件或原始文件也明确区分。
- 许可证标识和版本、许可链接、核对日期、完整署名或项目使用依据。未知许可不能填成CC0；生成音频记录供应商条款和依据，不擅自标为公有领域。
- 本地原始路径和SHA-256、实测格式与时长、源片段范围、处理参数、选用状态，以及是否实际试听。
- 复用时记录原项目或素材库条目，保留原作者、原许可和原始性质。裁剪、转WAV、加混响、跨集复用均不把生成音改成外录，也不把他人录音改成自己的作品。

公开发布的选材默认优先明确的CC0或可完成署名的CC BY；带NC的素材仅在明确的非商业用途和条件核对后考虑。以实际条目为准；本站免费、可播放或可下载不是使用许可结论。署名可放片尾或可访问的完整来源页，不能因小红书正文不介绍工具就省去必要署名。[Freesound许可与署名说明](https://freesound.org/help/faq/#licenses)

复用库可放在使用者自己的素材目录，包含原音频、台账与处理副本；仓库示例不携带私人链接、密钥、临时签名URL或未获分发许可的声音。保留原始版本，避免覆盖此前已通过的声音。

## 可选声音计划与检查脚本

既有工程可保留自己的表格或JSON，不强制迁移。新增的[声音计划示例](../examples/ruihe-sound-draft.json)是《瑞鹤图》**下一版真实音效选材草案**，没有执行替换、没有候选录音或可下载媒体，也没有把已交付的生成音效改写成实录。

`scripts/validate_sound.py`仅用Python3.9+标准库；涉及媒体探测需要ffprobe，能量分析另需ffmpeg。它不联网检索、下载、生成、混音或修改输入，不会修改代理配置。

```bash
# 草案结构检查，导出可编辑声音时码CSV；未选材/未核许可作为警告
python3 scripts/validate_sound.py examples/ruihe-sound-draft.json \
  --cue-sheet /path/to/cues.csv

# 选材后检查本地文件、格式、实际长度和源片段范围，保留带SHA的项目台账
python3 scripts/validate_sound.py /path/to/sound-plan.json \
  --probe --report /path/to/sound-report.json

# 准备交付时：要求已选素材与已核对来源；分析源片段，导出署名
python3 scripts/validate_sound.py /path/to/sound-plan.json \
  --ready --analyze --report /path/to/sound-report.json \
  --cue-sheet /path/to/cues.csv --credits /path/to/sound-credits.txt
```

时间均为秒，路径相对计划文件目录。最小字段：

| 层级 | 字段 |
| --- | --- |
| 计划 | `schema_version: 1`、`title`、`duration_seconds`、`status: draft/ready`、`usage: public-release/noncommercial`、`assets`、`cues` |
| 素材 | 唯一`id`、`title`、`origin: recorded/generated`、`status: candidate/selected/rejected`、`path`、`source_url`、`author`、`license`、`review`；可另记`provider`、`retrieved_at`、`file_variant`、`processing`、`reused_from` |
| 许可 | `id`、`url`、`reviewed`、`checked_on`；CC BY需完整`attribution`，`self-created`需创作者和`usage_basis`，`provider-terms/custom`需链接和`usage_basis`。这些值需有真实依据，不能为通过校验而填写 |
| 生成来源 | `model`与`generation_record`保存实际模型及生成记录/提示词文件，不从库名推断；`self-created`不用于跳过生成服务条款 |
| 试听 | `review.audition: not-listened/listened`及可选`notes`；校验器不验证或自动改变人工试听声明 |
| 声音提示 | 唯一`id`、`asset_id`、`role: voice/music/ambience/event`、`intent`、`start/end`、`source_in/source_out`；可另记`scene`、`distance`、`gain_db`、`fade_in/fade_out`、`ducking` |
| 循环 | `loop: true`时填写`loop_crossfade`，必须小于源片段一半；`false`时源片段不得长于时间窗。这里检查普通速度的取段，不代做循环或变速 |

- `--check-files`检查被声音提示引用的本地文件并计算SHA-256，不处理未引用候选。
- `--probe`隐含文件检查，探测音轨和实际时长，拒绝超过源音频的取段；不把下载到的HTML文件当作MP3。
- `--ready`或计划`status: ready`隐含`--probe`，要求被引用素材为selected、许可已核对且来源完整；未经试听仍会明确警告，不虚构新确认，也不把核对元数据等同于听感验收。
- `--analyze`隐含`--probe`，解码源片段，报告48kHz立体声工作副本的采样峰值/RMS及相对峰值−40dB的首尾能量位置；全数字静音报错。它不测最终混音LUFS/真峰值，也不能判断警报感、物种、发音或录音真伪。
- `--credits`隐含ready检查，只为被引用素材输出台账中已有的署名与依据，不自动推断许可。
- `--report`保留源计划、测量与错误；验证失败不导出CSV或署名，退出码为1。成功为0，只表示所列检查通过。输出路径不得覆盖计划或源音频。
- 草案允许待定素材与未知许可并提出警告；待定不等于已获许可。CSV可作工作表，正式剪辑时码仍随实际旁白和声音校正。

## 借鉴范围

选材思路参考[vibe-motion/sound的公开skill](https://github.com/vibe-motion/sound/blob/main/SKILL.md)与[公开实现](https://github.com/vibe-motion/sound/blob/main/scripts/sfx.py)，本仓库独立实现声音表和台账校验，没有复制对方脚本、媒体或附带推广流程。

2026-11-02评估时，其公开实现主要搜索Freesound并下载MP3预览；不将仓库简介中的其他素材库、BGM或混音宣传视为已接入。网页解析可能随站点变化，现有连接器或官方接口可用时优先使用；网络失败记录具体限制，不默认运行作者机器的Clash修复脚本。
