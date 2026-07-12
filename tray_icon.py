"""
系统托盘模块
pystray 托盘图标 + 右键菜单
"""
import os
import subprocess
import threading
import webbrowser
from io import BytesIO
from typing import Optional

from PIL import Image, ImageDraw


def _create_icon_image(size: int = 64) -> Image.Image:
    """生成托盘图标（简单的渐变色块图标）"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 画一个简单的山景图标
    # 天空渐变（用纯色简化）
    sky_color = (70, 130, 200)
    draw.rectangle([0, 0, size, size], fill=sky_color)

    # 太阳
    sun_r = size // 10
    sun_x = size * 3 // 4
    sun_y = size // 5
    draw.ellipse(
        [sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r],
        fill=(255, 220, 100),
    )

    # 远山
    mountain_color = (60, 100, 60)
    draw.polygon([
        (0, size),
        (size // 3, size // 3),
        (size * 2 // 3, size // 2),
        (size, size // 4),
        (size, size),
    ], fill=mountain_color)

    # 近山
    near_mountain = (40, 75, 40)
    draw.polygon([
        (0, size),
        (size // 4, size // 2),
        (size // 2, size * 3 // 5),
        (size * 3 // 4, size // 3),
        (size, size // 2),
        (size, size),
    ], fill=near_mountain)

    return img


def _make_interval_label(minutes: int) -> str:
    """将分钟数转为可读标签"""
    if minutes <= 0:
        return "关闭自动切换"
    if minutes < 60:
        return f"{minutes} 分钟"
    hours = minutes // 60
    if minutes % 60 == 0:
        return f"{hours} 小时"
    return f"{hours} 小时 {minutes % 60} 分钟"


INTERVAL_OPTIONS = [
    (0, "关闭"),
    (30, "30 分钟"),
    (60, "1 小时"),
    (360, "6 小时"),
    (720, "12 小时"),
    (1440, "24 小时"),
]


class WallpaperTray:
    """壁纸工具系统托盘"""

    def __init__(self, core):
        self._core = core
        self._icon_image = _create_icon_image()
        self._tray: Optional["pystray.Icon"] = None
        self._menu_lock = threading.Lock()

    def run(self) -> None:
        """启动托盘（阻塞直到退出）"""
        import pystray

        self._tray = pystray.Icon(
            "WallpaperTool",
            self._icon_image,
            menu=self._build_menu(),
        )
        self._tray.title = "壁纸小工具"
        self._tray.run()

    def stop(self) -> None:
        """停止托盘"""
        if self._tray is not None:
            self._tray.stop()

    def notify(self, title: str, message: str) -> None:
        """弹出系统通知"""
        if self._tray is not None and self._core.config.get("enable_notification", True):
            try:
                self._tray.notify(title=title, message=message)
            except Exception:
                pass

    # ── 菜单构建 ──────────────────────────────────────

    def _build_menu(self):
        """构建右键菜单"""
        import pystray

        return pystray.Menu(
            # ── 下一张 ──
            pystray.MenuItem(
                "📷  下一张壁纸",
                self._on_next_wallpaper,
                default=True,  # 左键单击默认触发
            ),

            pystray.Menu.SEPARATOR,

            # ── 自动切换子菜单 ──
            pystray.MenuItem(
                self._get_auto_switch_label(),
                pystray.Menu(*self._build_interval_submenu()),
            ),

            # ── 收藏 ──
            pystray.MenuItem(
                "⭐  收藏当前壁纸",
                self._on_favorite,
            ),

            pystray.Menu.SEPARATOR,

            # ── 打开文件夹 ──
            pystray.MenuItem(
                "🖼  打开壁纸文件夹",
                self._on_open_cache_dir,
            ),

            pystray.Menu.SEPARATOR,

            # ── 开机自启 ──
            pystray.MenuItem(
                self._get_autostart_label(),
                self._on_toggle_autostart,
            ),

            # ── 退出 ──
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "❌  退出",
                self._on_exit,
            ),
        )

    def _build_interval_submenu(self):
        """构建间隔选择子菜单"""
        import pystray

        current = self._core.interval_minutes

        items = []
        for minutes, label in INTERVAL_OPTIONS:
            prefix = "●" if minutes == current else "○"
            items.append(pystray.MenuItem(
                f"{prefix}  {label}",
                self._make_interval_callback(minutes),
            ))
        return items

    def _make_interval_callback(self, minutes: int):
        """生成间隔选择的回调（闭包捕获 minutes）"""
        def callback(icon, item):
            if minutes <= 0:
                self._core.stop_auto_switch()
            else:
                self._core.interval_minutes = minutes
                if not self._core.is_auto_running:
                    self._core.start_auto_switch()
                else:
                    self._core.reset_timer()
            self.notify("壁纸小工具", f"自动切换: {_make_interval_label(minutes)}")
            self._refresh_menu(icon)
        return callback

    # ── 菜单回调 ──────────────────────────────────────

    def _on_next_wallpaper(self, icon, item):
        """点击「下一张」"""
        threading.Thread(target=self._do_switch, args=(icon,), daemon=True).start()

    def _do_switch(self, icon) -> None:
        """在后台线程执行切换"""
        try:
            path = self._core.switch_wallpaper()
            self._core.reset_timer()  # 手动切换后重新计时
            basename = os.path.basename(path)
            self.notify("壁纸已更新", basename)
        except Exception as e:
            self.notify("切换失败", str(e)[:200])
            print(f"[错误] {e}")

    def _on_favorite(self, icon, item):
        """收藏当前壁纸"""
        dest = self._core.favorite_current()
        if dest:
            self.notify("已收藏", f"保存至: {os.path.basename(dest)}")
        else:
            self.notify("收藏失败", "当前没有壁纸可收藏")

    def _on_open_cache_dir(self, icon, item):
        """打开壁纸文件夹"""
        cache_dir = self._core.cache_dir
        if os.path.isdir(cache_dir):
            subprocess.Popen(["explorer", cache_dir])
        else:
            self.notify("错误", "壁纸文件夹不存在")

    def _on_toggle_autostart(self, icon, item):
        """切换开机自启"""
        new_state = not self._core.auto_start
        self._core.auto_start = new_state
        state_text = "已开启" if new_state else "已关闭"
        self.notify("开机自启", state_text)
        self._refresh_menu(icon)

    def _on_exit(self, icon, item):
        """退出程序"""
        self._core.stop_auto_switch()
        icon.stop()

    # ── 辅助 ──────────────────────────────────────────

    def _get_auto_switch_label(self) -> str:
        """获取自动切换菜单项的标签"""
        if self._core.is_auto_running:
            return f"⏱  自动切换: {_make_interval_label(self._core.interval_minutes)}"
        return "⏱  自动切换: 已关闭"

    def _get_autostart_label(self) -> str:
        """获取开机自启菜单项标签"""
        state = "☑ 开机自启" if self._core.auto_start else "☐ 开机自启"
        return state

    def _refresh_menu(self, icon) -> None:
        """刷新托盘菜单（更新选中状态）"""
        icon.menu = self._build_menu()
