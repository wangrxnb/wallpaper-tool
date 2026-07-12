"""
核心调度模块
协调图片获取、壁纸设置、定时器和本地缓存
"""
import json
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from fetcher import fetch_and_download, generate_filename
from scheduler import WallpaperScheduler
from setter import set_wallpaper


def _default_cache_dir() -> str:
    """默认缓存目录: ~/Pictures/Wallpapers"""
    home = Path.home()
    return str(home / "Pictures" / "Wallpapers")


class WallpaperCore:
    """壁纸核心管理器"""

    def __init__(self, config_path: str = "config.json"):
        self._config_path = os.path.abspath(config_path)
        self._config = self._load_config()

        # 缓存目录
        cache_dir = self._config.get("cache_dir") or _default_cache_dir()
        self._cache_dir = os.path.normpath(os.path.expandvars(os.path.expanduser(cache_dir)))
        os.makedirs(self._cache_dir, exist_ok=True)

        # 收藏目录
        self._favorite_dir = os.path.join(self._cache_dir, "favorites")
        os.makedirs(self._favorite_dir, exist_ok=True)

        # 当前壁纸路径
        self._current_wallpaper: Optional[str] = None

        # 定时器
        interval = self._config.get("interval_minutes", 1440)
        self._scheduler = WallpaperScheduler(
            callback=self.auto_switch_wallpaper,
            interval_minutes=interval,
        )

    # ── 配置 ──────────────────────────────────────────

    def _load_config(self) -> dict:
        """加载配置文件"""
        if not os.path.isfile(self._config_path):
            return {}
        with open(self._config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self) -> None:
        """保存配置到文件"""
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)

    @property
    def interval_minutes(self) -> int:
        return self._config.get("interval_minutes", 1440)

    @interval_minutes.setter
    def interval_minutes(self, minutes: int) -> None:
        self._config["interval_minutes"] = minutes
        self.save_config()
        self._scheduler.reset(new_interval_minutes=minutes)

    @property
    def auto_start(self) -> bool:
        return self._config.get("auto_start", False)

    @auto_start.setter
    def auto_start(self, enabled: bool) -> None:
        self._config["auto_start"] = enabled
        self.save_config()
        _set_autostart(enabled)

    @property
    def category_id(self) -> str:
        """当前选中的分类 ID"""
        return self._config.get("api_params", {}).get("categoryId", "")

    @category_id.setter
    def category_id(self, value: str) -> None:
        """更新分类 ID 并持久化"""
        if "api_params" not in self._config:
            self._config["api_params"] = {}
        self._config["api_params"]["categoryId"] = value
        self.save_config()

    @property
    def is_auto_running(self) -> bool:
        return self._scheduler.is_running

    @property
    def current_wallpaper(self) -> Optional[str]:
        return self._current_wallpaper

    @property
    def cache_dir(self) -> str:
        return self._cache_dir

    @property
    def config(self) -> dict:
        return self._config

    # ── 壁纸操作 ──────────────────────────────────────

    def switch_wallpaper(self) -> str:
        """
        手动切换壁纸：获取新图片 → 设置壁纸

        Returns:
            新壁纸的文件路径
        """
        api_url = self._config.get("api_url", "")
        api_params = self._config.get("api_params", {})

        if not api_url:
            raise RuntimeError("未配置 API 地址，请在 config.json 中设置 api_url")

        # 1. 获取并下载图片（一步完成，自动适应 API 返回格式）
        filename = generate_filename()
        save_path = os.path.join(self._cache_dir, filename)
        wallpaper_path = fetch_and_download(api_url, api_params, save_path)

        # 3. 设为壁纸
        fit_mode = self._config.get("fit_mode", "fill")
        success = set_wallpaper(wallpaper_path, fit_mode)

        if not success:
            raise RuntimeError("设置壁纸失败，Win32 API 返回 false")

        # 4. 更新状态
        self._current_wallpaper = wallpaper_path
        self._cleanup_old_cache()

        return wallpaper_path

    def auto_switch_wallpaper(self) -> str:
        """
        自动切换壁纸（由定时器触发）

        Returns:
            新壁纸的文件路径
        """
        try:
            return self.switch_wallpaper()
        except Exception as e:
            print(f"[自动切换失败] {e}")
            raise

    # ── 调度器控制 ────────────────────────────────────

    def start_auto_switch(self) -> None:
        """启动定时自动切换"""
        self._scheduler.start()

    def stop_auto_switch(self) -> None:
        """停止定时自动切换"""
        self._scheduler.stop()

    def reset_timer(self) -> None:
        """重置定时器（手动切换后调用，从当前时间重新计时）"""
        self._scheduler.reset()

    # ── 收藏管理 ──────────────────────────────────────

    def favorite_current(self) -> Optional[str]:
        """将当前壁纸复制到收藏目录"""
        if not self._current_wallpaper or not os.path.isfile(self._current_wallpaper):
            return None

        basename = os.path.basename(self._current_wallpaper)
        dest = os.path.join(self._favorite_dir, basename)
        shutil.copy2(self._current_wallpaper, dest)
        return dest

    # ── 缓存清理 ──────────────────────────────────────

    def _cleanup_old_cache(self) -> None:
        """清理过期缓存，保留最近 max_cache_count 张"""
        max_count = self._config.get("max_cache_count", 100)
        files = [
            os.path.join(self._cache_dir, f)
            for f in os.listdir(self._cache_dir)
            if os.path.isfile(os.path.join(self._cache_dir, f))
        ]
        files.sort(key=os.path.getmtime, reverse=True)

        # 跳过收藏目录里的文件
        favorites = set()
        if os.path.isdir(self._favorite_dir):
            for f in os.listdir(self._favorite_dir):
                favorites.add(f)

        for old_file in files[max_count:]:
            if os.path.basename(old_file) not in favorites:
                try:
                    os.remove(old_file)
                    print(f"[缓存清理] 已删除: {old_file}")
                except OSError:
                    pass


# ── 开机自启 ──────────────────────────────────────────

AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "WallpaperTool"


def _set_autostart(enabled: bool) -> None:
    """通过注册表设置开机自启"""
    import winreg

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            AUTOSTART_KEY,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
        )
    except OSError:
        return

    try:
        if enabled:
            # 获取当前 exe 路径（打包后）或 python 脚本路径
            import sys
            exe_path = sys.executable
            if getattr(sys, "frozen", False):
                # PyInstaller 打包后
                target = f'"{sys.executable}"'
            else:
                # 开发模式，用 pythonw 启动
                main_script = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "main.py"
                )
                pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                target = f'"{pythonw}" "{main_script}"'
            winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, target)
        else:
            try:
                winreg.DeleteValue(key, AUTOSTART_NAME)
            except OSError:
                pass
    finally:
        winreg.CloseKey(key)
