# 可视证据对白

风格 id：`evidence-dialogue`。它是《读画》里的一种成片做法，入口仍是本仓库的 [SKILL.md](../../SKILL.md)。默认成片仍是 [经典读画](../style-registry.md)（`ken-burns`）。

## 借什么

Arte 系列《À musée vous, à musée moi》。中文常称「假如名画会说话」或《奇趣美术馆》。节目目录见 [Dada Media：A Musée Vous, A Musée Moi](https://dadamedia.app/catalogue/amuseevousamuseemoi/)。

从这一档借四件事，用在中国画短片上：

- **去神坛**。先问一个观众能在画上核对的问题，不从作者履历讲起。
- **极短**。原片大约两到三分钟。本风格的目标是 **60 秒**（计划允许 45–75 秒，留给配音对齐）。
- **一画多刀**。一整集只对着一件主作品切多刀。对照另一件作品时，沿用 [画面与脚本](../art-direction.md) 的同作者对照，不在这一风格里展开第二件作品。
- **开静收静**。开场是原画静帧，结尾回到原画静帧。中间才运动。

人物对白换成 **可视证据对白**：两处原画局部互相回答，观众能在馆藏高清上核对。Seedance 做气氛、构图演绎和多镜连贯。皴法、颜料、尺寸、题款和印文只来自馆藏原图。

《名画的小秘密》不作为模板。不要改成画中人吐槽、演员扮演或第一人称走进山水。事实仍回到馆藏作品页和高清原图，优先级见 [画面与脚本](../art-direction.md#资料优先级)。

## 一条视觉想法

全集只推进一个能在原画上核对的问题，写入计划顶层 `idea`。旁白、Seedance 运动和两处原画局部都回答这一句。第二处局部是对第一处的回答，不引入新主题，也不把个人履历接到后面。

## 60 秒节拍

下面是计划骨架的时间。配音对齐后可以在 45–75 秒内伸缩，但顺序不变，运动画面的合计时长不少于 24 秒，并且不少于全片的四成。开场静帧、人尺、收束静帧各自至少 4 秒。

| 时间 | `beat` | 画面 | 旁白槽位 |
| --- | --- | --- | --- |
| 0–6 | `open-still` | 馆藏高清静帧。镜头停住。 | 只留一个问题：【观众能在画上核对的问题】。可以出现作品名。 |
| 6–16 | `motion` | Seedance。镜头留在画面平面里。 | 指向气氛或构图。不把生成结果说成皴法、颜料或尺寸。 |
| 16–26 | `motion` | Seedance。与上一镜连贯，仍是同一个想法。 | 第二刀，仍不提供原作证据。 |
| 26–36 | `motion` | Seedance。运动收住，把视线送回原作。 | 一句过渡。 |
| 36–44 | `scale` | 原画全幅，叠 [人尺](../scale-reference.md)。馆方厘米短暂上屏。 | 说明参照是按馆方尺寸示意。 |
| 44–48 | `evidence` | 原画局部，静帧或原图上的短推。 | 【看得见的第一处】。 |
| 48–52 | `evidence` | 同一幅原画的另一局部。 | 【这一处怎样回答上一处】。 |
| 52–60 | `return-still` | 回到开场那一帧或全幅，停住。 | 回到开头的问题。感受最多一句，并写成“本片解读”。 |

人尺放在两处原画细读之前。运动镜头的 `purpose` 是 `atmosphere`，不算这段细读。收静是最后一镜，人尺不放到片尾再补。

开场、人尺和收静使用原画，`camera` 省略或写 `still`。两处证据使用同一件原画，`camera` 可以是 `still` 或 `push-in`。运动镜头的 `camera` 只使用 `picture-plane`、`push-in`、`multi-shot`。

`first-person`、`pov`、`landscape-pov` 不使用。横版 16:9 或竖版 9:16 仍按 [横竖版](../formats.md) 选择；被禁止的是走进山水的主观镜头，不是横屏画幅。

## 可读标识

每段生成画面都带计划字段 `ai_label`，并且这句字要出现在画面上。本风格只接受两句已在《读画》里用过的标识，空格不影响：

- `AI 笔墨延展`
- `AI 想象演绎`

标识做成独立文字层，不要烤进 Seedance 成片，以免改画幅时被裁掉。整段运动期间保持可读，包括首帧、尾帧和短持。验收时看画面，不把计划字段当成已经上屏。见 [剪辑与交付](../editing-delivery.md)。

## 计划里要写的字段

在 [计划格式](../project-format.md) 上增加这些字段。经典计划不写它们。

| 位置 | 字段 | 内容 |
| --- | --- | --- |
| 顶层 | `style` | `evidence-dialogue` |
| 顶层 | `idea` | 一个视觉问题，一句话 |
| 素材 | `generator` | 每条 `ai-video` 写 `seedance` |
| 镜头 | `beat` | `open-still`、`motion`、`scale`、`evidence`、`return-still` |
| 镜头 | `camera` | 见上表。运动镜头必填 |
| 镜头 | `ai_label` | 生成画面使用上面两句之一 |

尺幅镜的 `asset_id` 仍是原画全幅，`purpose` 为 `analysis`。成人剪影另列为 `graphic`，不作为该镜主素材。原画 `notes` 写明尺幅镜头 id、叠加方式和馆方尺寸页面。

骨架是 [evidence-dialogue-plan.json](../../examples/evidence-dialogue-plan.json)。画名和馆藏 URL 仍是占位，不能当成某一件作品的考据或成片。

```bash
python3 scripts/validate_plan.py examples/evidence-dialogue-plan.json
```

## 脚本骨架

旁白按上表的槽位写。配音前的秒数是预估；Seed Audio 出实际时长后再对齐，并保持开静、运动、人尺、两处证据、收静的顺序。

声音沿用 [声音制作](../audio.md)：人声、BGM、音效分轨，讲解时配乐让位。Seedance 不生成人物对白，也不用它的口型。需要环境声时再打开生成音频，这段声音不充当旁白，也不充当证据。

资料、画心、题跋和表面细节的取舍仍按 [画面与脚本](../art-direction.md)。这一风格不放宽“看得见才讲”。

## 成片怎么接进现有时间线

Seedance 的 mp4 记成 `ai-video` 素材。Remotion 里用 `OffthreadVideo` 播放；原画静帧和缓推仍走现有的 `Img` 与 [LongScrollPan](../../assets/long-scroll/LongScrollPan.tsx)。标识、字幕和人尺叠在视频组件外面。

生成入口用已经安装的 OpenMontage 或 YouMind，不在本仓库再抄一套客户端。步骤见 [工具接入：Seedance 成片接入](../tooling.md#seedance-成片接入)。剪映精剪仍是可选的最后一步。
