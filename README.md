# 🖼️ Wallpaper Tool

极简 Windows 桌面壁纸小工具 — 系统托盘常驻，定时 / 手动一键切换精美壁纸。

## ✨ 功能

- **🖱 一键切换** — 左键单击托盘图标或右键菜单「下一张」立即更换壁纸
- **⏱ 定时自动切换** — 支持 30 分钟 / 1 小时 / 6 小时 / 12 小时 / 24 小时多档间隔
- **⭐ 收藏壁纸** — 喜欢的壁纸一键保存到收藏夹，不会被自动清理
- **📦 本地缓存** — 自动缓存最近壁纸，可随时打开文件夹回顾
- **🚀 开机自启** — 托盘菜单一键开关，写入注册表随系统启动
- **🔔 系统通知** — 壁纸切换成功后弹出 Windows Toast 通知（可关闭）

## 🛠 技术栈

| 层 | 技术 |
|---|---|
| 语言 | Python 3 |
| 托盘 GUI | `pystray` |
| 图片处理 | `Pillow` |
| HTTP 请求 | `requests` + `cloudscraper`（Cloudflare 绕过） |
| 壁纸设置 | Win32 API (`SystemParametersInfoW`) |
| 定时调度 | `threading.Timer` |
| 打包 | `pyinstaller`（可选） |

## 📦 安装

```powershell
# 1. 克隆项目
git clone https://github.com/wangrxnb/wallpaper-tool.git
cd wallpaper-tool

# 2. 创建虚拟环境（可选）
conda create -n wallpaperenv python=3.12
conda activate wallpaperenv

# 3. 安装依赖
pip install -r requirements.txt
```

## 🚀 使用

```powershell
# 命令行前台运行（可看到日志）
python main.py

# 无窗口后台运行
pythonw main.py
```

启动后任务栏右下角出现山景图标，右键弹出菜单：

```
📷  下一张壁纸          ← 立即切换（左键单击同效）
─────────────────
⏱  自动切换: 24 小时   ← 展开选间隔 / 关闭
⭐  收藏当前壁纸
─────────────────
🖼  打开壁纸文件夹
─────────────────
☐  开机自启
─────────────────
❌  退出
```

## ⚙️ 配置

编辑项目根目录下的 `config.json`：

```json
{
    "api_url": "https://www.luvbree.com/api/image/random",
    "api_params": {
        "categoryId": "1927377837329715201",
        "isNsfw": "true",
        "isLandscape": "true",
        "type": "3",
        "imageType": "compressed"
    },
    "interval_minutes": 1440,
    "cache_dir": "",
    "max_cache_count": 100,
    "auto_start": false,
    "enable_notification": true,
    "fit_mode": "fill"
}
```

| 字段 | 说明 | 默认值 |
|---|---|---|
| `api_url` | 图片 API 地址 | — |
| `api_params` | API 查询参数 | — |
| `interval_minutes` | 自动切换间隔（分钟），0 表示关闭 | `1440`（24 小时） |
| `cache_dir` | 壁纸缓存目录，留空为 `~/Pictures/Wallpapers` | `""` |
| `max_cache_count` | 最多缓存张数，超出自动清理旧文件 | `100` |
| `auto_start` | 是否开机自启 | `false` |
| `enable_notification` | 切换后是否弹出通知 | `true` |
| `fit_mode` | 壁纸填充方式：`fill` / `fit` / `stretch` / `tile` / `center` | `"fill"` |

## 📦 打包为 EXE

```powershell
pip install pyinstaller
pyinstaller --onefile --noconsole --name WallpaperTool main.py
```

生成的文件在 `dist\WallpaperTool.exe`，可直接运行或放入开机启动项。

## 📂 项目结构

```
wallpaper-tool/
├── main.py              # 入口：启动时设置壁纸 + 启动托盘
├── fetcher.py           # 图片获取：API 调用 + 自动识别返回格式
├── setter.py            # 壁纸设置：Win32 API + 注册表样式
├── scheduler.py         # 定时器：可重置间隔调度
├── core.py              # 核心调度：统一协调各组件
├── tray_icon.py         # 系统托盘：图标 + 右键菜单
├── config.json          # 用户配置文件
├── requirements.txt     # Python 依赖
└── .gitignore
```

## 📝 License

MIT
