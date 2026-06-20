import httpx
import hashlib
import uuid
from typing import Dict, Any
from nonebot import on_command, get_driver
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.params import CommandArg
from nonebot.log import logger
from nonebot.exception import FinishedException
from functools import wraps

from src.plugins.blacklist import check_blacklist
from .config import load_config

_config = load_config()
ACCOUNTS = _config["accounts"]
PRODUCTS = _config["products"]
ALLOWED_USERS_MAP = _config["allowed_users_map"]
ALLOWED_USERS = [int(uid) for uid in ALLOWED_USERS_MAP]
NL_API_URL = "https://user-api.neverlose.cc/api/market"

class NeverloseAPI:
    def __init__(self, user_id: str, secret: str, base_url: str):
        self.user_id = user_id
        self.secret = secret
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    def _generate_signature(self, data: Dict[str, Any]) -> str:
        sorted_keys = sorted(data.keys())
        str_to_hash = "".join(f"{k}{data[k]}" for k in sorted_keys) + self.secret
        return hashlib.sha256(str_to_hash.encode()).hexdigest()

    async def _request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params["user_id"] = self.user_id
        params["signature"] = self._generate_signature(params)
        try:
            resp = await self.client.post(f"{self.base_url}/{method}", json=params)
            return resp.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return {"success": False, "error": str(e)}

    async def give_item(self, username: str, item_code: str) -> Dict[str, Any]:
        params = {"id": str(uuid.uuid4())[:8], "username": username, "code": item_code}
        return await self._request("give-for-free", params)

    async def get_balance(self) -> float:
        result = await self._request("get-balance", {})
        return result.get("balance", 0.0)

    async def close(self):
        await self.client.aclose()


nl_api: Dict[str, NeverloseAPI] = {}
for aid, acc in ACCOUNTS.items():
    nl_api[aid] = NeverloseAPI(acc["user_id"], acc["secret"], NL_API_URL)

def check_permission(func):
    @wraps(func)
    async def wrapper(bot: Bot, event: Event, *args, **kwargs):
        if int(event.get_user_id()) not in ALLOWED_USERS:
            await bot.send(event, "你没有权限使用此功能")
            return
        return await func(bot, event, *args, **kwargs)
    return wrapper

balance_cmd = on_command("/nle", aliases={"/balance", "/mybal"}, priority=5)

@balance_cmd.handle()
@check_permission
@check_blacklist
async def handle_balance(bot: Bot, event: Event):
    user_id = event.get_user_id()
    account_id = ALLOWED_USERS_MAP.get(user_id, "1")

    try:
        balance = await nl_api[account_id].get_balance()
        msg = f"Balance：{balance} NLE"
    except Exception as e:
        logger.error(f"查询余额失败: {e}")
        msg = "查询失败"

    await balance_cmd.finish(msg)

give_cmd = on_command("/bind", aliases={"/赠送", "/give"}, priority=5)

@give_cmd.handle()
@check_permission
@check_blacklist
async def handle_give(bot: Bot, event: Event, arg=CommandArg()):
    args = arg.extract_plain_text().strip().split()

    if len(args) < 2:
        msg = "格式错误"
        for key, prod in PRODUCTS.items():
            msg += f"  {key} - {prod['name']} (account {prod.get('account', '?')})\n"
        await give_cmd.finish(msg)

    username = args[0]
    product_key = args[1]

    if product_key not in PRODUCTS:
        await give_cmd.finish(f"物品 {product_key} 不存在")

    product = PRODUCTS[product_key]
    account_id = product.get("account", "1")

    try:
        result = await nl_api[account_id].give_item(username, product["code"])
        logger.debug(f"赠送API响应: {result}")

        if result.get("success"):
            account_username = ACCOUNTS[account_id]["username"]
            msg = (
                f"item given\n"
                f"• user：{username}\n"
                f"• another：{account_username}"
                f"• item：{product['name']}\n"
            )
        else:
            error_msg = result.get("error", "未知错误")
            if "user not found" in error_msg.lower() or "doesn't exist" in error_msg.lower():
                msg = f"用户 {username} 不存在"
            else:
                msg = f"绑定失败：{error_msg}"
    except Exception as e:
        logger.error(f"绑定失败: {e}")
        msg = "api请求超时"

    await give_cmd.finish(msg)

market_cmd = on_command("/market", priority=5)

@market_cmd.handle()
@check_permission
@check_blacklist
async def handle_market(bot: Bot, event: Event):
    msg = "• market items：\n"
    for key, prod in PRODUCTS.items():
        msg += f"  {key} - {prod['name']} (account {prod.get('account', '?')})\n"
    await market_cmd.finish(msg)

author_cmd = on_command("/us", aliases={"/author"}, priority=5)

@author_cmd.handle()
@check_permission
@check_blacklist
async def handle_author(bot: Bot, event: Event):
    msg = (
        "[1] Shenwang2333\n• Joined:May 2, 2023\n\n"
        "[2] lovelust\n• Joined:Sep 19, 2024\n\n"
        "[3] Hlines\n• Joined:Dec 25, 2022"
    )
    await author_cmd.finish(msg)

driver = get_driver()

@driver.on_shutdown
async def shutdown():
    for api in nl_api.values():
        await api.close()