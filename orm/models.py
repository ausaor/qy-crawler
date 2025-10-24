from tortoise.models import Model
from tortoise import fields

class HeroInfo(Model):
    id = fields.IntField(pk=True, generated=True, description="id")
    hero_name = fields.CharField(max_length=50, description="英雄名称")
    hero_alias_name = fields.CharField(max_length=50, null=True, description="英雄别名")
    hero_detail_url = fields.CharField(max_length=1500, null=True, description="英雄详情链接")
    hero_profile_url = fields.CharField(max_length=1500, null=True, description="英雄头像链接")
    hero_id = fields.CharField(max_length=50, null=True, description="英雄id")
    is_crawl = fields.BooleanField(default=False, description="是否爬取")
    category = fields.CharField(max_length=50, description="类别")
    create_time = fields.DatetimeField(null=True, description="创建时间")
    update_time = fields.DatetimeField(null=True, description="更新时间")

    class Meta:
        table = "t_hero_info"
        table_description = "英雄信息表"
        unique_together = ("hero_name", "category")


class HeroSkin(Model):
    id = fields.IntField(pk=True, generated=True, description="id")
    hero_id = fields.CharField(max_length=50, description="英雄id")
    hero_name = fields.CharField(max_length=50, description="英雄名称")
    skin_name = fields.CharField(max_length=50, description="皮肤名称")
    skin_url = fields.CharField(max_length=1500, null=True, description="皮肤图片链接")
    skin_profile_url = fields.CharField(max_length=1500, null=True, description="皮肤头像链接")
    category = fields.CharField(max_length=50, description="类别")
    is_crawl = fields.BooleanField(default=False, description="是否爬取")
    create_time = fields.DatetimeField(null=True, description="创建时间")
    update_time = fields.DatetimeField(null=True, description="更新时间")

    class Meta:
        table = "t_hero_skin"
        table_description = "英雄皮肤数据表"
        unique_together = ("hero_id", "category", "skin_name")


class HeroWord(Model):
    id = fields.IntField(pk=True, generated=True, description="id")
    hero_id = fields.CharField(max_length=50, description="英雄id")
    hero_name = fields.CharField(max_length=50, description="英雄名称")
    category = fields.CharField(max_length=20, description="类别")
    word = fields.CharField(max_length=200, null=True, description="台词")
    voice_url = fields.CharField(max_length=1500, null=True, description="台词语音")
    is_crawl = fields.BooleanField(default=False, description="是否爬取")
    create_time = fields.DatetimeField(null=True, description="创建时间")
    update_time = fields.DatetimeField(null=True, description="更新时间")

    class Meta:
        table = "t_hero_word"
        table_description = "英雄台词表"
