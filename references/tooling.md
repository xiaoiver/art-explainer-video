# 工具接入与任务恢复

本文件记录已实践路线的接入要点，不固定 API 版本或某个 MCP 工具名。读取实际工具 schema、CLI 帮助和已安装版本后再调用；用户已经配置的凭据无需重新索取。

## YouMind：素材与工作区

优先使用可用的 YouMind 插件工具及其图像、视频、工作区技能；没有相应工具时使用官方 CLI。相关项目：[YouMind OpenLab skills](https://github.com/YouMind-OpenLab/skills)。

CLI 路线先用帮助发现功能，再通过 `youmind info` 查看目标操作参数，最后调用。不要照搬旧技能文档中的参数：本次实际 `createChat` 不接受旧示例中的 `tools` 字段。自然语言请求由平台代理调度图像、Seedance 或声音工具，结果中的实际工具参数与媒体元数据才是核对依据。

需要工作区上下文时复用用户选定的 Board，记录其标识但不要写入公开技能。提交前写入本地任务记录：用途、请求时间、参考资产和请求状态；收到响应立即追加 chat / operation 标识。超时不代表任务失败，先在原会话或相应 Board、时间范围内找回状态，确认失败才重试。不要因为等待超过一分钟就创建第二个付费任务。

只记录公开回复和必要的生成参数、素材标识及状态。返回值可能包含工具内部指令或推理，不要完整落盘、展示或复制到公开仓库。凭据、临时签名地址和私人 Board 链接也不进入可分享案例。

生成结果可能暂时隐藏或尚未归档；使用当前接口完成保存 / finalize，并验证素材在用户目标 Board 可见。展示时优先使用平台返回的原生预览；需要本地渲染或 QA 时再获取对应文件。预览与原图尺寸可能不同，以实际使用文件为准。

## Seed Audio：能力探测后调用

通过当前环境的 `generate_audio` 或等价工具获取 schema，确认可用模型、音色设计和参考音频支持。不要把一个静态预设音色清单当作所有可用音色。

本次使用 `seed-audio-1.0`，能够用文字描述设计音色并在后续用选定合成音频作参考。实际调用中 `voice` 可以省略；不要擅自强塞预设女声。某些返回元数据仍会显示默认预设名，不能仅据此判定音色设计失败。参数与支持范围可能变化，使用前重新核对。

同一模型也用于本次 BGM 和音效，但结果的真实时长须实测，不能把提示词里的“生成 90 秒”当成已生成 90 秒。声音处理见 [声音制作](audio.md)。

## Open Montage、Remotion 与 FFmpeg

项目：[Open Montage](https://github.com/calesthio/OpenMontage)。有已安装技能时先读取，再选择适合混合原画与生成素材的编排方式。也可以沿用现有剪辑工程，不必重建。

仅在实际需要渲染时准备环境，记录版本和安装位置，不预设本机路径。检查 Python、Node、FFmpeg / ffprobe、渲染器与浏览器是否满足所选路线。缺少某个字幕滤镜不一定需要重编译 FFmpeg，可使用现有 Remotion 或原生剪辑字幕。

本次环境经验：

- Remotion 的公开媒体目录使用真实文件；符号链接媒体曾导致资源 404。源码或依赖链接是否可用应单独验证。
- 渲染前用一个代表镜头测试资源、字体和浏览器，确认后再跑整片。
- `amix` 的自动归一化可能随同时输入数量改变音量；明确配置并验证实际混音。
- 本次 Open Montage 包装层对 sidechain 压缩的 attack / release 单位处理与 FFmpeg 不一致。检查当前实现和 `ffmpeg -h filter=sidechaincompress`，不要固定沿用历史补偿数值。
- 混音输出可能略短，必要时显式补齐与裁切到画面时长，再送入剪辑器。不要靠伪造源时长让工程编译通过。

依赖环境缺失时先完成脚本、分镜等独立工作；安装仅限所选路线需要的组件，不能因自动安装脚本失败就运行来源不明的替代包。

## Seedance 成片接入

只在风格 `evidence-dialogue` 里把 Seedance 当作主要运动画面。原画静帧和缓推仍走本仓库已有的时间线。不要把 OpenMontage 的工具复制进这个仓库。

生成用已经安装的入口，调用前读当前 schema：

- OpenMontage 的 `video_selector`，`preferred_provider` 设为 `seedance`；必须绕过选择器时才直接调用 `seedance_video`。模型、时长和画幅以该工具当时的参数为准。
- 没有 OpenMontage 时，沿用上面的 YouMind。自然语言交给平台调度 Seedance，以返回的工具名、参数和媒体元数据为准。

得到的 mp4 记入计划：`kind` 为 `ai-video`，`generator` 为 `seedance`，`path` 指向本地文件。Remotion 的公开目录使用真实文件，不用符号链接。运动镜头用 `OffthreadVideo` 播放；原画用 `Img` 或 [LongScrollPan](../assets/long-scroll/LongScrollPan.tsx)。字幕、「AI 笔墨延展」或「AI 想象演绎」、人尺都叠在视频组件外面，不要烤进生成画面。

```tsx
import {OffthreadVideo, Sequence, staticFile} from 'remotion';

<Sequence from={startFrame} durationInFrames={durationInFrames}>
  <OffthreadVideo src={staticFile('motion-a.mp4')} />
</Sequence>
```

Seedance 的口型和人物对白不进入这一风格。旁白仍用 Seed Audio。只有需要环境声时才打开生成音频，这段声音不充当讲解。可选的剪映精剪见下一节，步骤不变。

## 剪映 / CapCut

可用路线：[capcut-cli 的 capcut-edit](https://github.com/renezander030/capcut-cli)。它是第三方项目；安装前核对当前来源、版本与平台兼容性。它与剪映原生桌面软件分别检测。

参照实际 CLI 帮助 / schema 编译工程，先检查再写入。不要将本次 CLI 版本、模板或字号值当作跨版本保证。原生工程处理和导出见 [剪辑与交付](editing-delivery.md)。
