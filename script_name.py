import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PyPDF2 import PdfMerger, PdfReader
from datetime import datetime

headers = {"User-Agent": "Mozilla/5.0"}

# 👉 获取今天日期
today = datetime.now()
year = today.strftime("%Y")
month = today.strftime("%m")
day = today.strftime("%d")

# 👉 生成URL
base_url = f"http://paper.people.com.cn/rmrb/pc/layout/{year}{month}/{day}/node_01.html"
remark = f"人民日报 {year}年{month}月{day}日"

# 👉 保存目录改为 papers，并确保文件夹存在
download_dir = "papers"
os.makedirs(download_dir, exist_ok=True)  # 这行确保文件夹被创建

try:
    res = requests.get(base_url, headers=headers, timeout=10)
    if res.status_code != 200:
        print(f"页面加载失败，状态码: {res.status_code}")
        exit()
    print(f"请求成功：{base_url}")
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")
except Exception as e:
    print(f"请求失败：{base_url}，错误：{e}")
    exit()

output_pdf = os.path.join(download_dir, f"{remark}.pdf")
print(f"\n准备合并输出文件：{output_pdf}")

base_path = base_url.rsplit('/', 1)[0] + "/"

swiper = soup.find("div", class_="swiper-container")
if not swiper:
    print(f"未找到版面容器，可能当天报纸未发布")
    exit()

pages = []
for a_tag in swiper.find_all("a", id="pageLink"):
    href = a_tag.get("href")
    title = a_tag.get_text(strip=True)
    if href and title:
        full_url = urljoin(base_path, href)
        pages.append((full_url, title))

if not pages:
    print("未找到版面链接")
    exit()

merger = PdfMerger()
page_start = 0
downloaded_pdfs = []  # 存储已下载的分页文件路径

for page_url, bookmark_title in pages:
    print(f"处理：{bookmark_title}")
    try:
        page_res = requests.get(page_url, headers=headers, timeout=10)
        page_res.encoding = "utf-8"
        page_soup = BeautifulSoup(page_res.text, "html.parser")

        pdf_tag = page_soup.find("p", class_="right btn")
        if pdf_tag and pdf_tag.a:
            pdf_url = urljoin(page_url, pdf_tag.a["href"])
            pdf_name = os.path.basename(pdf_url)
            pdf_path = os.path.join(download_dir, pdf_name)

            if not os.path.exists(pdf_path):
                print("Downloading:", pdf_url)
                with open(pdf_path, "wb") as f:
                    f.write(requests.get(pdf_url).content)
            else:
                print("已存在:", pdf_name)

            merger.append(pdf_path)
            merger.add_outline_item(bookmark_title, page_start)

            reader = PdfReader(pdf_path)
            page_start += len(reader.pages)

            # 保存已下载的PDF路径
            downloaded_pdfs.append(pdf_path)
        else:
            print("未找到PDF链接")
    except Exception as e:
        print(f"处理失败：{page_url}，错误：{e}")

try:
    merger.write(output_pdf)
    merger.close()
    print("✅ 合并完成：", output_pdf)

    # 删除原始分页文件
    for pdf_file in downloaded_pdfs:
        try:
            os.remove(pdf_file)
            print(f"删除文件：{pdf_file}")
        except Exception as e:
            print(f"删除文件失败：{pdf_file}，错误：{e}")

except Exception as e:
    print("❌ 保存失败：", e)
