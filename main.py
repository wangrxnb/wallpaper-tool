"""
壁纸小工具 — 入口文件
启动系统托盘，自动切换壁纸（默认 24 小时）
"""
import os
import signal
import sys
import traceback


def main():
    # 确保工作目录在项目根目录，方便找到 config.json
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    from core import WallpaperCore
    from tray_icon import WallpaperTray

    # 初始化核心
    config_path = os.path.join(project_dir, "config.json")
    core = WallpaperCore(config_path=config_path)

    # 首次启动时立即切换一张壁纸（如果还没有壁纸）
    if core.current_wallpaper is None:
        print("首次启动，获取第一张壁纸...")
        try:
            path = core.switch_wallpaper()
            print(f"壁纸已设置: {path}")
        except Exception as e:
            print(f"首次获取壁纸失败: {e}")
            traceback.print_exc()

    # 启动定时自动切换
    interval = core.interval_minutes
    if interval > 0:
        core.start_auto_switch()
        print(f"自动切换已启动，间隔: {interval} 分钟")

    # 启动托盘（阻塞主线程直到退出）
    tray = WallpaperTray(core)

    # 注册 Ctrl+C 信号处理
    def _shutdown(signum, frame):
        print("\n收到退出信号，正在关闭...")
        core.stop_auto_switch()
        tray.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGBREAK, _shutdown)

    print("壁纸小工具已启动，右键托盘图标操作，按 Ctrl+C 退出")
    try:
        tray.run()
    except KeyboardInterrupt:
        pass
    finally:
        core.stop_auto_switch()
        print("壁纸小工具已退出")


if __name__ == "__main__":
    main()
