from fastapi import APIRouter
import httpx
from orm.models import HeroInfo
from tortoise.exceptions import IntegrityError
from datetime import datetime

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