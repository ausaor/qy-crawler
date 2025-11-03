from datetime import datetime
import time
import threading
import queue
from queue import Empty

from fastapi import APIRouter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup

from orm.models import HeroInfo, HeroSkin

import logging

# 配置日志，方便查看后台爬虫运行状态
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

yhzr_api = APIRouter()

@yhzr_api.get("/crawler/heros")
async def crawler_heros():
    """
    爬取英魂之刃英雄数据
    """
    # 设置 ChromeDriver 路径（需自行下载）
    driver_path = 'F:/software/chromedriver/chromedriver-win64/chromedriver.exe'  # 请替换为你的 chromedriver 实际路径
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service)

    url = "https://cos.99.com/data/"

    try:
        driver.get(url)
        # 显式等待：等待特定英雄列表元素加载完成
        # 替换 'hero-list' 为实际页面中的目标元素ID或选择器
        wait = WebDriverWait(driver, 10)

        print(driver.title)  # 打印页面标题

        hero_list = wait.until(EC.presence_of_element_located((By.ID, "heroList")))  # 请替换为实际选择器
        hero_list_li = hero_list.find_elements(By.TAG_NAME, "li")

        print(f'英雄列表数量：{len(hero_list_li)}')

        # 用于统计插入和更新的记录数
        inserted_count = 0
        updated_count = 0

        for li in hero_list_li:
            a = li.find_element(By.TAG_NAME, "a")
            # 获取英雄名称 a标签的title属性
            hero_name = a.get_attribute("title")
            print(f'英雄名称：{hero_name}')

            # 获取英雄详情链接,从a标签中获取，例：https://cos.99.com/data/hero.shtml?id=237001
            hero_detail_url = a.get_attribute("href")
            print(f'英雄详情链接：{hero_detail_url}')

            # 根据英雄详情链接提取英雄ID，从https://cos.99.com/data/hero.shtml?id=237001提取最后的id
            hero_id = hero_detail_url.split("=")[-1]
            print(f'英雄ID：{hero_id}')

            # 获取英雄头像链接
            img = a.find_element(By.XPATH, ".//div//img")
            hero_avatar_src = img.get_attribute("data-original")
            print(f'英雄头像链接：{hero_avatar_src}')

            # 尝试查找数据库中是否已存在该英雄
            hero_obj = await HeroInfo.get_or_none(hero_name=hero_name, category="英魂之刃")

            # 获取当前时间
            current_time = datetime.now()

            if hero_obj is None:
                # 如果英雄不存在，则创建新记录
                await HeroInfo.create(
                    hero_id=hero_id,
                    hero_name=hero_name,
                    hero_detail_url=hero_detail_url,
                    hero_profile_url=hero_avatar_src,
                    category="英魂之刃",
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


@yhzr_api.get("/crawler/heroDetailByBg")
async def crawler_hero_detail_by_bg(max_id: int):
    """
    通过后台线程爬取英雄详情数据
    """
    # 启动后台总控线程（非阻塞，接口立即返回）
    hero_list = await HeroInfo.filter(is_crawl=False, category="英魂之刃", id = max_id)
    print(f'待爬取英雄数量：{len(hero_list)}')
    if not hero_list:
        return {
            "message": "没有待爬取英雄"
        }

    # 在后台线程中执行爬虫任务
    async def run_crawler_in_thread():
        results = background_crawl_task(hero_list, 1)
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

            # 判断皮肤数据是否为空
            if not skin_data_list:
                 continue

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
            try:
                hero = queue.get(timeout=5)
            except Empty:
                # 超时，继续尝试获取任务
                continue

            if hero is None:  # 结束信号
                break

            logger.info(f"爬虫线程 {thread_id} 开始爬取: {hero.hero_name}")

            driver.get(hero.hero_detail_url)

            # 显式等待：等待英雄详情页面加载完成
            wait = WebDriverWait(driver, 10)
            hero_skins = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "skin-hd")))

            # 获取英雄皮肤头像列表
            skin_avatars = hero_skins.find_elements(By.TAG_NAME, "a")

            # 判断皮肤数据是否为空
            if not skin_avatars:
                 continue
            skin_data_list = []

            for avatar in skin_avatars:
                # 获取英雄皮肤头像链接 例：https://mobavideo.99.com/games/cos/upload/yhzrheroheadimg/237001.png
                img = avatar.find_element(By.TAG_NAME, "img")
                avatar_img = img.get_attribute("src")

                if not avatar_img:
                    continue
                print(f'英雄[{hero.hero_name}]皮肤头像链接：{avatar_img}')

                # 获取皮肤名称
                skin_name = img.get_attribute("alt")
                print(f'英雄[{hero.hero_name}]皮肤名称：{skin_name}')

                skin_data_list.append({
                    'hero_id': hero.hero_id,
                    'hero_name': hero.hero_name,
                    'avatar_img': avatar_img,
                    'skin_name': skin_name,
                    'category': "英魂之刃"
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