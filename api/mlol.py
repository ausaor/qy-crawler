from fastapi import APIRouter
import httpx
from datetime import datetime
from tortoise.exceptions import IntegrityError
from orm.models import HeroInfo

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