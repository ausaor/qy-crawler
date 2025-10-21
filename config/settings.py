TORTOISE_ORM = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.mysql",
                "credentials": {
                    "host": "127.0.0.1",
                    "port": 3306,
                    "user": "root",
                    "password": "root",
                    "database": "qy-crawler",
                    "minsize": 1,
                    "maxsize": 5,
                    "charset": "utf8mb4",
                    "echo": True
                }
            }
        },
        "apps": {
            "models": {
                "models": ["orm.models", "aerich.models"],
                "default_connection": "default",
            }
        },
        "use_tz": True,
        "timezone": "Asia/Shanghai",
    }