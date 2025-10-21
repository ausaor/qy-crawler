from tortoise.models import Model
from tortoise import fields

class HeroInfo(Model):
    id = fields.IntField(pk=True, generated=True, description="id")
    hero_name = fields.CharField(max_length=50, description="英雄名称")
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