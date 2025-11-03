from fastapi import FastAPI
import uvicorn
from tortoise.contrib.fastapi import register_tortoise

from api.wzry import wzry_api
from api.lol import lol_api
from api.mlol import mlol_api
from api.vshero import vshero_api
from api.ping_an_jing import paj_api
from api.yhzr import yhzr_api
from config import settings
app = FastAPI(
    docs_url="/api/docs",  # 将 Swagger UI 文档路径改为 /api/docs
    redoc_url="/api/redoc", # 将 ReDoc 文档路径改为 /api/redoc
)

register_tortoise(
    app,
    config=settings.TORTOISE_ORM,
)

app.include_router(wzry_api, prefix="/wzry", tags=["王者荣耀接口"])
app.include_router(lol_api, prefix="/lol", tags=["英雄联盟接口"])
app.include_router(mlol_api, prefix="/mlol", tags=["英雄联盟手游接口"])
app.include_router(vshero_api, prefix="/vshero", tags=["曙光英雄接口"])
app.include_router(paj_api, prefix="/paj", tags=["决战平安京接口"])
app.include_router(yhzr_api, prefix="/yhzr", tags=["英魂之刃接口"])

if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8080, log_level="info", reload=True)