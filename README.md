# QY Crawler

这是一个开源的爬虫项目，主要用于从网络上爬取指定英雄的信息和详细资料。

## 目录结构

```
.
├── .gitignore
├── api
│   └── wzry.py
├── config
│   └── settings.py
├── main.py
├── orm
│   ├── __init__.py
│   └── models.py
└── static
    └── htmls
        └── wzry-hero-list.html
```

## 主要功能

- 提供 `/crawler/heros` 接口用于爬取英雄列表。
- 提供 `/crawler/heroDetail` 接口用于爬取英雄详细信息。

## 数据模型

- `HeroInfo`: 存储英雄的基本信息。
- `HeroSkin`: 存储英雄的皮肤信息。
- `HeroWord`: 存储英雄的相关文字信息。

## 使用技术

- 使用 `async` 异步框架提供 Web 接口。
- 使用 `Model` 类进行数据库模型定义。

## 静态资源

- `static/htmls/wzry-hero-list.html`: 展示爬取的英雄列表。

## 配置文件

- `config/settings.py`: 项目的配置文件。

## 入口文件

- `main.py`: 项目的入口文件。

## 如何贡献

欢迎提交 Issue 和 Pull Request。

## 许可证

该项目采用 MIT 许可证。详情请查看项目根目录下的 LICENSE 文件。