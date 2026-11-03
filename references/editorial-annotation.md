# 编辑标注叠层

馆藏高清仍是主证据，Ken Burns、长卷慢移、标明的 Seedance 气氛和 Open Montage 编排保持不动。这一层只在旁白需要观众「看见这句话」时叠上去：年份、馆藏署名、短引文，以及偶尔一镜非画作的档案桌。

它不是新的成片风格，计划里不必新写 `style`。趣味艺术史和名画小剧场的镜头上也可以加这一层；不加的计划保持原样。

## 手绘标注：年份、馆藏、引文

上屏的资料句保持短。底部解说字幕继续用已认可的宋体；这一层用常规黑体，圈的是词，不是另一套字幕。

| 计划 `kind` | 画在什么上 | 官方组件（可选） |
| --- | --- | --- |
| `underline` | 年份、年代 | `Underline` |
| `highlight` | 馆藏署名、一句里要停的词 | `Highlight` |
| `circle` | 画里要指认的物，或档案上的一个词 | `Circle` |
| `bracket` | 短引文 | `Bracket` |

对应关系只用于使用者自己的 Remotion 工程。本仓库的 [CitationMark](../assets/editorial-overlay/CitationMark.tsx) 用固定笔划描出同样四种，不安装 `@remotion/rough-notation`。

安装只发生在已经有 Remotion 的工程里，并与该工程现有的 `remotion` 版本对齐：

```bash
npx remotion add @remotion/rough-notation
```

或 `npm install @remotion/rough-notation --save-exact`。不要给版本号加 `^`。本技能仓库没有 Remotion 应用，不把这个包写进依赖。

进度交给旁白，不交给模板自带的整段淡出。`markerDraw` 在词开始那一帧把不透明度设为 1，笔划再按元素时钟描完。`seed` 保持常数，避免笔划每帧乱抖。

```tsx
import {Underline} from '@remotion/rough-notation';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {markerDraw} from './timing';

const frame = useCurrentFrame();
const {fps} = useVideoConfig();
const mark = markerDraw(frame - Math.round(1.2 * fps), fps, 12);
if (mark.opacity === 0) return null;
return (
  <Underline progress={mark.draw} seed={1} color="#c23b32" strokeWidth={8}>
    北宋
  </Underline>
);
```

`role` 为 `year`、`museum-credit`、`quote` 时必须写 `source`（馆方页面或档案 URL）。`label` 只指认画面里看得见的东西，例如「行旅」，不必伪装成出处。引文只覆盖要读的几个字；整句留在旁白。生成镜头已经有 `ai_label`，不再叠馆藏引文。

