from fastapi import APIRouter
import httpx
from orm.models import HeroInfo
from tortoise.exceptions import IntegrityError
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

lol_api = APIRouter()


@lol_api.get("/crawler/heros")
async def crawler_heros():
    # 获取数据链接https://game.gtimg.cn/images/lol/act/img/js/heroList/hero_list.js?ts=2935627
    url = "https://game.gtimg.cn/images/lol/act/img/js/heroList/hero_list.js?ts=2935627"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        hero_list = data["hero"]

        # 批量保存到数据库
        heroes_to_create = []
        for hero in hero_list:
            hero_name = hero["title"]
            hero_id = hero["heroId"]
            hero_alias_name = hero["name"]
            
            hero_info = HeroInfo(
                hero_name=hero_name,
                hero_id=hero_id,
                hero_alias_name=hero_alias_name,
                category="LOL",  # 设置类别为LOL
                is_crawl=False,  # 默认未爬取其他信息
                create_time=datetime.now(),
                update_time=datetime.now()
            )
            heroes_to_create.append(hero_info)
            
        # 批量创建或更新英雄信息
        try:
            # 使用bulk_create创建所有英雄，如果有重复则忽略
            await HeroInfo.bulk_create(heroes_to_create, ignore_conflicts=True)
            print(f"英雄[全部] 已保存到数据库")
        except IntegrityError as e:
            print(f"保存英雄时出错: {e}")

        return data["hero"]


@lol_api.get("/crawler/heroAvatar")
async def crawler_hero_avatar():
    """
    爬取LOL英雄头像和详情链接
    """
    # 设置 ChromeDriver 路径（需自行下载）
    driver_path = 'F:/software/chromedriver/chromedriver-win64/chromedriver.exe'  # 请替换为你的 chromedriver 实际路径
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service)

    url = "https://101.qq.com/#/hero-rank-5v5?tier=200&queue=420"
    try:
        driver.get(url)
        # 显式等待：等待特定英雄列表元素加载完成
        # 替换 'hero-list' 为实际页面中的目标元素ID或选择器
        wait = WebDriverWait(driver, 10)

        print(driver.title)  # 打印页面标题

        hero_list = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table-body")))  # 请替换为实际选择器
        hero_list_items = hero_list.find_elements(By.CLASS_NAME, "body-item")

        print(f'英雄列表数量：{len(hero_list_items)}')

        # 用于统计插入和更新的记录数
        inserted_count = 0
        updated_count = 0
        for hero_item in hero_list_items:
            hero_ele = hero_item.find_element(By.CLASS_NAME, "hero")
            # 获取a标签
            a_ele = hero_ele.find_element(By.TAG_NAME, "a")

            # 获取a标签的链接，例：https://101.qq.com/#/hero-detail?heroid=245&tab=overview&lane=all&datatype=5v5
            hero_detail_url = a_ele.get_attribute("href")
            # 提取heroId
            # 1. 解析URL，获取锚点（#后面的部分）
            parsed_url = urlparse(hero_detail_url)
            fragment = parsed_url.fragment  # 结果：'/hero-detail?heroid=245&tab=overview&lane=all&datatype=5v5'

            # 2. 从锚点中提取?后面的查询参数部分
            if "?" in fragment:
                query_str = fragment.split("?", 1)[1]  # 结果：'heroid=245&tab=overview&lane=all&datatype=5v5'
            else:
                query_str = ""

            # 3. 解析查询参数为字典（值为列表，支持多值参数）
            params = parse_qs(query_str)

            # 4. 提取heroid的值（取第一个匹配结果）
            hero_id = params.get("heroid", [None])[0]

            # 获取img标签
            img_ele = hero_ele.find_element(By.TAG_NAME, "img")
            hero_profile_url = img_ele.get_attribute("src")
            hero_alias_name = img_ele.get_attribute("alt")
            print(f'英雄[{hero_alias_name}]-{hero_id}头像链接：{hero_profile_url}')
            
            # 根据英雄ID查找数据库中的记录
            if hero_id:
                hero_info = await HeroInfo.filter(hero_id=hero_id, category="LOL").first()
                if hero_info:
                    # 更新记录
                    hero_info.hero_detail_url = hero_detail_url
                    hero_info.hero_profile_url = hero_profile_url
                    hero_info.update_time = datetime.now()
                    await hero_info.save()
                    updated_count += 1
                    print(f'英雄[{hero_alias_name}] 数据已更新')
                else:
                    # 如果通过hero_id找不到，则尝试通过英雄别名查找
                    hero_info = await HeroInfo.filter(hero_alias_name=hero_alias_name, category="LOL").first()
                    if hero_info:
                        # 更新记录
                        hero_info.hero_id = hero_id
                        hero_info.hero_detail_url = hero_detail_url
                        hero_info.hero_profile_url = hero_profile_url
                        hero_info.update_time = datetime.now()
                        await hero_info.save()
                        updated_count += 1
                        print(f'英雄[{hero_alias_name}] 数据已更新')
                    else:
                        # 创建新记录
                        hero_info = HeroInfo(
                            hero_id=hero_id,
                            hero_alias_name=hero_alias_name,
                            hero_detail_url=hero_detail_url,
                            hero_profile_url=hero_profile_url,
                            category="LOL",
                            is_crawl=False,
                            create_time=datetime.now(),
                            update_time=datetime.now()
                        )
                        await hero_info.save()
                        inserted_count += 1
                        print(f'英雄[{hero_alias_name}] 数据已插入')

    finally:
        driver.quit()
    return {
        "inserted_count": inserted_count,
        "updated_count": updated_count
    }