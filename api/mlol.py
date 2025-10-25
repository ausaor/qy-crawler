from fastapi import APIRouter
import httpx
import time
import threading
import queue
from datetime import datetime
from tortoise.exceptions import IntegrityError
from orm.models import HeroInfo, HeroSkin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import logging

# 配置日志，方便查看后台爬虫运行状态
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

mlol_api = APIRouter()


@mlol_api.get("/crawler/heros")
async def crawler_heros():
    """
    爬取英雄联盟手游英雄数据
    """
    # 获取数据链接https://game.gtimg.cn/images/lgamem/act/lrlib/js/heroList/hero_list.js
    url = "https://game.gtimg.cn/images/lgamem/act/lrlib/js/heroList/hero_list.js"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        hero_list_dict = data["heroList"] # 英雄列表, 字典

        # 将字典转为列表
        hero_list = list(hero_list_dict.values())
        # 批量保存到数据库
        heroes_to_create = []
        for hero in hero_list:
            hero_name = hero["name"]
            hero_alias_name = hero["title"]
            hero_id = hero["heroId"]
            hero_profile_url = hero["avatar"]
            hero_detail_url = f"https://lolm.qq.com/v2/detail.html?heroid={hero_id}"

            hero_info = HeroInfo(
                hero_name=hero_name,
                hero_id=hero_id,
                hero_alias_name=hero_alias_name,
                hero_profile_url=hero_profile_url,
                hero_detail_url=hero_detail_url,
                category="mlol",  # 设置类别为mlol
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
        finally:
            return hero_list


def crawler_worker(queue, thread_id, result_queue):
    """爬虫工作线程：从队列获取URL并爬取内容"""
    driver = None
    # 设置 ChromeDriver 路径（需自行下载）
    driver_path = 'F:/software/chromedriver/chromedriver-win64/chromedriver.exe'  # 请替换为你的 chromedriver 实际路径

    try:
        """处理单个英雄的函数，在线程中执行"""
        # 每个线程需要自己的webdriver实例
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service)
        logger.info(f"爬虫线程 {thread_id} 初始化完成")

        while True:
            hero = queue.get(timeout=5)
            if hero is None:  # 结束信号
                break

            logger.info(f"爬虫线程 {thread_id} 开始爬取: {hero.hero_name}")

            driver.get(hero.hero_detail_url)

            # 显式等待：等待英雄详情页面加载完成
            wait = WebDriverWait(driver, 10)
            hero_skins = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "skins-thumbnail-swiper")))

            # 获取英雄皮肤头像列表
            skin_avatars = hero_skins.find_elements(By.CLASS_NAME, "swiper-slide")
            skin_data_list = []

            for avatar in skin_avatars:
                # 获取英雄皮肤头像链接 例：https://game.gtimg.cn/images/lgamem/act/lrlib/img/HeadIcon/H_S_10001.png
                img = avatar.find_element(By.TAG_NAME, "img")
                avatar_img = img.get_attribute("src")
                print(f'英雄[{hero.hero_name}]皮肤头像链接：{avatar_img}')

                # 获取皮肤名称 例：德玛西亚之力 盖伦，皮肤名称是：德玛西亚之力
                alt = img.get_attribute("alt")
                # alt根据空格拆分获取皮肤名称
                skin_name = alt.split()[0]
                print(f'英雄[{hero.hero_name}]皮肤名称：{skin_name}')

                skin_data_list.append({
                    'hero_id': hero.hero_id,
                    'hero_name': hero.hero_name,
                    'avatar_img': avatar_img,
                    'skin_name': skin_name,
                    'category': "mlol"
                })

            # 将结果放入结果队列
            result_queue.put({
                'hero': hero,
                'skin_data_list': skin_data_list
            })

            logger.info(f"爬虫线程 {thread_id} 爬取结果: {hero.hero_name}")

            queue.task_done()
            time.sleep(1)  # 控制爬取速度

    except Exception as e:
        logger.error(f"爬虫线程 {thread_id} 出错: {str(e)}", exc_info=True)
    finally:
        if driver:
            driver.quit()
        logger.info(f"爬虫线程 {thread_id} 已关闭")


def background_crawl_task(hero_list, thread_count):
    """后台总控任务：创建队列和爬虫线程，分配任务"""
    logger.info(f"开始后台爬虫任务，共 {len(hero_list)} 个英雄，使用 {thread_count} 个线程")

    # 创建任务队列
    task_queue = queue.Queue()
    result_queue = queue.Queue()

    for hero in hero_list:
        task_queue.put(hero)

    # 启动爬虫线程
    threads = []
    for i in range(thread_count):
        t = threading.Thread(
            target=crawler_worker,
            args=(task_queue, i, result_queue),
            name=f"Crawler-{i}"
        )
        t.start()
        threads.append(t)

    # 等待所有URL处理完成
    task_queue.join()
    logger.info("所有URL爬取完成")

    # 发送结束信号给所有线程
    for _ in range(thread_count):
        task_queue.put(None)

    # 等待所有线程退出
    for t in threads:
        t.join()

    # 收集所有结果
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    logger.info("所有爬虫线程已退出，后台任务结束")

    return results


@mlol_api.get("/crawler/heroDetail")
async def crawler_hero_detail(id:int):
    """
    通过后台线程爬取英雄详情数据
    """
    # 启动后台总控线程（非阻塞，接口立即返回）
    hero_list = await HeroInfo.filter(is_crawl=False, category="mlol", id__lt=id)
    print(f'待爬取英雄数量：{len(hero_list)}')
    if not hero_list:
        return {
            "message": "没有待爬取英雄"
        }

    # 在后台线程中执行爬虫任务
    async def run_crawler_in_thread():
        results = background_crawl_task(hero_list, 3)
        # 在这里执行数据库操作，使用 await 方式

        # 更新英雄数据和皮肤数据
        for result in results:
            hero = result['hero']
            skin_data_list = result['skin_data_list']

            # 更新英雄状态
            await HeroInfo.filter(id=hero.id).update(
                is_crawl=True,
                update_time=datetime.now(),
                hero_id=hero.hero_id
            )

            # 插入皮肤数据
            for skin_data in skin_data_list:
                # 检查皮肤是否已存在
                existing_skin = await HeroSkin.filter(
                    hero_id=skin_data['hero_id'],
                    category=skin_data['category'],
                    skin_name=skin_data['skin_name']
                ).first()

                if not existing_skin:
                    await HeroSkin.create(
                        hero_id=skin_data['hero_id'],
                        hero_name=skin_data['hero_name'],
                        skin_name=skin_data['skin_name'],
                        skin_profile_url=skin_data['avatar_img'],
                        category=skin_data['category'],
                        create_time=datetime.now(),
                        update_time=datetime.now()
                    )

    import asyncio
    # 在现有的事件循环中创建任务
    loop = asyncio.get_event_loop()
    loop.create_task(run_crawler_in_thread())

    return {
        "status": "success",
        "message": "爬虫任务已在后台启动",
        "task_info": {
            "url_count": len(hero_list),
            "thread_count": 3
        }
    }