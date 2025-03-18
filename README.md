# OBS-TimeMarker
## 简介
在OBS Studio录制视频时，按下设定好的快捷键，弹出窗口，输入内容，给当前时间点打标记，完成录制后输出txt与pbf文件（pbf用于PotPlayer播放器）。

（用于录像/直播高能时刻/网课笔记等，方便快速定位/后期切片。）

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
- [ ] 弹出窗口置顶化（选项可选）
- [ ] 支持英语（已完成文本）
- [ ] 增加xmp文件支持
- [ ] 支持视频文件内嵌chapter标记（可以写一个独立工具实现）
- [ ] 改写为lua脚本，无需预装Python

## 相关项目参考
[derrod/obs-named-chapter-hotkeys](https://github.com/derrod/obs-named-chapter-hotkeys)

[StreamUPTips/obs-chapter-marker-manager](https://github.com/StreamUPTips/obs-chapter-marker-manager)

## 碎碎念
1年前写的项目，方便录视频用。OBS在2024.07推出30.2版本后，内置了Hybrid MP4的chapter标记，实现了部分功能。不过一些需求仍未实现（自定义标签内容、输出非内嵌文件），github上其它项目也不符合需求，操作比较繁琐。

tools里面是我常用的2个工具，时间点标记txt转pbf 与 无损切割视频（复制流），由于是无损切割，所以会从切割点自动向前选择最近的I帧，可能不是很准确，需要手动预留空间。
