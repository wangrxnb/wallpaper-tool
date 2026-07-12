"""
图片获取模块
调用远程 API 获取随机图片，支持两种模式：
  - 模式 A：API 直接返回图片二进制数据
  - 模式 B：API 返回 JSON（含图片 URL），再下载图片
"""
import json
import os
import time
from typing import Optional, Tuple

import requests


# 模拟浏览器 User-Agent，提高请求成功率
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.luvbree.com/",
}


def _create_session() -> requests.Session:
    """创建带 Cloudflare 绕过的 session"""
    try:
        import cloudscraper
        session = cloudscraper.create_scraper()
        session.headers.update(DEFAULT_HEADERS)
        return session
    except ImportError:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        return session


def fetch_and_download(api_url: str, api_params: dict, save_path: str) -> str:
    """
    调用 API 获取图片并保存到本地（一步完成）

    自动判断 API 返回的是图片二进制还是 JSON：
      - 直接返回图片 → 保存到 save_path
      - 返回 JSON（含 URL）→ 从 URL 下载后保存

    Args:
        api_url: API 地址
        api_params: 查询参数
        save_path: 本地保存路径

    Returns:
        保存的绝对路径

    Raises:
        RuntimeError: API 请求或下载失败
    """
    session = _create_session()

    try:
        resp = session.get(api_url, params=api_params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"API 请求失败: {e}")

    content_type = resp.headers.get("Content-Type", "").lower()

    # ── 模式 A：API 直接返回图片 ──
    if content_type.startswith("image/") or _is_image_data(resp.content):
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(resp.content)
        return os.path.abspath(save_path)

    # ── 模式 B：API 返回 JSON，从中提取图片 URL ──
    try:
        data = resp.json()
    except (json.JSONDecodeError, ValueError):
        raise RuntimeError(
            f"API 返回了非 JSON 也非图片的数据，可能是被 Cloudflare 拦截。\n"
            f"请确保已安装 cloudscraper: pip install cloudscraper\n"
            f"Content-Type: {content_type}\n"
            f"响应前 200 字符: {resp.text[:200]}"
        )

    image_url = _extract_url(data)
    if not image_url:
        raise RuntimeError(f"无法从 API 响应中提取图片 URL，响应内容: {data}")

    # 下载图片
    return _download_from_url(session, image_url, save_path)


def _is_image_data(data: bytes) -> bool:
    """通过魔数判断是否为图片二进制数据"""
    if len(data) < 8:
        return False
    # WEBP: RIFF....WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    # JPEG
    if data[:3] == b"\xff\xd8\xff":
        return True
    # PNG
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    # BMP
    if data[:2] == b"BM":
        return True
    # GIF
    if data[:6] in (b"GIF89a", b"GIF87a"):
        return True
    return False


def _extract_url(data) -> Optional[str]:
    """从 API JSON 响应中提取图片 URL，兼容多种格式"""
    if isinstance(data, str):
        return data

    if not isinstance(data, dict):
        return None

    for key in ("url", "imageUrl", "image_url", "src", "link", "img", "path"):
        if key in data and isinstance(data[key], str):
            return data[key]

    if "data" in data:
        inner = data["data"]
        if isinstance(inner, str):
            return inner
        if isinstance(inner, dict):
            for key in ("url", "imageUrl", "image_url", "src", "link", "img"):
                if key in inner and isinstance(inner[key], str):
                    return inner[key]

    return None


def _download_from_url(session: requests.Session, image_url: str, save_path: str) -> str:
    """从 URL 下载图片到本地"""
    try:
        resp = session.get(image_url, timeout=60, stream=True)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"图片下载失败: {e}")

    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)

    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return os.path.abspath(save_path)


def generate_filename(timestamp: Optional[float] = None) -> str:
    """按时间戳生成文件名"""
    t = timestamp or time.time()
    return f"wallpaper_{time.strftime('%Y%m%d_%H%M%S', time.localtime(t))}.webp"
