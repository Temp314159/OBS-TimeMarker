# -*- coding:utf-8 -*-
# based on python 3.9
# 2024/04/13 11:01
# by L.P.

"""
将特定格式的txt转为pbf文件，单独使用，兼容了方便自己用的一些格式，之后整合进主脚本
"""

import sys
import os
import glob
import re
import time


def time_to_milliseconds(time_str):
    """ hh:mm:ss 或 hh:mm:ss.sss 转毫秒 """
    parts = time_str.split(':')
    if '.' in parts[-1]:
        seconds, milliseconds = map(int, parts[-1].split('.'))
    else:
        seconds = int(parts[-1])
        milliseconds = 0
    minutes = int(parts[1])
    hours = int(parts[0])
    total_milliseconds = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
    return total_milliseconds


def parse_txt_file(txt_path):
    """ 解析 TXT ， return 一个 time label : description 的字典 """
    time_label_dct = {}
    description_title = ""
    with open(txt_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        for line in lines:
            line = line.strip()
            # 匹配格式3
            if re.match(r'^\[.*\]$', line) or re.match(r'^【.*】$', line):
                description_title = line
                continue
            # 匹配格式1/2
            # (?:)为非捕获组，所有()不论嵌套关系最终都会捕获为group（按前括号出现顺序）
            match = re.match(r'^(?:(\d+)\s+)?(\d{1,2}:\d{2}:\d{2}(?:\.\d{3})?)(?:\-(\d{1,2}:\d{2}:\d{2}(?:\.\d{3})?))?\s+(.+)$', line)
            if match:
                index, time_stamp, time_stamp2, description = match.groups()
                milliseconds = time_to_milliseconds(time_stamp)
                time_label_dct[milliseconds] = f"{description_title}{description}"
    return time_label_dct


def write_pbf_file(pbf_path, time_label_dct):
    """ 写入 PBF """
    with open(pbf_path, 'w', encoding='utf-8') as file:
        file.write('[Bookmark]\n0=')
        for idx, (time_stamp, description) in enumerate(sorted(time_label_dct.items())):
            file.write(f'{time_stamp}*{description}*\n{idx+1}=')


def get_txt_path(txt_path='TimeStamps.txt'):
    if txt_path is None:
        txt_path = 'TimeStamps.txt'
    # 检查 txt_path 是否存在，否，找当前目录下第一个 txt
    if not os.path.exists(txt_path):
        txt_files = glob.glob('*.txt')
        if txt_files:
            txt_path = txt_files[0]
        else:
            raise FileNotFoundError("No .txt files found in the current directory.")
    return txt_path


def get_pbf_path(txt_path='TimeStamps.txt'):
    # 提取 txt_path 的上层路径 txt_dir 和文件名 txt_file_name
    txt_dir, txt_file_name = os.path.split(txt_path)

    # 用正则表达式匹配 txt_path
    match = re.match(r'^(.+?)\s*TimeStamps.txt', txt_file_name)
    if match:
        pbf_name = match.group(1)
    else:
        pbf_name = 'TimeStamps'

    # 将 pbf_path 设置为 txt_dir 文件夹下的 pbf_name.pbf
    return os.path.join(txt_dir, f'{pbf_name}.pbf')


def main(txt_path='TimeStamps.txt', pbf_path='TimeStamps.pbf'):
    time_label_dct = parse_txt_file(txt_path)
    write_pbf_file(pbf_path, time_label_dct)
    print(f"Successfully processed {txt_path} and created {pbf_path}")


if __name__ == '__main__':
    try:
        # 获取参数
        txt_path = sys.argv[1] if len(sys.argv) > 1 else None
        txt_path = get_txt_path(txt_path)
        pbf_path = sys.argv[2] if len(sys.argv) > 2 else get_pbf_path(txt_path)
        main(txt_path, pbf_path)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Sleeping for 30 seconds...")
        time.sleep(30)




