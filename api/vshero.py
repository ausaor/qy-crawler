from orm.models import HeroInfo, HeroSkin

from fastapi import APIRouter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime


vshero_api = APIRouter()


@vshero_api.get("/crawler/heros")
async def crawler_heros():
    """
    爬取曙光英雄数据
    """
    # 设置 ChromeDriver 路径（需自行下载）
    driver_path = 'F:/software/chromedriver/chromedriver-win64/chromedriver.exe'  # 请替换为你的 chromedriver 实际路径
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service)

    url = "https://www.vshero.cn/#/data"

    try:
        driver.get(url)
        # 显式等待：等待特定英雄列表元素加载完成
        # 替换 'hero-list' 为实际页面中的目标元素ID或选择器
        wait = WebDriverWait(driver, 10)

        print(driver.title)  # 打印页面标题

        hero_list = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "hero-list")))  # 请替换为实际选择器
        hero_list_a = hero_list.find_elements(By.CLASS_NAME, "hero-item")

        print(f'英雄列表数量：{len(hero_list_a)}')

        # 用于统计插入和更新的记录数
        inserted_count = 0
        updated_count = 0

        for a_ele in hero_list_a:
            # 获取英雄名称
            hero_name = a_ele.find_element(By.CLASS_NAME, "name").text
            print(f'英雄名称：{hero_name}')

            # 获取英雄详情链接,从a标签中获取，例：https://www.vshero.cn/#/hero/1748
            hero_detail_url = a_ele.get_attribute("href")
            print(f'英雄详情链接：{hero_detail_url}')

            # 根据英雄详情链接提取英雄ID
            hero_id = hero_detail_url.split("/")[-1]

            # 获取英雄头像链接
            hero_avatar_src = a_ele.find_element(By.TAG_NAME, "img").get_attribute("src")
            print(f'英雄头像链接：{hero_avatar_src}')

            # 尝试查找数据库中是否已存在该英雄
            hero_obj = await HeroInfo.get_or_none(hero_name=hero_name, category="曙光英雄")

            # 获取当前时间
            current_time = datetime.now()

            if hero_obj is None:
                # 如果英雄不存在，则创建新记录
                await HeroInfo.create(
                    hero_id=hero_id,
                    hero_name=hero_name,
                    hero_detail_url=hero_detail_url,
                    hero_profile_url=hero_avatar_src,
                    category="曙光英雄",
                    create_time=current_time,
                    update_time=current_time
                )
                inserted_count += 1
                print(f'新增英雄：{hero_name}')
            else:
                # 如果英雄已存在，更新记录
                hero_obj.hero_detail_url = hero_detail_url
                hero_obj.hero_profile_url = hero_avatar_src
                hero_obj.update_time = current_time
                await hero_obj.save()
                updated_count += 1
                print(f'更新英雄：{hero_name}')

    finally:
        driver.quit()

    return {
        "message": "爬取完成",
        "inserted_count": inserted_count,
        "updated_count": updated_count
    }