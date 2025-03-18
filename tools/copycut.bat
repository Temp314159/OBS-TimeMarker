@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: 切割视频（纯复制流） ::

:: 中文注释末尾加冒号，避免行尾符号处理错误 ::
:: 输入参数 ::
set "input_file=源文件名.mkv"
set "output_file=切割后文件名.mkv"
set "start_time=00:12:34"
set "end_time=01:23:45"
set "video_track=0"
set "audio_track=0"
:: 保留视频1轨+音频1轨，可以自定义添加（index从0开始） ::

:: 处理持续时长 ::
:: -s [开始时间] -i -t [持续时长] 更快，-i -ss -to 要从头开始解码 ::
:: 计算片段持续时长duration ::
:: 将 start_time 转为秒数 ::
:: 可以改成毫秒，懒得了 ::
for /f "tokens=1-3 delims=:" %%a in ("%start_time%") do (
    set /a "start_seconds=(1%%a%%-100)*3600 + (1%%b%%-100)*60 + (1%%c%%-100)"
)
:: 上述代码解释：将 HH:MM:SS 或 HH:MM:SS,MS 转为秒数 ::
:: for /f 循环用于读取文件的每一行或解析字符串 ::
:: 语法：for /f "options" %%variable in (set) do command [command-parameters] ::
:: "options"：指定解析方式，包括分隔符（delims）和要读取的部分（tokens） ::
::      tokens 指定要读取的字段 tokens=1-3 表示读取第1到第3个字段 下文 %%a ~ %%c 表示第1~3个字段（时分秒） ::
::      delims：指定字段分隔符 delims=:., 表示使用冒号（:）、点（.）和逗号（,）作为分隔符 ::
:: %%variable：循环变量，用于存储解析后的值 ::
:: (set)：要解析的内容，这里是变量 %end_time_record% ::

:: /a 用于算术运算 /f 用于解析字符串或命令输出 /p 提示用户输入并赋值 ::
:: 1%%a%% 是在前加1，然后-100消回去，例如02变102再-100得2，以免直接计算02被当做8进制 ::
:: %%a%% 的前2个%是在for循环内需要进行转义，后2个%是为了防止意外的变量解析，实际上 %%a 已经可以了 ::

:: 将 end_time 转为秒数 ::
for /f "tokens=1-3 delims=:" %%a in ("%end_time%") do (
    set /a "end_seconds=(1%%a%%-100)*3600 + (1%%b%%-100)*60 + (1%%c%%-100)"
)
:: 计算 duration 秒数 ::
set /a "duration_seconds=end_seconds - start_seconds"
if !duration_seconds! lss 0 (
    echo End time must be after start time.
    pause
    exit /b 1
)
echo %duration_seconds%
:: 格式化 duration 为 hh:mm:ss ::
set /a "hours=duration_seconds / 3600"
set /a "minutes=(duration_seconds %% 3600) / 60"
set /a "seconds=duration_seconds %% 60"
if !hours! lss 10 set "hours=0!hours!"
if !minutes! lss 10 set "minutes=0!minutes!"
if !seconds! lss 10 set "seconds=0!seconds!"
set "duration=%hours%:%minutes%:%seconds%"
:: %VAR% 和 !VAR! 的不同 ::
:: 前者为即时扩展，后者为延迟扩展 ::
:: 即时扩展是在解析命令行时立即扩展变量的值，延迟扩展是在命令执行时扩展变量的值 ::
:: 简单来说一开始 VAR 是什么， %VAR% 就一直是什么，!VAR! 则会随 VAR 的变化而变，适合在循环/条件中用 ::
:: 延迟扩展需要启用延迟变量扩展（setlocal enabledelayedexpansion） ::
 
:: 计算运行时长 ::
:: 获取起始时间 ::
set "start_time_record=%time%"
echo Start time: %start_time_record%

:: 主体 ::
:: 执行ffmpeg命令 ::
ffmpeg -ss %start_time% -i "%input_file%" -t %duration% -map 0:v:%video_track% -map 0:a:%audio_track% -c copy "%output_file%"

:: 计算运行时长 ::
:: 获取结束时间 ::
set "end_time_record=%time%"
echo End time: %end_time_record%
:: 将时间转换为秒 ::
for /f "tokens=1-3 delims=:.," %%a in ("%start_time_record%") do (
    set /a "start_seconds=(1%%a%%-100)*3600 + (1%%b%%-100)*60 + (1%%c%%-100)"
)
for /f "tokens=1-3 delims=:.," %%a in ("%end_time_record%") do (
    set /a "end_seconds=(1%%a%%-100)*3600 + (1%%b%%-100)*60 + (1%%c%%-100)"
)
:: 计算总耗时并输出 ::
set /a "elapsed_seconds=end_seconds - start_seconds"
if !elapsed_seconds! lss 0 set /a "elapsed_seconds+=86400"
echo Elapsed time: !elapsed_seconds! seconds

endlocal

pause
