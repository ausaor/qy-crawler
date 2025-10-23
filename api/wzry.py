import time

from fastapi import APIRouter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from orm.models import HeroInfo, HeroSkin
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