借鉴的是 Remotion 官方 [`@remotion/rough-notation`](https://www.remotion.dev/docs/rough-notation/api)（MIT）和 [News Article Highlight](https://www.remotion.dev/elements/text/news-article-highlight/) 里「手绘笔划标在一句引文上」的做法。不搬那条新闻标题的版式，也不把画面在结尾淡出。

## 证据桌：只放非画作档案

脚本确实要拿地图、信札、照片或著录扫描说明语境时，可以单独一镜 `purpose: context`。三层是：

1. `desk`：纸色或纸纹底，相机可以在上面平滑移动。
2. `cutout`：档案扫描本身，可加一层很轻的网点，白边留在扫描件上。
3. `occlusion`：前景压住一角，让桌面有前后。要读的字放在最上层。

红线描在扫描件外侧，错开一截，不盖住字。组件是 [EvidenceDesk](../assets/editorial-overlay/EvidenceDesk.tsx)，布局在 [timing.ts](../assets/editorial-overlay/timing.ts)。扫描随这一镜的硬切就在画面里，只有红线在描。把 `<img>` 换成该工程已有的 Remotion `Img` 即可，不必换编排器。

计划里写明 `not_painting: true`，`subject` 写这张档案是什么，不能写成画作标题。主画面素材用 `graphic`，并记下真实来源。没有可引用的扫描，就删掉这一镜，回到原画上讲。

这一层借鉴 [jaredcassoutt/vox-editorial](https://github.com/jaredcassoutt/vox-editorial) `skills/vox-skill`（MIT）的三层桌子、旁白词当时钟、笔划弹簧进入、以及旁白底下的音乐让位。这里只保留这四件事。不复制该仓库的场景、代码绘制的假报纸，也不改用它的配音和合成音乐流程。

## 竖版短讲解里的时间

竖版仍建议 1080×1920。相机用成片帧率（通常 24fps）做平滑缓推或长卷平移；下划线、圈、荧光和红线用大约 12fps 步进，计划里写 `elements_fps`，允许 8–15，并且必须低于 `video.fps`。全部丝滑，或连相机也一卡一卡，都不采用。

| 做法 | 竖版里怎么用 |
| --- | --- |
| 硬切 | 切点跟旁白句读。档案镜和原画镜之间用硬切 |
| 沿红线再切回高清 | `follow_red_line: true` 的下一镜必须是原画 `analysis` |
| 笔划入场 | `entrance: spring`。词一到，字就在；笔划描出来，不靠淡入 |
| 扫描入画 | 随切点直接在，不弹入、不落下 |
| 音乐 | `music_duck: true` 只表示这一镜旁白优先。侧链做法仍按 [声音制作](audio.md)，不新做混音器 |
| 停留 | 要读的字留到读完。圈线落稳后再切 |

推进时长可以落在大约 0.6–1.5 秒，用缓入缓出，不用匀速慢漂凑时长。这些数字来自公开解说片的测量习惯，换一幅画仍要按实际旁白重排。测量来源是 [huashu-art-motion 的 y2_vox 语法卡](https://github.com/alchaincyf/huashu-art-motion/blob/main/references/动画语法/y2_vox.md)。本仓库不复制其中的角色帧、演示片或绘制函数。

口播先录、词界先有，标注的 `start` 等于对应 `vo_words` 的 `start`。还没有词界时可以先不写 `word_id`，配音对齐后再补。

## 不要做

- 不要用代码画出的假档案、假信纸或纸拼贴替换馆藏高清。原画分析镜的主画面仍是 `original`。
- 不要把画作放进证据桌，不要给原画加撕边、网点或胶带。网点只允许出现在非画作扫描上，并且可以关掉。
- 不要撕纸转场，不要每张图都弹入。计划里的 `cut` 只能是 `hard`，`camera` 只能是 `smooth`。
- 不要把 Seedance 或其它生成片段标成原作证据。气氛镜继续写 `AI笔墨延展` 或 `AI想象演绎`，上面不加馆藏引文。
- 不要做成问答闪卡。htlin222/vox-styled-reels 没有标明许可，不复制其代码；网格纸、马克笔字只当作「资料字可以像手写」的方向，本系列资料字仍用黑体，吐槽字仍按 [趣味艺术史](playful-editing.md)。
- 不要复制 Vox 成片、台标黄大底，或花叔角色帧。红线只用在标注和档案镜，不铺成片头底色。

## 计划字段

旧计划不写这些字段就不受影响。骨架见 [editorial-annotation-plan.json](../examples/editorial-annotation-plan.json)。

| 字段 | 要求 |
| --- | --- |
| `annotations[]` | `id`、`kind`、`role`、`text`、`start`、`end`。出处类角色另要 `source`。可写 `word_id` |
| `vo_words[]` | 该镜里被标注的词：`id`、`text`、`start`、`end` |
| `evidence_desk` | `material`（`map` / `letter` / `photo` / `document`）、`layers` 固定为 desk → cutout → occlusion、`subject`、`not_painting: true` |
| `purpose: context` | 只配证据桌。不能当 `analysis` |
| `editorial_timing` | 可选 `camera`、`elements_fps`、`cut`、`entrance`、`follow_red_line` |
| `music_duck` | 可选布尔值 |

`validate_plan.py` 只检查这些形状和「引文不落到生成镜、桌子不托画作、红线之后回到原画」。它不核对年代是否写对，也不渲染笔划。

## 验收

先看原画镜：标注没有挡住要讲的笔触或题款，手机宽度上那几个字仍可读。再看档案镜：扫描是带来源的真材料，三层都在，红线不压字，下一镜已经切回高清原画。生成镜只有 `ai_label`，没有馆藏圈线。

随机抽一帧应和顺序渲染一致。笔划状态只由帧号、帧率和词的起点决定。
