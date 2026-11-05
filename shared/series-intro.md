# 「名画开小差」统一片头

这是用户在2026-11-01确认的系列识别，不是所有画作视频的默认品牌。制作本系列续集时，优先用已确认文件；别为接一集正片重做片头、音乐或角色。

## 直接复用

仓库自带：

- [4秒完整版](../assets/series-intro/intro-4s-v2.mp4)：1920×1080、24fps、96帧。
- [1.5秒短版](../assets/series-intro/intro-short-v2.mp4)：1920×1080、24fps、36帧，独立剪辑了音乐与动作窗口。
- [音乐](../assets/series-intro/music.wav)和[音效](../assets/series-intro/sfx.wav)：4秒独立WAV。

MP4 已有混音，直接放入时间线即可；不要再叠加分轨而使声音加倍。短版带有自身混音，不能直接把4秒声音裁1.5秒代替。竖版或其他比例需重新构图，这两支文件仅适合16:9，不拉伸或居中硬裁三幅画框。

给已有成片加片头，保留原文件，输出新版本；原生工程另行修改才算同步，外部拼接文件不称新剪映原生导出。正片字幕已烧录时会跟画面整体移动；伴随SRT也要顺延，不能再重复烧一次。

可用随附脚本接入已经导出的正片：

```bash
python3 scripts/prepend_intro.py \
  --episode /path/to/episode.mp4 \
  --output /path/to/episode-with-intro.mp4 \
  --subtitles /path/to/episode.srt
```

默认使用完整版、6帧叠化，保持正片尺寸和帧率，另写同名SRT和JSON报告。`--intro assets/series-intro/intro-short-v2.mp4`可换短版，`--overlap-frames 0`可硬切，`--dry-run`只读媒体并显示计划。需要FFmpeg/ffprobe；输入不改写，已有输出会拒绝覆盖。该脚本仅做片头拼接，不做竖版重构或剪映工程同步。

以本集24fps为例：4秒片头减去6帧重叠，正片起点为3.75秒；27.5秒正片得到31.25秒、750帧，SRT统一加3.75秒。不能把字幕一律加4秒。换短版或重叠长度后重新计算。

## 视觉和节奏

- 炭黑小剧场，三幅旧金色画框。人物保留油画笔触，偷瞄、探手，和真人复景正片区分。
- 画框依次入场，约2秒起收拢到上方，再出现标题，避免大画框尚未让位时文字盖住人物。
- 主标题是准确排字的思源宋体CN SemiBold（600），170px；在1920×1080画布上，文字容器左侧518px，五字横向位置为`[0,184,376,542,706]`。后面三个字稍紧。
- 出字帧为`[58,62,66,70,77]`。“差”字旧金色、迟到、落定后约-2.2度；配轻木响。其余字暖白，字形保持原比例。
- 这是本版坐标，不直接套到新画幅。源代码见[Remotion入口](../assets/series-intro/source/index.tsx)及同目录的props。

## 素材生成与可编辑源

本版实际生成一次GPT Image 2角色整版图、一次Seedance 2.0四秒无声动态、两次Seed Audio 1.0（音乐与拟音各一次）。三幅画分别取《戴珍珠耳环的少女》《蒙娜丽莎》《美国哥特式》的绘画形象；源图用均匀洋红背景隔开画框，便于分层。正式片头使用真实生成动态，不是开发用静态样张。

Seedance源视频实测1280×720、24fps、97帧；只用前96帧。按三分区域拆出透明角色层，输出ProRes4444。QTRLE曾在本次Remotion解码失败，故改用ProRes4444；换渲染器先检查透明通道兼容性，不能只改扩展名。

仓库带可直接用的MP4、分轨与小体积源码，不包含约100MB的三条ProRes透明母版或12MB字体。只改拼接不需要这些文件。要重渲染/换角色时，准备`left-alpha.mov`、`middle-alpha.mov`、`right-alpha.mov`、`mix.wav`、`mix-short.wav`，按props填写真实尺寸与主体可见高度，并准备`fonts/SourceHanSerifCN-SemiBold.otf`及许可。不要把此源目录称作无需外部素材的完整渲染包。

字体从[Adobe官方仓库](https://github.com/adobe-fonts/source-han-serif)获取，遵守其中SIL OFL许可；随项目分发字体时保留版权和许可。源码以`FontFace + delayRender`等待加载，失败会中止，不能用系统回退冒充准确字体。2026-11-01实际运行环境为Remotion / @remotion/cli 4.0.539、React / react-dom 18.3.1；源码可在使用者现有Remotion工程内运行：

```bash
npx remotion render assets/series-intro/source/index.tsx MinghuaIntro \
  /path/to/new-intro.mp4 \
  --props=assets/series-intro/source/props.json \
  --public-dir=/path/to/your-intro-assets
```

公开媒体目录放真实文件。本次符号链接造成404，改为实体拷贝后成功；这不是字体或模型故障。完整本地母版包在原制作项目中另存；不把私人Board标识、下载链接或本机目录写入仓库。

## 声音标识

音乐源8.544秒，拟音源7.416秒。把音乐音符之间的空白缩短，未整体变调或变速；七个音符在本版24fps的`[4,18,34,46,57,65,79]`帧。木框轻响在4、22、38帧，衣料声27帧，迟到落点79帧。

完整版最终AAC测得-19.35 LUFS、-2.37 dBTP；以此检查与各集声音的衔接，不把读数当作主观听感验收。后续接正片先听转场，再决定淡化，别把整段主对白一并压低。素材由本项目新生成与编排，没有使用Amusee节目片头或配乐。
