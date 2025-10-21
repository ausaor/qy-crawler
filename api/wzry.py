from fastapi import APIRouter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

from orm.models import HeroInfo
wzry_api = APIRouter()

@wzry_api.get("/crawler/heros")
async def crawler_heros():
    """
    爬取王者荣耀英雄列表
    """
    # 设置 ChromeDriver 路径（需自行下载）
    driver_path = 'F:/software/chromedriver/chromedriver-win64/chromedriver.exe'  # 请替换为你的 chromedriver 实际路径
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service)

    url = "https://pvp.qq.com/web201605/herolist.shtml"

    try:
        driver.get(url)
        # 显式等待：等待特定英雄列表元素加载完成
        # 替换 'hero-list' 为实际页面中的目标元素ID或选择器
        wait = WebDriverWait(driver, 10)

        print(driver.title)  # 打印页面标题

        hero_list = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "herolist")))  # 请替换为实际选择器
        hero_list_li = hero_list.find_elements(By.TAG_NAME, "li")

        print(f'英雄列表数量：{len(hero_list_li)}')
        
        # 用于统计插入和更新的记录数
        inserted_count = 0
        updated_count = 0
        
        for li in hero_list_li:
            # 获取英雄名称
            hero_name = li.find_element(By.TAG_NAME, "a").text
            print(f'英雄名称：{hero_name}')

            # 获取英雄详情链接,从a标签中获取
            hero_detail_url = li.find_element(By.TAG_NAME, "a").get_attribute("href")
            print(f'英雄详情链接：{hero_detail_url}')

            # 获取英雄头像链接
            hero_avatar_src = li.find_element(By.TAG_NAME, "img").get_attribute("src")
            print(f'英雄头像链接：{hero_avatar_src}')
            
            # 尝试查找数据库中是否已存在该英雄
            hero_obj = await HeroInfo.get_or_none(hero_name=hero_name, category="王者荣耀")
            
            # 获取当前时间
            current_time = datetime.now()
            
            if hero_obj is None:
                # 如果英雄不存在，则创建新记录
                await HeroInfo.create(
                    hero_name=hero_name,
                    hero_detail_url=hero_detail_url,
                    hero_profile_url=hero_avatar_src,
                    category="王者荣耀",
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