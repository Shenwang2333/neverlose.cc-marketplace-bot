import json
from pathlib import Path
from typing import Dict, Any

CONFIG_PATH = Path(__file__).parent / "neverlose_config.json"

_default_config = {
    "accounts": {
        "1": {"username": "用户名", "user_id": "123456", "secret": "填你token"},
        "2": {"username": "用户名",      "user_id": "123456", "secret": "填你token"},
        "3": {"username": "用户名",        "user_id": "123456", "secret": "填你token"}
    },
    "products": {
        "1": {"name": "123",              "code": "物品id", "desc": "描述",                 "account": "accounts id"},
        "2": {"name": "123",             "code": "物品id", "desc": "描述",          "account": "accounts id"},
        "3": {"name": "123",        "code": "物品id", "desc": "描述",        "account": "accounts id"},
        "4": {"name": "123",  "code": "物品id", "desc": "描述",  "account": "accounts id"}
    },
    "allowed_users_map": {
        "qq号": "accounts id",
        "qq号": "accounts id",
        "qq号": "accounts id"
    }
}


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(_default_config, f, indent=2, ensure_ascii=False)
    return _default_config