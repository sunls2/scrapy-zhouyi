# -*- coding: utf-8 -*-
import os
import re
import time
import urllib.parse

import requests
import scrapy
from scrapy.selector import Selector


class Yijing64(scrapy.Spider):
    name = "yijing64"
    start_urls = [
        "https://www.zhouyi.cc/zhouyi/yijing64/"
        # "https://www.zhouyi.cc/zhouyi/yijing64/4103.html" # 第 1 卦
        # "https://www.zhouyi.cc/zhouyi/yijing64/4197.html" # 第 56 卦
    ]

    custom_settings = {
        "WORK_DIR": os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    }

    def parse(self, response, **kwargs):
        current_url = response.url
        print(f"=> {current_url}")
        if current_url.endswith(".html"):
            self.parse_one(response)
            return

        response = Selector(response=response)
        # 提取所有的地址
        hrefs = response.xpath('//*[@id="main"]/div[4]/div/div[2]/div[4]/div/ul/li/a/@href').getall()
        for href in hrefs:
            if href:
                yield scrapy.Request(url=urllib.parse.urljoin(current_url, href), callback=self.parse)

    def parse_one(self, response):
        work_dir = self.settings.get("WORK_DIR")
        response = Selector(response=response)
        main = response.css("div.gua_wp")
        file = None

        # 本卦，互卦，错卦，综卦
        table = main.css("table.guatab").get()
        table = re.sub(r'<table\s+[^>]*>', '<table>', table)
        table = re.sub(r'(?m)^\t', '', table)
        table = self.convert_table_link(table)
        table = table.replace("</a>本卦</td>", "</a></td>")  # 修复第一卦中的错误

        for item in main.css("div.f14"):
            # 标题
            title = item.css("div.gua_toptt::text")
            if title:
                title = title.get()
                # 转换标题格式: 56.旅卦.火山旅.离上艮下
                mark = self.convert_title(title)
                work_dir = os.path.join(work_dir, mark)
                os.makedirs(work_dir, exist_ok=True)
                filepath = os.path.join(work_dir, f"{mark}.md")

                file = open(filepath, "w")
                file.write(f"# {title} \n\n")

                table = self.download_image(table, work_dir)
                file.write(table)
                continue

            # 段落标题
            pt = item.css("div.guatt::text")
            if pt:
                if file:
                    file.write(f"\n\n## {pt.get()}\n\n")
                continue

            # 正文内容
            content = item.css("div.gualist").get()
            if not content:
                continue

            # 提取图片
            content = self.download_image(content, work_dir)

            # 转换为 Markdown 格式
            content = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', content)  # 将 <strong> 标签替换为 **
            content = re.sub(r'<br\s*/?>', '\n', content)  # 将多个 <br> 标签替换为换行符
            content = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', r'![image](\1)', content)  # Markdown 图片链接
            content = re.sub(r'\s*\!\[image\](.*?)\)', r'\n![image]\1)\n', content)  # 移除 ![image] 前面的空格
            content = re.sub(r'<[^>]+>', '', content)  # 移除剩余的 HTML 标签
            content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)  # 将超过两个连续的空行替换为一个空行
            content = re.sub(r'\u00A0', ' ', content)  # 去除 [NBSP] 字符

            if file:
                file.write(content.strip())
        if file:
            file.close()

    @staticmethod
    # 下载标签中的图片到本地并替换路径
    def download_image(content, work_dir):
        for image_url in re.findall(r'<img[^>]*src="([^"]+)"[^>]*>', content):
            if image_url.startswith("file://"):
                continue
            filename = image_url.split("/")[-1]  # 提取图片文件名
            local_path = os.path.join(work_dir, filename)
            if not os.path.exists(local_path):
                response = requests.get(image_url)
                if response.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(response.content)
                        time.sleep(1)  # 延迟1s
            content = content.replace(image_url, f"./{filename}")
        return content

    @staticmethod
    def convert_title(title) -> str:
        pattern = r"周易第(\d+)卦_([^_]+)\(([^)]+)\)_([^_]+)"
        match = re.match(pattern, title)
        if match:
            return f"{match.group(1)}.{match.group(3)}"
        return title

    @staticmethod
    def convert_table_link(table):
        def replace_match(m):
            mark = f"{m.group(1)}.{m.group(3)}"
            return f'<a href="../{mark}/{mark}.md" style="text-decoration: none;">{m.group(0)}</a>'

        pattern = r'第(\d+)卦：(.+?)\((.+?)\)'
        table = re.sub(pattern, replace_match, table)
        return table
