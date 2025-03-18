# -*- coding:utf-8 -*-
# based on python 3.9
# 2024/02/02 21:02
# by L.P.
# beta 1.0

"""
重要：OBS脚本不能命名为test.py，否则无效，原因未知
测试了老半天才发现是这个问题，坑爹
"""
# 原本打算做个语言选择或者根据环境语言自动适配，算了，懒，直接写一个本地化的dict，然后默认设置en或者zh，分成不同文件得了
# 在文档里搜索output、txt等，再深入学习，看看能否获取输出文件名，以及直接获取输出文件frames数，然后通过fps计算出时间点，不过这个没太所谓，因为精准度要求不高
# 另外，考虑增加xmp与嵌入章节功能，可以写一个额外的来提取章节与嵌入章节，lua就写一个最简单的

import obspython as obs
import datetime
import os
import sys
import time
import tkinter as tk
# from tkinter import font  # 好像不这么写会出问题
from pathlib import Path
import threading  # 多线程，方便通信


# import multiprocessing  # 多进程，内存是独立的，通信比较麻烦，暂时用不上

# 脚本配置类
class LabelRecorder:
    def __init__(self):
        # 参数
        # 设置
        self.hotkey_id = None  # 快捷键ID
        self.hotkey_array = None  # 快捷键（默认无）
        self.output_dir = "D:\\OBS_labels"  # 默认输出目录
        self.is_simp = False  # 静默模式
        self.hotkey_save_key = None  # 快捷键配置存储键
        self.base_filename = "default_filename"  # 基础文件名
        # 文件名
        self.txt_path = None
        self.pbf_path = None
        # 标签与时间
        self.labels = []  # 存储标签的列表（这是线程共享的list，更改时必须用thread_lock）
        self.rec_start_time = None  # 录制开始系统时间
        self.paused_duration = 0  # 累计暂停时长
        self.last_pause_time = None  # 上次暂停时间
        # 线程相关
        self.thread_lock = threading.Lock()  # 线程锁，更改label与写入文件时用，避免冲突
        self.threads = []  # 执行的线程
        self.window_lock = threading.Lock()  # 更改windows时用
        self.windows_n_close_events = dict()  # key是正打开的窗口，value是对应的关闭信号（这是线程共享的，更改时必须用window_lock）

    # 录制相关参数初始化
    def record_attr_init(self):
        # 文件名
        self.txt_path = None
        self.pbf_path = None
        # 标签与时间
        self.labels = []  # 存储标签的列表
        self.rec_start_time = None  # 录制开始系统时间
        self.paused_duration = 0  # 累计暂停时长
        self.last_pause_time = None  # 上次暂停时间
        # 线程相关
        self.threads = []  # 执行的线程
        self.windows_n_close_events = dict()  # 打开的窗口

    # 日志输出（带时间戳）
    @staticmethod
    def log(message):
        # debug时使用，嫌烦或者浪费资源可以改pass
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        obs.script_log(obs.LOG_INFO, f"[{timestamp}] {message}")

    # 时间相关
    # 获取当前视频时间（毫秒）
    def get_current_video_time_ms(self):
        # 检查是否录制
        if not self.rec_start_time:
            self.log("未开始录制，无法获取时间")
            return None

        # 考虑暂停期间获取
        if self.last_pause_time is None:
            now_time = obs.os_gettime_ns()
        else:
            now_time = self.last_pause_time
            self.log("当前为暂停状态，当前时间点校正为暂停时间点")

        # 计算总时长（毫秒）
        total_duration = self.real_duration_ms(now_time)

        return total_duration

    # 获取实际视频时长（当前时间点需校正）
    def real_duration_ms(self, now_time):
        return int((now_time - self.rec_start_time - self.paused_duration) / 1000000)

    # 生成时间字符串（hh:mm:ss.sss）
    @staticmethod
    def format_time_ms(ms):
        hours = ms // 3_600_000
        ms %= 3_600_000
        minutes = ms // 60_000
        ms %= 60_000
        seconds = ms // 1_000
        milliseconds = ms % 1_000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    @staticmethod
    def format_time_ns(ns):
        return LabelRecorder.format_time_ms(ns // 1000000)

    # 文件相关
    # 创建唯一文件名（重名则重命名）
    def get_unique_filename(self, ext):
        base_path = Path(self.output_dir) / self.base_filename
        counter = 0
        while True:
            suffix = f" ({counter})" if counter else ""
            full_path = base_path.parent / f"{base_path.name}{suffix}{ext}"
            if not full_path.exists():
                return full_path
            counter += 1

    # 写入文件
    def write_files(self, mode="w"):
        """
        call时必须用thread_lock，避免写入冲突
        """
        if not self.labels:
            self.log("没有标签，跳过文件写入")
            return  # 没有标签时不创建文件

        # 确保目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        try:
            # 文件路径
            txt_path = self.txt_path if self.txt_path else self.get_unique_filename(".txt")
            pbf_path = self.pbf_path if self.pbf_path else self.get_unique_filename(".pbf")

            # 完整覆盖写入
            if mode == "w":
                # 写入TXT文件
                with open(txt_path, "w", encoding="utf-8") as f:
                    for idx, (ms, text) in enumerate(self.labels):
                        time_str = self.format_time_ms(ms)
                        f.write(f"{idx} {time_str} {text}\n")
                self.log(f"成功覆盖写入TXT文件: {txt_path}")
                # 写入PBF文件
                with open(pbf_path, "w", encoding="utf-8") as f:
                    f.write("[Bookmark]\n")
                    for idx, (ms, text) in enumerate(self.labels):
                        f.write(f"{idx}={ms}*{text}*\n")
                self.log(f"成功覆盖写入PBF文件: {pbf_path}")

            # 在单次标签写入时使用追加模式，保证异常打断时仍能尽可能保存标签，不过写入顺序是确认顺序而非触发顺序，异常打断时标签排序不一定正确
            elif mode == "a":
                # 复用参数
                idx = len(self.labels) - 1
                ms, text = self.labels[-1]
                time_str = self.format_time_ms(ms)
                # 首次写入，添加[Bookmark]
                if idx == 0:
                    with open(pbf_path, "w", encoding="utf-8") as f:
                        f.write("[Bookmark]\n")
                # 写入TXT文件
                with open(txt_path, "a", encoding="utf-8") as f:
                    f.write(f"{idx} {time_str} {text}\n")
                self.log(f"成功追加写入TXT文件: {txt_path}")
                # 写入PBF文件
                with open(pbf_path, "a", encoding="utf-8") as f:
                    f.write(f"{idx}={ms}*{text}*\n")
                self.log(f"成功追加写入PBF文件: {pbf_path}")

            else:
                self.log(f"写入文件失败: 写入参数错误")

        except Exception as e:
            self.log(f"写入文件失败: {str(e)}")

    # 弹出标签输入窗口
    def input_label_dialog(self, current_time_str, close_event=None):
        """
        返回输入的string
        """

        # 窗口大小位置（屏幕居中）
        def center_window(width, height):
            # 获取屏幕宽高，计算窗口居中的 xy 坐标
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            # 设置窗口的位置和大小
            root.geometry(f"{width}x{height}+{x}+{y}")

        # 关闭窗口
        def close_window():
            """
            不论在何种情况下都必须通过该函数关闭窗口，避免意外
            """
            nonlocal is_closed
            '''
            if not is_closed:
                root.quit()  # 用destroy（关闭窗口释放资源但不结束mainloop）可能出现异常阻塞，所以用quit（结束mainloop）
                self.log(f"关闭窗口{current_time_str}完成")
            else:
                self.log(f"窗口{current_time_str}已关闭，关闭被重复调用")
            '''
            if is_closed:
                self.log(f"窗口{current_time_str}：已标记关闭，关闭被重复调用")
            try:
                root.quit()  # 测试发现用 is_closed 控制1次关闭可能出现没成功关闭的情况，不如每次都try，保证关闭成功
            except Exception as e:
                self.log(f"退出窗口{current_time_str}出错: {str(e)}")
            on_close()

        def auto_check_close():
            """
            通过外部信号关窗，目前仅用于结束录制时
            """
            nonlocal close_event
            while not close_event.is_set() and not is_closed:  # 循环检查关闭信号
                time.sleep(0.1)  # 短暂休眠，避免占用CPU资源
            # if not is_closed:
            #    close_window()  # 关闭窗口
            close_window()  # 保证关闭成功
            self.log(f"窗口{current_time_str}：检测到关闭信号，已关闭")

        # 操作反馈
        def on_close():
            # 关闭窗口后执行的最终处理
            # 比如点击叉叉会直接关窗口，不适合绑定到cancel（叉叉绑定到这里后，点击叉叉不会关窗了，难道是替换掉了关闭方法？）
            # 不过叉叉会相当于confirm而不是cancel，但是无伤大雅
            nonlocal is_closed
            if root in self.windows_n_close_events:
                with self.window_lock:
                    del self.windows_n_close_events[root]
            is_closed = True
            self.log(f"窗口{current_time_str}：触发关闭事件")

        def on_confirm():
            # 确认
            self.log(f"窗口{current_time_str}执行确认操作")
            nonlocal input_value  # nonlocal表示上层作用域变量
            input_value = entry.get()  # 获取输入框的内容
            close_window()  # 关闭窗口
            self.log(f"窗口{current_time_str}执行确认操作完成")

        def on_cancel():
            # 取消
            self.log(f"窗口{current_time_str}执行取消操作")
            nonlocal input_value
            input_value = None  # 设置为None，之后当做删除标签处理
            close_window()
            self.log(f"窗口{current_time_str}执行取消操作完成")

        def on_enter(event):
            on_confirm()  # 按下 Enter 键时，相当于点击确认

        def on_esc(event):
            on_cancel()  # 按下 Esc 键时，相当于点击取消

        # 检查输入，自动保存，超时关闭
        def auto_check_input():
            """
            每5秒自动保存1次输入
            总共等待60秒后，若输入为空则自动关闭，否则继续等待60秒
            """
            nonlocal input_value
            nonlocal total_wait
            nonlocal auto_save_interval
            wait_interval = 60000  # 等待间隔，首次等待后，若有输入，进入二次等待，之后直接默认确认
            # 计时
            total_wait += auto_save_interval
            # 自动保存
            input_value = entry.get()  # 若窗口提前关闭，此处的input_value仍能得到返回
            # 超时检查
            if total_wait < wait_interval:
                root.after(auto_save_interval, auto_check_input)  # 继续等待
                self.log(f"窗口{current_time_str}等待1阶段，等待{total_wait//1000}秒，当前输入'{input_value}'")
            elif total_wait < wait_interval * 2:
                if input_value:  # 检查是否有输入
                    root.after(auto_save_interval, auto_check_input)
                    self.log(f"窗口{current_time_str}等待2阶段，等待{total_wait // 1000}秒，当前输入'{input_value}'")
                else:
                    self.log(f"窗口{current_time_str}等待2阶段，输入为空，执行确认操作")
                    on_confirm()  # 没有输入直接confirm（此时返回空string）
            else:
                self.log(f"窗口{current_time_str}等待3阶段，当前输入'{input_value}'，执行确认操作")
                on_confirm()

        self.log(f"窗口{current_time_str}：创建主窗口")
        # 创建主窗口
        root = tk.Tk()
        self.log(f"窗口{current_time_str}：窗口id{id(root)}")
        root.title("输入标签")  # 翻译点
        # root_width = 310
        root_width = 290
        root_height = 150
        center_window(width=root_width, height=root_height)

        self.log(f"窗口{current_time_str}：创建主窗口")
        # 提示
        # label_font = font.Font(size=12)
        '''
        原因不明，但是只要用了多线程，font.Font就非常容易引发错误
        有可能是 RuntimeError: main thread is not in main loop，也可能是隔空引起 mainloop 阻塞
        所以不用了，丑了点就丑了点吧
        '''
        # 创建文字
        # label = tk.Label(root, text=f"标签时间点：{current_time_str}", font=label_font)  # 可用 fg="blue" 指定颜色
        # label = tk.Label(root, text=f"标签时间点：{current_time_str}", font=self.label_font)  # 临时
        label = tk.Label(root, text=f"标签时间点：{current_time_str}")  # 临时  # 翻译点
        # label.pack(pady=(20, 0))
        label.pack(pady=(10, 0))

        self.log(f"窗口{current_time_str}：创建输入框")
        # 输入框
        # entry_font = font.Font(size=15)
        # entry_width = 25  # width 和 height 以字符数量为单位，下同
        entry_width = 30  # temp
        # 创建输入框
        # entry = tk.Entry(root, width=entry_width, font=entry_font)
        # entry = tk.Entry(root, width=entry_width, font=self.entry_font)
        entry = tk.Entry(root, width=entry_width)  # 临时
        entry.pack(pady=(5, 0))  # 上/下侧间距，padx类似（左/右），如果只有1个int则代表上下间距均用这个

        self.log(f"窗口{current_time_str}：创建按钮")
        # 按钮大小
        # button_font = font.Font(size=12)
        button_width = 13
        button_height = 2
        # button_side_x = 28
        button_side_x = 28
        # 创建确认按钮
        # confirm_button = tk.Button(root, text="确认", command=on_confirm, width=button_width, height=button_height, font=button_font)
        # confirm_button = tk.Button(root, text="确认", command=on_confirm, width=button_width, height=button_height, font=self.label_font)  # 临时复用
        confirm_button = tk.Button(root, text="确认", command=on_confirm, width=button_width, height=button_height)  # 临时  # 翻译点
        confirm_button.pack(side=tk.LEFT, padx=(button_side_x, 0))
        # 创建取消按钮
        # cancel_button = tk.Button(root, text="取消", command=on_cancel, width=button_width, height=button_height, font=button_font)
        # cancel_button = tk.Button(root, text="取消", command=on_cancel, width=button_width, height=button_height, font=self.label_font)  # 临时复用
        cancel_button = tk.Button(root, text="取消", command=on_cancel, width=button_width, height=button_height)  # 临时  # 翻译点
        cancel_button.pack(side=tk.RIGHT, padx=(0, button_side_x))
        # 绑定按键事件
        root.bind("<Return>", on_enter)  # 按下 Enter 键时调用 on_enter 函数
        root.bind("<Escape>", on_esc)  # 按下 Esc 键时调用 on_esc 函数

        self.log(f"窗口{current_time_str}：绑定关闭事件")
        # 绑定窗口关闭事件
        root.protocol("WM_DELETE_WINDOW", on_close)

        self.log(f"窗口{current_time_str}：设置焦点")
        # 设置输入框为焦点
        entry.focus_set()  # 弹出窗口后，输入框立即获得焦点

        self.log(f"窗口{current_time_str}：设置自动保存关闭定时器")
        # 设置自动关闭窗口的定时器
        total_wait = 0  # 等待总时长
        auto_save_interval = 5000  # 自动保存间隔
        root.after(auto_save_interval, auto_check_input)  # 此处单位是ms，5秒后执行auto_check_input

        # 初始化变量
        input_value = ""  # 默认打了标签就有内容，只是为空string，只有cancel才视为None，进而删除标签

        # 计入正在打开的窗口
        with self.window_lock:
            self.windows_n_close_events[root] = close_event
        self.log(f"窗口{current_time_str}：计入dict完成")

        # 关闭相关
        is_closed = False  # 窗口是否已经关闭，用于传递信号
        # 启动子线程，用于监控外部的关闭信号
        close_event_flag = 0
        check_thread = threading.Thread(target=auto_check_close)
        if close_event:
            close_event_flag = 1  # 用flag做标记，避免close_event发生变化
        if close_event_flag == 1:
            check_thread.start()
            self.log(f"窗口{current_time_str}：启动关闭信号监控线程")

        # 启动主循环
        root.mainloop()  # 窗口被destroy则可以继续向下执行
        self.log(f"窗口{current_time_str}：主循环结束")

        # 等待监控子线程完成
        if close_event_flag == 1:
            check_thread.join()
            self.log(f"窗口{current_time_str}：监控线程结束")

        # 返回输入内容
        self.log(f"窗口{current_time_str}返回：{input_value}")
        return input_value

    # 主处理函数（快捷键回调）
    def on_hotkey_pressed(self, pressed):
        if not pressed:
            return

        # 获取当前视频时间
        current_time_ms = self.get_current_video_time_ms()

        # 若录制，才执行
        if current_time_ms is not None:
            self.log(f"检测到快捷键按下，当前时间点: {self.format_time_ms(current_time_ms)}")

            if self.is_simp:
                # 静默模式标签为从1开始的数字
                idx = len(self.labels) + 1  # 从1开始
                self.labels.append((current_time_ms, f'{idx}'))
            else:
                # 通过多线程弹出输入对话框并写入标签
                def dialog_thread(current_time_ms, close_event):
                    current_time_str = self.format_time_ms(current_time_ms)
                    text = self.input_label_dialog(current_time_str, close_event)
                    if text is not None:
                        text = text if text else "空标签"
                        with self.thread_lock:
                            self.labels.append((current_time_ms, text))
                            self.log(f"添加新标签: {text} @ {current_time_str}")
                            self.write_files(mode="a")  # 立即写入文件
                            self.log(f"追加写入完成")

                close_event = threading.Event()
                thread = threading.Thread(target=dialog_thread, args=(current_time_ms, close_event))  # 使用子线程执行窗口弹出
                self.threads.append(thread)
                self.log(f"即将启动子线程弹窗{self.format_time_ms(current_time_ms)}")
                self.log(f"close_event id {id(close_event)}")
                thread.start()

        # 异常log
        else:
            self.log(f"检测到快捷键按下，但当前不处于录像状态")

    # 录制状态改变回调
    def on_recording_state_changed(self, event):
        """
        假如一段代码在执行过程中，触发了下一个事件，是否还会执行下一段代码？可以用sleep做测试
        """
        if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:
            # 记录录制开始时间
            self.rec_start_time = obs.os_gettime_ns()  # nanosecond 精度的时间
            self.base_filename = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            self.log("录制开始，重置计时器")
            self.log(f"当前系统时间点：{self.format_time_ns(self.rec_start_time)}")
            self.log(f"当前视频时间点：{self.format_time_ms(self.real_duration_ms(self.rec_start_time))}")
            self.log(f"基础文件名：{self.base_filename}")
            self.txt_path = self.get_unique_filename(".txt")
            self.pbf_path = self.get_unique_filename(".pbf")
        elif event == obs.OBS_FRONTEND_EVENT_RECORDING_PAUSED:
            self.last_pause_time = obs.os_gettime_ns()
            self.log(f"录制暂停，开始记录暂停时间")
            self.log(f"当前系统时间点：{self.format_time_ns(self.last_pause_time)}")
            self.log(f"当前视频时间点：{self.format_time_ms(self.real_duration_ms(self.last_pause_time))}")
        elif event == obs.OBS_FRONTEND_EVENT_RECORDING_UNPAUSED:
            if self.last_pause_time:
                unpaused_time = obs.os_gettime_ns()
                pause_duration = (unpaused_time - self.last_pause_time)
                self.paused_duration += pause_duration
                self.log(f"录制恢复，停止记录暂停时间，累计暂停时长: {self.format_time_ns(self.paused_duration)}")
                self.log(f"当前系统时间点：{self.format_time_ns(unpaused_time)}")
                self.log(f"当前视频时间点：{self.format_time_ms(self.real_duration_ms(unpaused_time))}")
                self.last_pause_time = None
                self.log(f"清除暂停起始时间")
        elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
            if not self.is_simp:
                # 杀掉所有未关闭的窗口（根据前文，会返回自动保存的input）
                if len(self.windows_n_close_events) != 0:
                    wd_n_c_ev = self.windows_n_close_events.copy()  # copy是浅拷贝，不过对象应该是不会变的
                    # 此处不做window_lock，以防调用内容又触发window_lock死锁，为防止该过程中dict发生变化，于是做了copy
                    for window in wd_n_c_ev:
                        self.log(f"发现窗口未关闭，传递关闭信号")
                        try:
                            wd_n_c_ev[window].set()  # 若窗口还在，尝试设定关闭信号
                        except Exception as e:
                            self.log(f"传递关闭信号出错: {str(e)}")
                        time.sleep(0.1)
                # 确认所有线程完成
                for thread in self.threads:
                    thread.join(timeout=0.3)  # timeout单位是s，留点时间完成剩余读写工作
            # 最后一次写入文件
            with self.thread_lock:  # 避免通过timeout结束时还有线程占用
                self.labels.sort(key=lambda label: label[0])  # 按照时间排序
                self.write_files(mode="w")  # 最终覆盖写入
            self.log("录制停止，写入最终文件")
            """
            上述代码有个隐患，已有多种措施尽可能减少异常，但若还是操作太快，不确定会发生什么
            """
            # 初始化
            self.record_attr_init()
            self.log("初始化参数完成")


# 全局实例
recorder = LabelRecorder()


# 辅助函数
def hotkey_register():
    """
    热键注册
    """
    recorder.hotkey_id = obs.obs_hotkey_register_frontend(
        "label_hotkey", "添加时间点标记",
        lambda pressed: recorder.on_hotkey_pressed(pressed))  # 不知为何不用 lambda 会有问题  # 翻译点
    recorder.log(f"注册热键")


def get_output_dir(settings):
    """
    获取输出目录
    把settings里的output_dir赋给recorder.output_dir
    """
    new_dir = obs.obs_data_get_string(settings, "output_dir")  # 从settings中获取输出目录
    if new_dir:
        recorder.output_dir = new_dir
    recorder.log(f"加载输出目录设置: {recorder.output_dir}")


def get_is_simp(settings):
    """
    获取静默模式设置
    """
    new_is_simp = obs.obs_data_get_bool(settings, "is_simp")  # 从settings中获取输出目录
    recorder.is_simp = new_is_simp
    recorder.log(f"加载静默模式设置: {recorder.is_simp}")


def get_hotkey(settings):
    """
    获取热键设置
    """
    hotkey_save_array = obs.obs_data_get_array(settings, "label_hotkey_settings")
    if hotkey_save_array:
        recorder.hotkey_array = hotkey_save_array  # 这个数组引用是要release的，不太懂赋给recorder属性后要怎么处理，所以不用这个函数了
    recorder.log(f"加载快捷键设置: {recorder.hotkey_array}")


# OBS脚本生命周期函数 -------------------------------------------------
def script_description():
    """
    脚本描述
    """
    return ("【录像时间点标记1.0】\n"
            "功能：录制视频时，通过快捷键记录时间点标签。\n"
            "使用说明：\n"
            "1. 快捷键在 文件-设置-快捷键 中设置；\n"
            "2. 建议 标签输出目录 与 录像输出目录 相同；\n"
            "3. 勾选 静默模式 将不弹出输入标签内容的窗口。\n"
            "作者：L.P."
            )  # 翻译点


def script_properties():
    """
    脚本设置界面
    """
    props = obs.obs_properties_create()
    # 输出目录设置
    obs.obs_properties_add_path(props, "output_dir", "标记输出文件夹",
                                obs.OBS_PATH_DIRECTORY, None, None)  # 翻译点
    # 静默模式设置
    obs.obs_properties_add_bool(props, "is_simp", "静默模式")  # 翻译点
    return props


def script_load(settings):
    """
    脚本加载时运行
    """
    """
    由于OBS似乎未提供脚本设置页面的快捷键，控件，快捷键的实现如下：
    首先，脚本加载时，注册设置菜单里的快捷键选项label_hotkey（获得其id），即添加录制标签（可能随脚本更新改名）（此时为空）
    其次，从脚本settings中获取label_hotkey_settings数据，并加载给设置
    最后，每次保存设置，都通过id获取最新的label_hotkey，并保存到label_hotkey_settings，以便下次加载
    
    注意，settings是属于本脚本的设置数据，不会随加载卸载而删除，想加什么都行，不需要显性展示
    properties里的设置和settings是对应的，比如output_dir是一样的
    但是frontend不一样，这里label_hotkey_settings和label_hotkey专门做了名字区分，就是避免该过程混淆
    
    另：我没找到处理热键数据的API，比如把string转换成热键，或者把热键转换成可读的形式
    故无法设置默认热键，只能靠用户手动设置，log也记录不了设置了什么
    热键配置应该是对某个array的引用（这和python的数据类型又有点不一样），但是array的元素又是什么类型，不知道，反正能用就行
    """
    # 注册快捷键
    hotkey_register()
    hotkey_save_array = obs.obs_data_get_array(settings, "label_hotkey_settings")
    obs.obs_hotkey_load(recorder.hotkey_id, hotkey_save_array)  # 将settings中的热键配置加载到设置中
    obs.obs_data_array_release(hotkey_save_array)  # 释放hotkey_save_array，不清楚不释放会怎样，这块垃圾内存不会自动清理吗
    recorder.log(f"加载快捷键设置: {hotkey_save_array}")
    # 获取输出目录
    get_output_dir(settings)
    # 获取静默设置
    get_is_simp(settings)
    # 注册前端事件回调
    obs.obs_frontend_add_event_callback(lambda event: recorder.on_recording_state_changed(event))
    # recorder.log(f"脚本目录: {obs.script_path()}")  # 文档里有script_path但实际使用报错没有，不用了
    recorder.log("脚本加载完成")


def script_save(settings):
    """
    设置保存时运行
    解释是Called when the script is being saved. This is not necessary for settings that are set by the user; instead this is used for any extra internal settings data that may be used in the script.
    不懂什么叫the script is being saved，不过设置菜单应用时会call
    所以理论上来说这里只需存一下热键即可，不过保险起见把别的也存了
    """
    # 从hotkey_id保存快捷键到settings
    hotkey_save_array = obs.obs_hotkey_save(recorder.hotkey_id)
    obs.obs_data_set_array(settings, "label_hotkey_settings", hotkey_save_array)  # 保存热键配置到设置中
    obs.obs_data_array_release(hotkey_save_array)
    recorder.log(f"保存热键：{hotkey_save_array}")
    # 从recorder.output_dir保存输出目录到settings
    obs.obs_data_set_string(settings, "output_dir", recorder.output_dir)
    recorder.log(f"保存目录：{recorder.output_dir}")
    recorder.log("脚本保存完成")
    # 从recorder.is_simp保存输出目录到settings
    obs.obs_data_set_bool(settings, "is_simp", recorder.is_simp)
    recorder.log(f"保存静默设置：{recorder.is_simp}")
    recorder.log("脚本保存完成")


def script_update(settings):
    """
    脚本更新时运行
    解释是Called when the script’s settings (if any) have been changed by the user.
    save是其他改动会call，update是脚本设置改动会call，我猜
    因为recorder内的hotkey目前弃用，所以只更新一下output_dir和is_simp
    """
    # 从settings更新输出目录到recorder.output_dir，维持同步
    get_output_dir(settings)
    recorder.log(f"更新目录：{recorder.output_dir}")
    # 从settings更新输出目录到recorder.is_simp，维持同步
    get_is_simp(settings)
    recorder.log(f"更新静默设置：{recorder.is_simp}")
    recorder.log("脚本更新完成")


def script_unload():
    """
    脚本卸载时运行
    """
    recorder.log("脚本卸载")


# 主入口
if __name__ == "__main__":
    pass
