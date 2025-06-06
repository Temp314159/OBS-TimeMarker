# OBS-TimeMarker
## 简介
在OBS Studio录制视频时，按下设定好的快捷键，弹出窗口，输入内容，给当前时间点打标记，完成录制后输出txt与pbf文件（pbf用于PotPlayer播放器）。

用于录像/直播高能时刻/网课笔记等，方便快速定位/后期切片。

## 使用方法
安装[Python](https://www.python.org/downloads/)

工具-脚本-Python设置，添加Python路径

工具-脚本-脚本-+号，添加OBS_Time_Marker.py脚本文件

### 选项
- 输出文件夹：时间点标记文件的输出路径

- 静默模式：不弹出标记内容输入窗口（标记默认数字）

- 文件-设置-快捷键-添加时间点标记：设置快捷键

## 更新计划
- [x] 静默模式（不弹出标记窗口）
- [ ] 弹出窗口自动置顶（选项可选）（已可置顶，为何无法获取焦点探索中…）
- [ ] 支持英语（已完成文本）
- [ ] 增加更多文件支持（xmp, csv, ... 可参考[Import/export more project files and formats · mifi/lossless-cut](https://github.com/mifi/lossless-cut/issues/1340)）
- [ ] 支持视频文件内嵌chapter标记（可以写一个独立工具实现）
- [ ] 改写为lua脚本，无需预装Python

## 相关项目参考
[derrod/obs-named-chapter-hotkeys](https://github.com/derrod/obs-named-chapter-hotkeys)

[StreamUPTips/obs-chapter-marker-manager](https://github.com/StreamUPTips/obs-chapter-marker-manager)

## 碎碎念
苦OBS没有时间点标记功能久矣，遂于24年2月写此项目，结果OBS在24年7月推出30.2版本，增加了测试版的Hybrid MP4，并内置了快捷键添加chapter的功能。难绷！

所幸OBS自带的chapter标记功能太过简单，自定义标签内容都很难实现，也不算白忙活。github上有其它类似的项目，不过似乎都不提供快捷键弹出窗口输入标签。可恶，为啥不支持这么自然舒服的操作！

tools里面是我常用的2个工具，时间点标记txt转pbf 与 无损切割视频（利用FFmpeg复制流）。由于是无损切割，所以会从切割点自动向前选择最近的I帧，可能不是很准确，需要手动预留空间。（更新：使用具备完善功能与UI的[lossless-cut](https://github.com/mifi/lossless-cut)将更为方便，并且它允许导入pbf等多种章节标记文件。）

有很多贴心的小功能，方便使用，详见代码。窗口是通过 Tkinter 弹出的，虽然容易出兼容性的问题，不过比较灵活。
