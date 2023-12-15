# -*- coding: utf-8 -*-
import os
import re
import time
import urllib.parse

import requests
import scrapy
from scrapy.selector import Selector
from zhconv import zhconv


class Yijing64(scrapy.Spider):
    name = "golla_tw"
    start_urls = [f"https://www.golla.tw/sm/64gua/{42256 - i}.html" for i in range(64)]

    custom_settings = {
        "WORK_DIR": os.path.join(os.path.dirname(os.path.dirname(__file__)), "output/golla_tw")
    }

    def parse(self, response, **kwargs):
        current_url = response.url
        print(f"=> {current_url}")
        if current_url.endswith(".html"):
            self.parse_one(response)
            return

    def parse_one(self, response):
        work_dir = self.settings.get("WORK_DIR")
        response = Selector(response=response)
        main = response.css("#entrybody").get()

        # 转换为 Markdown 格式
        main = re.sub(r'<strong[^>]*>(.*?)</strong>', r' **\1** ', main)  # 将 <strong> 标签替换为 **
        main = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', main)  # 将 <p> 标签替换为 \n
        main = re.sub(r'<[^>]+>', '', main)  # 移除剩余的 HTML 标签
        main = re.sub(r'^\s+', '\n', main, flags=re.MULTILINE)  # 移除多余的空格

        match = re.search(r"周易第(\d+?)卦詳解((.|\n)+?)卦（(.+?)）\*\*", main)
        if match:
            number = match.group(1)
            if len(number) == 1:
                number = f"0{number}"
            filename = f"{number}.{match.group(4)}"
            # main = zhconv.convert(main, 'zh-cn')
            filename = zhconv.convert(filename, 'zh-cn')
            print(filename)

            dir_path = os.path.join(work_dir, filename)
            os.makedirs(dir_path, exist_ok=True)
            filepath = os.path.join(dir_path, "index.md")
            with open(filepath, "w") as f:
                f.write(main.strip())
        else:
            print("no match")
