from orm.models import HeroInfo, HeroSkin, HeroWord
import time
import threading
import queue
import asyncio
import requests
import json
import os

from fastapi import APIRouter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# 配置日志，方便查看后台爬虫运行状态
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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


@wzry_api.get("/crawler/heroDetail")
async def crawler_hero_detail(id: int):
    """
    爬取英雄详情(多线程版本)
    """
    # 获取所有未爬取英雄列表, id小于15
    hero_list = await HeroInfo.filter(is_crawl=False, category="王者荣耀", id__lt=id)
    print(f'待爬取英雄数量：{len(hero_list)}')
    if not hero_list:
        return {
            "message": "没有待爬取英雄"
        }

    # 设置 ChromeDriver 路径（需自行下载）
    driver_path = 'F:/software/chromedriver/chromedriver-win64/chromedriver.exe'  # 请替换为你的 chromedriver 实际路径
    
    # 使用线程池处理多线程任务
    max_workers = min(len(hero_list), 3)  # 最多同时运行3个线程，避免过多资源占用
    success_count = 0
    failed_count = 0
    
    def process_hero(hero):
        # 线程停止1秒
        time.sleep(1)
        """处理单个英雄的函数，在线程中执行"""
        # 每个线程需要自己的webdriver实例
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service)
        
        try:
            url = hero.hero_detail_url
            driver.get(url)
            # 显式等待：等待英雄详情页面加载完成
            wait = WebDriverWait(driver, 10)
            hero_skins = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pic-pf")))

            # 获取英雄皮肤头像列表
            skin_avatars = hero_skins.find_elements(By.TAG_NAME, "li")
            skin_data_list = []
            
            for avatar in skin_avatars:
                # 获取英雄皮肤头像链接 例：https://game.gtimg.cn/images/yxzj/img201606/heroimg/564/564-smallskin-1.jpg
                img = avatar.find_element(By.TAG_NAME, "img")
                avatar_img = img.get_attribute("src")
                print(f'英雄[{hero.hero_name}]皮肤头像链接：{avatar_img}')

                # 获取皮肤名称
                skin_name = img.get_attribute("data-title")
                print(f'英雄[{hero.hero_name}]皮肤名称：{skin_name}')

                # 获取皮肤详情链接 例：https://game.gtimg.cn/images/yxzj/img201606/skin/hero-info/564/564-bigskin-6.jpg
                skin_url = 'https:' + img.get_attribute("data-imgname")
                print(f'英雄[{hero.hero_name}]皮肤详情链接：{skin_url}')

                # 如果hero.hero_id是null,根据皮肤头像链接获取英雄id
                if hero.hero_id is None:
                    hero.hero_id = avatar_img.split("/")[-1].split("-")[0]
                    print(f'英雄[{hero.hero_name}]英雄id：{hero.hero_id}')
                    
                skin_data_list.append({
                    'hero_id': hero.hero_id,
                    'hero_name': hero.hero_name,
                    'avatar_img': avatar_img,
                    'skin_name': skin_name,
                    'skin_url': skin_url,
                    'category': "王者荣耀"
                })
                
            return hero.id, hero.hero_id, skin_data_list, None
        except Exception as e:
            print(f'处理英雄[{hero.hero_name}]时发生异常: {e}')
            return hero.id, hero.hero_id, None, str(e)
        finally:
            driver.quit()
            print(f"英雄[{hero.hero_name}]浏览器已关闭")

    # 收集所有爬取结果
    all_skin_data = []
    heroes_to_update = []  # 记录需要更新的英雄
    
    # 在线程池中执行任务
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_hero = {executor.submit(process_hero, hero): hero for hero in hero_list}
            
            # 处理完成的任务
            for future in as_completed(future_to_hero):
                t_id, hero_id, skin_data_list, error = future.result()
                
                if error:
                    failed_count += 1
                    continue
                    
                success_count += 1
                # 添加到全局皮肤数据列表中
                all_skin_data.extend(skin_data_list)
                # 记录需要更新的英雄信息
                heroes_to_update.append({
                    'id': t_id,
                    'hero_id': hero_id
                })
                
    except Exception as e:
        print(f'多线程处理过程中发生异常: {e}')
        return {
            "message": f"多线程处理过程中发生异常: {e}"
        }
    
    # 更新所有成功的英雄状态
    updated_heroes = 0
    for hero_data in heroes_to_update:
        try:
            await HeroInfo.filter(id=hero_data['id']).update(
                hero_id=hero_data['hero_id'], 
                is_crawl=True, 
                update_time=datetime.now()
            )
            # 获取英雄名称用于日志输出
            hero = next(h for h in hero_list if h.id == hero_data['id'])
            print(f'英雄[{hero.hero_name}]信息更新成功')
            updated_heroes += 1
        except Exception as e:
            print(f'更新英雄[id={hero_data["id"]}]信息时发生异常: {e}')
            failed_count += 1
    
    # 处理所有收集到的皮肤数据
    created_skins = 0
    updated_skins = 0
    
    for skin_data in all_skin_data:
        try:
            # 创建英雄皮肤数据，判断是否已存在
            skin_obj = await HeroSkin.get_or_none(
                hero_id=skin_data['hero_id'], 
                category=skin_data['category'], 
                skin_name=skin_data['skin_name'], 
                hero_name=skin_data['hero_name']
            )
            
            if skin_obj is None:
                # 如果皮肤不存在，则创建新记录
                await HeroSkin.create(
                    hero_id=skin_data['hero_id'],
                    hero_name=skin_data['hero_name'],
                    skin_name=skin_data['skin_name'],
                    skin_url=skin_data['skin_url'],
                    skin_profile_url=skin_data['avatar_img'],
                    category=skin_data['category'],
                    create_time=datetime.now(),
                    update_time=datetime.now()
                )
                created_skins += 1
                print(f'英雄[{skin_data["hero_name"]}]皮肤[{skin_data["skin_name"]}]创建成功')
            else:
                # 如果皮肤已存在，更新记录
                skin_obj.skin_url = skin_data['skin_url']
                skin_obj.skin_profile_url = skin_data['avatar_img']
                skin_obj.update_time = datetime.now()
                await skin_obj.save()
                updated_skins += 1
                print(f'英雄[{skin_data["hero_name"]}]皮肤[{skin_data["skin_name"]}]更新成功')
        except Exception as e:
            print(f'处理皮肤数据[{skin_data["skin_name"]}]时发生异常: {e}')
            failed_count += 1
            
    print(f"爬取完成，成功处理英雄: {success_count}，失败: {failed_count}")
    print(f"皮肤数据统计：新增 {created_skins}，更新 {updated_skins}")
        
    return {
        "message": "爬取完成",
        "heroes_success": success_count,
        "heroes_failed": failed_count,
        "heroes_updated": updated_heroes,
        "skins_created": created_skins,
        "skins_updated": updated_skins
    }


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
            hero_skins = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pic-pf")))

            # 获取英雄皮肤头像列表
            skin_avatars = hero_skins.find_elements(By.TAG_NAME, "li")
            skin_data_list = []

            for avatar in skin_avatars:
                # 获取英雄皮肤头像链接 例：https://game.gtimg.cn/images/yxzj/img201606/heroimg/564/564-smallskin-1.jpg
                img = avatar.find_element(By.TAG_NAME, "img")
                avatar_img = img.get_attribute("src")
                print(f'英雄[{hero.hero_name}]皮肤头像链接：{avatar_img}')

                # 获取皮肤名称
                skin_name = img.get_attribute("data-title")
                print(f'英雄[{hero.hero_name}]皮肤名称：{skin_name}')

                # 获取皮肤详情链接 例：https://game.gtimg.cn/images/yxzj/img201606/skin/hero-info/564/564-bigskin-6.jpg
                skin_url = 'https:' + img.get_attribute("data-imgname")
                print(f'英雄[{hero.hero_name}]皮肤详情链接：{skin_url}')

                # 如果hero.hero_id是null,根据皮肤头像链接获取英雄id
                if hero.hero_id is None:
                    hero.hero_id = avatar_img.split("/")[-1].split("-")[0]
                    print(f'英雄[{hero.hero_name}]英雄id：{hero.hero_id}')

                skin_data_list.append({
                    'hero_id': hero.hero_id,
                    'hero_name': hero.hero_name,
                    'avatar_img': avatar_img,
                    'skin_name': skin_name,
                    'skin_url': skin_url,
                    'category': "王者荣耀"
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


@wzry_api.get("/crawler/heroDetailByBg")
async def crawler_hero_detail_by_bg():
    """
    通过后台线程爬取英雄详情数据
    """
    # 启动后台总控线程（非阻塞，接口立即返回）
    hero_list = await HeroInfo.filter(is_crawl=False, category="王者荣耀")
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
                        skin_url=skin_data['skin_url'],
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


def hero_word_worker(queue, thread_id, result_queue):
    """处理英雄语音台词的工作线程：从队列获取英雄信息并爬取语音台词"""
    logger.info(f"英雄语音台词线程 {thread_id} 初始化完成")
    
    while True:
        hero_info = queue.get()
        if hero_info is None:  # 结束信号
            break
            
        logger.info(f"英雄语音台词线程 {thread_id} 开始处理: {hero_info.hero_name}")
        
        try:
            # 爬取的链接格式：https://pvp.qq.com/zlkdatasys/yuzhouzhan/herovoice/172.json?t=1761263896565，172是英雄id，1761263896565是时间戳
            url = f"https://pvp.qq.com/zlkdatasys/yuzhouzhan/herovoice/{hero_info.hero_id}.json?t={int(time.time() * 1000)}"
            
            # 添加请求头（模拟浏览器，避免部分网站拒绝请求）
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            # 发送GET请求，设置超时时间（避免无限等待）
            response = requests.get(url, headers=headers, timeout=10)

            # 检查请求是否成功（状态码200表示成功）
            response.raise_for_status()  # 若状态码非200，会抛出HTTPError

            # 解析JSON内容
            json_data = response.json()

            save_path = os.path.join(f"static/json/wzry/voice/", f"{hero_info.hero_name}.json")
            # 处理保存路径：确保目录存在
            dir_path = os.path.dirname(save_path)
            if dir_path:  # 若目录不为空（即不是当前目录）
                os.makedirs(dir_path, exist_ok=True)  # 递归创建目录，exist_ok=True避免目录已存在时报错

            # 保存解析后的Python对象（自动格式化，确保JSON规范，推荐）
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)  # indent=2：格式化缩进，更易读

            print(f"英雄[{hero_info.hero_name}]JSON文件已成功保存到：{os.path.abspath(save_path)}")

            # 获取json_data的dqpfyy_5403属性
            dqpfyy_5403 = json_data.get("dqpfyy_5403")
            print(f"英雄[{hero_info.hero_name}]dqpfyy_5403", dqpfyy_5403)

            hero_word_list = []
            # 如果dqpfyy_5403是一个列表，则循环处理
            if isinstance(dqpfyy_5403, list):
                for words in dqpfyy_5403:
                    yylbzt_9132 = words.get("yylbzt_9132")
                    if yylbzt_9132:
                        for item in yylbzt_9132:
                            word = item.get("yywbzt_1517")
                            print(f"英雄[{hero_info.hero_name}]台词：", word)
                            voice_url = "https:" + item.get("yywjzt_5304")
                            print(f"英雄[{hero_info.hero_name}]语音链接：", voice_url)
                            hero_word_list.append({
                                "hero_id": hero_info.hero_id,
                                "hero_name": hero_info.hero_name,
                                "word": word,
                                "voice_url": voice_url,
                                "category": "王者荣耀",
                                "create_time": datetime.now(),
                                "update_time": datetime.now()
                            })
            else:
                # 获取dqpfyy_5403的属性yylbzt_9132，是一个list
                yylbzt_9132 = dqpfyy_5403.get("yylbzt_9132")
                if yylbzt_9132:
                    for item in yylbzt_9132:
                        word = item.get("yywbzt_1517")
                        print(f"英雄[{hero_info.hero_name}]台词：", word)
                        voice_url = "https:" + item.get("yywjzt_5304")
                        print(f"英雄[{hero_info.hero_name}]语音链接：", voice_url)
                        hero_word_list.append({
                            "hero_id": hero_info.hero_id,
                            "hero_name": hero_info.hero_name,
                            "word": word,
                            "voice_url": voice_url,
                            "category": "王者荣耀",
                            "create_time": datetime.now(),
                            "update_time": datetime.now()
                        })

            # 将结果放入结果队列
            result_queue.put({
                'hero': hero_info,
                'hero_word_list': hero_word_list,
                'success': True
            })
            
            logger.info(f"英雄语音台词线程 {thread_id} 处理完成: {hero_info.hero_name}")
            
            # 控制爬取速度
            time.sleep(1)
            
        except requests.exceptions.ConnectionError:
            logger.error(f"英雄语音台词线程 {thread_id} 处理 {hero_info.hero_name} 时发生网络连接错误")
            result_queue.put({
                'hero': hero_info,
                'hero_word_list': [],
                'success': False,
                'error': '网络连接失败'
            })
        except requests.exceptions.Timeout:
            logger.error(f"英雄语音台词线程 {thread_id} 处理 {hero_info.hero_name} 时发生请求超时")
            result_queue.put({
                'hero': hero_info,
                'hero_word_list': [],
                'success': False,
                'error': '请求超时'
            })
        except requests.exceptions.HTTPError as e:
            logger.error(f"英雄语音台词线程 {thread_id} 处理 {hero_info.hero_name} 时发生HTTP错误: {e.response.status_code}")
            result_queue.put({
                'hero': hero_info,
                'hero_word_list': [],
                'success': False,
                'error': f'请求失败，状态码：{e.response.status_code}'
            })
        except json.JSONDecodeError:
            logger.error(f"英雄语音台词线程 {thread_id} 处理 {hero_info.hero_name} 时发生JSON解析错误")
            result_queue.put({
                'hero': hero_info,
                'hero_word_list': [],
                'success': False,
                'error': 'JSON格式无效，无法解析'
            })
        except Exception as e:
            logger.error(f"英雄语音台词线程 {thread_id} 处理 {hero_info.hero_name} 时发生未知错误: {e}", exc_info=True)
            result_queue.put({
                'hero': hero_info,
                'hero_word_list': [],
                'success': False,
                'error': f'发生未知错误：{e}'
            })
        finally:
            queue.task_done()


def background_hero_word_task(hero_list, thread_count):
    """后台总控任务：创建队列和爬虫线程，分配英雄语音台词爬取任务"""
    logger.info(f"开始后台英雄语音台词爬虫任务，共 {len(hero_list)} 个英雄，使用 {thread_count} 个线程")

    # 创建任务队列
    task_queue = queue.Queue()
    result_queue = queue.Queue()
    
    for hero in hero_list:
        task_queue.put(hero)

    # 启动爬虫线程
    threads = []
    for i in range(thread_count):
        t = threading.Thread(
            target=hero_word_worker,
            args=(task_queue, i, result_queue),
            name=f"HeroWord-{i}"
        )
        t.start()
        threads.append(t)

    # 等待所有任务处理完成
    task_queue.join()
    logger.info("所有英雄语音台词爬取完成")

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
        
    logger.info("所有英雄语音台词爬虫线程已退出，后台任务结束")
    
    return results


@wzry_api.get("/crawler/heroWord")
async def crawler_hero_word(id: int):
    """
    爬取英雄语音台词(多线程版本)
    """
    hero_info_list = await HeroInfo.filter(is_crawl=False, category="王者荣耀", id__lt=id)
    print(f'待爬取英雄数量：{len(hero_info_list)}')
    if not hero_info_list:
        return {
            "message": "没有待爬取英雄"
        }

    # 在后台线程中执行爬虫任务
    async def run_hero_word_crawler_in_thread():
        results = background_hero_word_task(hero_info_list, 3)
        # 在这里执行数据库操作，使用 await 方式
        
        success_count = 0
        failed_count = 0
        
        # 处理每个英雄的结果
        for result in results:
            hero = result['hero']
            hero_word_list = result['hero_word_list']
            
            if result['success']:
                try:
                    # 使用 bulk_create 批量插入台词数据
                    if hero_word_list:
                        hero_words = []
                        for word_data in hero_word_list:
                            hero_words.append(HeroWord(**word_data))

                        # 批量插入，每批100条记录
                        await HeroWord.bulk_create(hero_words, batch_size=100)
                        print(f"批量插入{hero.hero_name}的台词数据成功，共插入 {len(hero_words)} 条台词数据")

                    # 更新爬虫状态
                    await HeroInfo.filter(id=hero.id).update(
                        is_crawl=True,
                        update_time=datetime.now()
                    )
                    
                    success_count += 1
                    print(f"英雄[{hero.hero_name}]语音台词数据处理成功")
                except Exception as e:
                    failed_count += 1
                    print(f"处理英雄[{hero.hero_name}]台词数据时发生数据库错误: {e}")
            else:
                failed_count += 1
                print(f"处理英雄[{hero.hero_name}]台词数据失败: {result['error']}")

        print(f"英雄语音台词爬取完成，成功: {success_count}，失败: {failed_count}")
        
    # 在现有的事件循环中创建任务
    loop = asyncio.get_event_loop()
    loop.create_task(run_hero_word_crawler_in_thread())

    return {
        "status": "success",
        "message": "英雄语音台词爬虫任务已在后台启动",
        "task_info": {
            "hero_count": len(hero_info_list),
            "thread_count": 3
        }
    }

