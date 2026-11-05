# 独立 Remotion 渲染

用本片自己的 React / Remotion 入口编排原画、生成片段、转场与文字，再按需要用 FFmpeg 混音、合成字幕和编码。无需 Open Montage 的仓库、Python 包、渲染模板或流程指令；研究、来源、生成任务、声音、原生工程和最终验收仍按本 skill 记录。

## 准备最小环境

需要 Node.js、npm 和可用的渲染浏览器；最终音视频处理需要 FFmpeg / ffprobe。只写脚本、做封面或直接在剪辑器内编辑时，不准备渲染环境。

可复制 [最小运行环境](../assets/remotion-runtime/package.json) 到项目自己的 `render/`，然后在该目录执行 `npm ci`。附带 lockfile 固定依赖；Remotion / CLI 使用本次已验证的4.0.539，React / React DOM为18.3.1，不声称是最新版本。升级时同时更新同组 Remotion 包并验证，不让不同版本混装。参见[官方版本一致性说明](https://www.remotion.dev/docs/version-mismatch)。

```text
project/
  render/
    package.json
    package-lock.json
    tsconfig.json
    remotion.config.ts  # 本地输出设置，不含本机浏览器路径
    node_modules/       # 本项目安装，不提交仓库
    src/index.tsx       # registerRoot，导出自己的 Composition
  assets/               # 实际媒体和字体文件
  props.json            # 本片的尺寸、镜头、字幕等参数
  project.json          # 可选的本 skill 计划
  outputs/
```

需要跨集共享环境时，可以共用一个独立 `render/`，各集入口置于其 `projects/<episode>/` 下，分别传入素材目录与 props。不要把依赖目录指向旧制作框架。入口位于运行环境内，保证 React / Remotion 能从本地 `node_modules` 解析；相对导入的组件也随入口保留目录结构。

首次渲染时 Remotion 可能获取其默认浏览器；已有兼容浏览器时可用 `--browser-executable /path/to/browser` 指定，不必再装另一套浏览器。运行环境附带的 `src/check.tsx` 与 `check-props.json` 只生成两秒移动色块，用于验证连接，不能当作作品制作模板。

## 渲染入口与检查

可以直接使用[官方 render](https://www.remotion.dev/docs/cli/render) / [still](https://www.remotion.dev/docs/cli/still)命令，也可使用标准库脚本 `scripts/render_remotion.py`。脚本只调用已安装的本地 CLI，不通过 npx 隐式安装工具。示例中的路径由使用者替换：

```bash
python3 /path/to/skill/scripts/render_remotion.py \
  --runtime /path/to/project/render \
  --entry /path/to/project/render/src/index.tsx \
  --composition Film \
  --props /path/to/project/props.json \
  --public-dir /path/to/project/assets \
  --output /path/to/project/outputs/visual-clean.mp4 \
  --plan /path/to/project/project.json --check
```

`--check` 只检查本地环境、版本、路径、JSON 与已列计划素材，不启动浏览器或写入输出，不能证明布局或浏览器渲染通过。`--plan` 可省略；传入时调用本 skill 的计划检查，预检不要求尚未生成的交付文件存在，也不会联网下载素材。计划不包含渲染入口的全部取段、变速与图层关系，源片段长度、完整时间线和具体讲解点仍需项目核对。

- 带 `--still-frame 120`，输出改为 `.png`：核对真实字形、构图与媒体加载。
- 带 `--frames 0-47`：按包含首尾的帧范围输出两秒测试视频（本例24fps）。测试动态段时使用对应实际帧范围；短样成功不能代表全片通过。
- 去掉 `--check` / 帧选择参数：渲染整片。默认H.264、CRF18、concurrency1；根据实际环境选择并发，不固定推断机器性能。
- 本机已验证 `--gl swangle`；其他环境按实际浏览器选择，不强制套用。脚本可用 `--browser-executable` 指定已有浏览器。

脚本先写独立临时输出，CLI成功且ffprobe能读取后才落到目标文件；有计划时核对尺寸、视频FPS和时长，选帧渲染按范围计算预期时长。默认拒绝覆盖已有输出和对应日志/报告；需要替换时显式 `--overwrite`。旁边保留 `.render.json` 和 `.renderer.log`，记录实际版本、命令、成功/失败与测量；失败不会用旧文件冒充新结果。

输出目录须在 `public-dir` 外，避免把生成文件反复打包进素材。公开媒体目录使用实际文件；本次符号链接媒体曾出现404。字体加载完成后再释放渲染等待，避免首帧回退字体。

## 分工与迁移

画面底片可以不含人声和烧录字幕，按 [剪辑与交付](editing-delivery.md) 独立输出声音轨和可编辑字幕。声音既可由 Remotion 合成，也可用现有 FFmpeg 脚本；清楚记录实际路线。直接使用 FFmpeg sidechain 的实际单位，不继承旧框架的参数补偿。

旧工程迁移只需要保留本片入口、相对导入、props、素材与字体，放到独立运行环境，通过本脚本或官方 CLI 渲染。先核对代表帧、动态取段与字体，再检查整片。保留旧版本及其真实制作记录，不批量重写旧作品；无需重新生成已选声音、AI片段、封面或剪映工程。

这里的ffprobe探测不是完整解码、闪帧排查、原生字幕预览或主观试听，最终仍按本 skill 的验收与记录执行。

## 迁移验证：2026-11-05

在本机新目录独立安装上述 npm 依赖，使用已有系统 Chrome；没有链接旧框架的依赖目录。补齐 tsconfig 与输出配置后，实际通过两秒48帧移动图形、PNG代表帧、一秒24帧范围测试，以及[《捣练图》22镜时间线](../examples/contemplative/daolian-produced-plan.json)的整片渲染：125.458333秒、1920×1080、24fps、3011帧。复用原有源码、props、素材和字体。

原版与独立渲染结果均完成3011帧解码及比较，视频元数据一致。哈希不是逐帧完全相同：1394帧有像素差异，整片平均SSIM为0.997655。查看第700、1200、2800帧的原版、新版与放大差图，没有观察到构图、字形或人物姿态偏移，差异表现为细纹区域的小像素值变化；未独立确定根因，不宣称逐像素一致。原有最终成片与声音没有替换。

这证明本次独立渲染路线可用，不代表在所有系统上验证过，也不替代新作品的画面、字体和声音检查。
