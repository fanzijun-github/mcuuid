import os
import json
import uuid
import time
import requests

# 缓存文件路径 - 使用绝对路径确保在任何模块中都能正确访问
# 获取项目根目录（mcuuid目录的上一级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, "uuid_cache.json")


# 加载缓存
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


# 保存缓存
def save_cache(cache_data):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2)


# 检查是否为 v4 UUID
def is_valid_uuidv4(input_uuid):
    try:
        parsed_uuid = uuid.UUID(str(input_uuid))
        return parsed_uuid.version == 4
    except ValueError:
        return False


# 查询 Mojang API 判断是否为正版 UUID（带缓存）
def query_mojang_api(uuid_str, cache):
    if uuid_str in cache:
        status, name = cache[uuid_str]
        return status, name

    url = f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid_str}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            name = data['name']
            cache[uuid_str] = ("valid", name)
            save_cache(cache)
            return "valid", name
        elif response.status_code == 204:
            cache[uuid_str] = ("offline", None)
            save_cache(cache)
            return "offline", None
        else:
            print(f"⚠️ API 返回非预期状态码 {response.status_code}（UUID: {uuid_str}）")
            return "?", None
    except Exception as e:
        print(f"⚠️ API 请求失败 (UUID: {uuid_str}): {e}")
        return "?", None


# 从 playerdata 文件夹判断是否有存档
def has_playerdata(world_folder, uuid_str):
    playerdata_path = os.path.join(world_folder, "playerdata")
    if not os.path.isdir(playerdata_path):
        return False

    uuid_canonical = str(uuid.UUID(uuid_str))  # 加上连字符的标准格式
    candidates = [
        os.path.join(playerdata_path, f"{uuid_str}.dat"),
        os.path.join(playerdata_path, f"{uuid_canonical}.dat"),
    ]

    for path in candidates:
        if os.path.isfile(path):
            return True

    return False