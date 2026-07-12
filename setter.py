"""
Windows 壁纸设置模块
通过 ctypes 调用 Win32 API 设置桌面壁纸
"""
import ctypes
import os
import winreg


# Win32 常量
SPI_SETDESKWALLPAPER = 0x0014
SPIF_UPDATEINIFILE = 0x0001
SPIF_SENDCHANGE = 0x0002

# 壁纸样式注册表路径
REG_KEY_WALLPAPER_STYLE = r"Control Panel\Desktop"
REG_VAL_WALLPAPER_STYLE = "WallpaperStyle"
REG_VAL_TILE = "TileWallpaper"

# 样式映射
FIT_MODES = {
    "fill": ("10", "0"),     # 填充 (拉伸裁剪以填充整个屏幕)
    "fit": ("6", "0"),       # 适应 (保持比例，留黑边)
    "stretch": ("2", "0"),   # 拉伸 (拉伸以填满屏幕，不保持比例)
    "tile": ("0", "1"),      # 平铺
    "center": ("0", "0"),    # 居中
}


def set_wallpaper(image_path: str, fit_mode: str = "fill") -> bool:
    """
    将指定图片设为 Windows 桌面壁纸

    Args:
        image_path: 图片文件的绝对路径
        fit_mode: 壁纸样式，可选 fill / fit / stretch / tile / center

    Returns:
        是否设置成功
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    abs_path = os.path.abspath(image_path)

    # 设置壁纸样式
    _set_wallpaper_style(fit_mode)

    # 调用 Win32 API 设置壁纸
    result = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER,
        0,
        abs_path,
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
    )

    return result != 0


def _set_wallpaper_style(fit_mode: str) -> None:
    """通过注册表设置壁纸样式"""
    style, tile = FIT_MODES.get(fit_mode, FIT_MODES["fill"])

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_KEY_WALLPAPER_STYLE,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, REG_VAL_WALLPAPER_STYLE, 0, winreg.REG_SZ, style)
        winreg.SetValueEx(key, REG_VAL_TILE, 0, winreg.REG_SZ, tile)
        winreg.CloseKey(key)
    except OSError as e:
        raise RuntimeError(f"无法修改壁纸样式注册表: {e}")


def get_screen_resolution() -> tuple[int, int]:
    """获取主显示器分辨率"""
    user32 = ctypes.windll.user32
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)
    return width, height
