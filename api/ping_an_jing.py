from datetime import datetime

from fastapi import APIRouter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from orm.models import HeroInfo

paj_api = APIRouter()


@paj_api.get("/crawler/heros")
async def crawler_heros():
    """
    爬取决战平安京英雄数据
    """
    # 设置 ChromeDriver 路径
    driver_path = 'F:/software/chromedriver/chromedriver-win64/chromedriver.exe'
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service)

    url = "https://moba.163.com/?from=nietop"

    try:
        driver.get(url)
        # 显式等待：等待特定英雄列表元素加载完成
        wait = WebDriverWait(driver, 10)

        print(driver.title)  # 打印页面标题

        heros_box = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "shishen-slide_box")))
        # 查找获取ul标签下的所有li标签
        li_list = heros_box.find_elements(By.TAG_NAME, "li")

        # 用于统计插入和更新的记录数
        inserted_count = 0
        updated_count = 0
        for li in li_list:
            # 获取li标签下的a标签
            a_es = li.find_elements(By.TAG_NAME, "a")
            for a in a_es:
                hero_detail_url = a.get_attribute("href")
                print(f"英雄详情页链接：{hero_detail_url}")  # 例：https://moba.163.com/ssl/page.html?id=1059

                # 根据英雄详情链接，获取英雄id
                hero_id = hero_detail_url.split("=")[1]

                # 查找a标签下的img标签
                img = a.find_element(By.TAG_NAME, "img")
                hero_img_url = img.get_attribute("src")

                # 如果img的src属性值为空，则使用data-src属性值
                if not hero_img_url:
                    hero_img_url = img.get_attribute("data-src")
                print(f"英雄图片链接：{hero_img_url}")

                # 查找a标签下的class=shishen-desc的p标签
                p = a.find_element(By.TAG_NAME, "p")
                if p.is_displayed():
                    hero_name = p.text
                else:
                    # 尝试使用其他方式获取文本
                    hero_name = p.get_attribute("textContent") or p.get_attribute("innerText")

                print(f"英雄名称：{hero_name}，hero_id：{hero_id}")

                # 尝试查找数据库中是否已存在该英雄
                hero_obj = await HeroInfo.get_or_none(hero_name=hero_name, category="决战平安京")

                if hero_obj is None:
                    await HeroInfo.create(
                        hero_id=hero_id,
                        hero_name=hero_name,
                        hero_detail_url=hero_detail_url,
                        hero_profile_url=hero_img_url,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        category="决战平安京"
                    )
                    print(f"已添加英雄：{hero_name}")
                    inserted_count += 1
                else:
                    hero_obj.hero_detail_url = hero_detail_url
                    hero_obj.hero_profile_url = hero_img_url
                    await hero_obj.save()
                    print(f"已更新英雄：{hero_name}")
                    updated_count += 1
    finally:
        driver.quit()

    return {
        "message": "爬取完毕",
        "inserted_count": inserted_count,
        "updated_count": updated_count
    }