<div align="center">
  
  ![:name](https://count.getloli.com/@QQFavoriteExtract?name=QQFavoriteExtract&theme=minecraft&padding=6&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)
  <img heigh="250" alt="image" src="https://github.com/user-attachments/assets/ce9a62e1-c5c6-4167-bae4-297863110b57" />
  
</div>

<div align="center">
  
  [![GitHub license](https://img.shields.io/github/license/VanillaNahida/QQFavoriteExtract?style=flat-square)](https://github.com/VanillaNahida/QQFavoriteExtract/blob/main/LICENSE)
  [![GitHub stars](https://img.shields.io/github/stars/VanillaNahida/QQFavoriteExtract?style=flat-square)](https://github.com/VanillaNahida/QQFavoriteExtract/stargazers)
  [![GitHub forks](https://img.shields.io/github/forks/VanillaNahida/QQFavoriteExtract?style=flat-square)](https://github.com/VanillaNahida/QQFavoriteExtract/network)
  [![GitHub issues](https://img.shields.io/github/issues/VanillaNahida/QQFavoriteExtract?style=flat-square)](https://github.com/VanillaNahida/QQFavoriteExtract/issues)
  [![Platform](https://img.shields.io/badge/Platform-Windows-brightgreen.svg?style=flat-square)]()
  [![Qt](https://img.shields.io/badge/Framwork-QFluentWidgets-blue)]()
  [![Author](https://img.shields.io/badge/%E4%BD%9C%E8%80%85-VanillaNahida-green)](https://github.com/VanillaNahida)  
  
</div>

<img decoding="async" align=right src="https://upload-bbs.miyoushe.com/upload/2024/10/31/285532152/f2e2b1acf5c7696f37a80146e15aa3c7_1753693358022516581.gif" width="35%">

# QQNT表情包批量提取工具 🛠️

一个使用 **Python** + **Qt6** + **QFluentWidgets** 设计并构建的现代化 QQ 表情包提取工具，可批量提取QQ账号收藏表情包。

本仓库Gitee镜像：[点击前往Gitee仓库](https://gitee.com/VanillaNahida/QQFavoriteExtract)  

该仓库为**Windows**版，**Android**版请前往[这个仓库](https://github.com/VanillaNahida/QQFavoriteExtract-android) （目前已停更）


# 程序界面

<br>
<details>
  <summary>长图较多，请点击展开查看</summary>
  <div align="center">
  <img width="640" alt="image" src="https://github.com/user-attachments/assets/9275c76f-1506-4f7c-b270-f97993180088" />  
  <p>程序主界面（浅色）</p> 
  
  <img width="640" alt="image" src="https://github.com/user-attachments/assets/803ef5b2-fe4b-4c36-aae6-608dfed14e42" />  
  <p>程序主界面（深色）</p> 

  <img width="640" alt="image" src="https://github.com/user-attachments/assets/e48edd75-3960-420e-8f6a-33744c396060" />
  <p>表情预览</p> 
  
  <img width="640" alt="image" src="https://github.com/user-attachments/assets/6a3126c3-7f04-43a5-8643-4c50066eaaa5" />
  <p>加载动画</p>
  </div>
</details>

# 特点 ✨ 

- ✅ 使用微软 Fluent Design 设计的现代化图形化界面，界面美观，全面支持并自适应了系统的深浅色模式。
- ✅ 全自动操作，自动查找表情文件位置，复制文件并重命名
- ✅ 支持多账号分开提取对应的收藏表情包
- ✅ 支持提取商店表情包和收藏夹收藏表情包
- ✅ 支持表情包预览功能

# 使用方法  

1. 请前往[GitHub Release](https://github.com/VanillaNahida/QQFavoriteExtract/releases)下载程序包  
   - `QQFavoriteExtract_<版本>_pyinstaller_onefile.exe`：单文件版，双击即可运行，无需解压（推荐）  
   - `QQFavoriteExtract_<版本>_pyinstaller_portable.zip`：多文件版，解压后运行文件夹内 exe  
  > [!NOTE]
  > 如果你的网络环境较差，无法连接到 Github，你可以使用 [GitHub Proxy](https://mirror.ghproxy.com/) 提供的文件代理加速下载服务  
  > 或者你可以[点击这里](https://pan.quark.cn/s/8424ef995c86)前往夸克网盘下载程序包。
  > 或前往 [Gitee Release](https://gitee.com/VanillaNahida/QQFavoriteExtract/releases) 下载exe文件（可能会更新不及时）  
  > 如果 Release 页面暂无程序包，说明 GitHub Actions 仍在构建中，请等待 5~15 分钟后刷新页面。  

2. 下载好后，推荐先打开要提取表情包的QQ账号，随便打开一个聊天页面，刷新表情（包括商店表情、已添加的表情）

  > [!WARNING]
  >
  > 请务必将你的收藏表情包界面**翻到底**，而不是**只打开页面！**必须让所有表情包图片**完全加载**出来再使用本程序，否则程序提取出来的表情包将会是**不完整**的。

  <div align="center">
    <img width="800" alt="image" src="https://github.com/user-attachments/assets/17c2155a-aaa9-41d3-98fb-90a56b109f2e" />
  </div>
  
  > [!NOTE]
  > 经过作者测试，QQ在删除收藏表情包后**并不会**将已缓存到本地的表情包一并删除，
  > 所以程序**可能**会提取到账号收藏夹里并不存在的表情包，这是正常的。
  > 后续可能会在程序里添加**一键清除表情包**的功能来避免提取到无关的表情包。

3. 双击运行程序，按照提示选择对应账号和保存位置即可

# 常见问题 ❓

### 1、提取的表情包数量和账号收藏数量不一致

请确保你已将所有收藏表情包加载出来，否则程序提取的表情包数量会偏少 。

后续可能会在程序里添加**一键清除表情包**的功能来避免提取到无关的表情包。

### 2、用户列表为空
请安装[最新版NT架构QQ（非怀旧版）](https://im.qq.com/)再试！  
安装后打开并登录账号加载表情文件后即可使用本程序

### 3、无法自动定位聊天文件夹
请尝试手动选择 `Tencent Files` 文件夹。

# 项目结构

```
QQFavoriteExtract/
├── .github/
│   ├── workflows/
│   │   └── build-windows-exe.yml   # GitHub Actions：构建四种格式 exe 并发布 Release
│   └── templates/
│       └── release-notes-tail.md.template  # Release 下载说明模板（构建后自动追加）
├── src/                          # 源码（Everything is a module）
│   ├── main.py                   # 程序入口（uv run python -m src.main）
│   ├── app/                      # 应用层：主窗口、信号总线、主题
│   │   ├── main_window.py        # 主窗口（FluentWindow）与四页导航注册
│   │   ├── signal_bus.py         # 全局信号总线（日志输出、保存路径同步等）
│   │   └── theme.py              # 主题应用辅助
│   ├── core/                     # 核心逻辑：扫描、导出、配置、更新检查
│   │   ├── emoji_scanner.py      # 表情包扫描（多账号 / 多分类 / 关键词筛选）
│   │   ├── exporter.py           # 批量导出与重命名
│   │   ├── workers.py            # QThread 工作线程（扫描 / 排序 / 导出）
│   │   ├── app_settings.py       # qconfig 配置项与首次运行默认值
│   │   ├── update_checker.py     # GitHub Release 版本检查
│   │   ├── user_service.py       # QQ 账号与数据目录识别
│   │   └── ...                   # marketface_handler / emoji_converter 等
│   ├── views/                    # 页面视图：工作台、日志、设置、关于
│   │   ├── workspace_view.py     # 工作台（数据路径、扫描、预览、导出、排序）
│   │   ├── log_view.py           # 日志页（分级输出、导出）
│   │   ├── setting_view.py       # 设置页（主题、保存路径、更新检查）
│   │   └── about_view.py         # 关于页（软件 / 作者信息、检查更新）
│   ├── widgets/                  # 可复用组件
│   │   ├── emoji_preview_widget.py   # 表情预览网格（懒加载、排序、右键菜单）
│   │   ├── emoji_detail_widget.py    # 表情详情面板（预览、信息、导出）
│   │   ├── image_viewer.py           # 大图预览窗口（无边框、可缩放）
│   │   ├── round_avatar.py           # 圆形头像（异步加载 + 本地缓存）
│   │   └── ...                       # 状态提示 / GIF 播放 / 新手教程等
│   ├── utils/                    # 工具函数
│   │   ├── helpers.py            # get_asset_path / get_font_path、路径显示转换
│   │   └── pillow_gif_player.py  # GIF 解码播放（Pillow，避免 QMovie 崩溃）
│   ├── assets/                   # 静态资源（占位图等，打包时内嵌 exe）
│   └── fonts/                    # 内置字体（MiSans Medium / SemiBold，打包时内嵌）
├── build.py                      # Nuitka 构建脚本（版本号取自 git tag）
├── pyproject.toml                # 依赖清单（uv 管理）
└── uv.lock                       # 依赖锁定文件
```

# 开发指南

### 环境准备

- Windows 10/11，Python 3.9+（推荐 3.12）
- 安装 [uv](https://docs.astral.sh/uv/)（依赖管理与虚拟环境）

### 安装依赖

```bash
uv sync
```

### 运行

```bash
uv run python -m src.main
```

### 打包

- **GitHub Actions（推荐）**：推送 `vX.Y.Z` 格式的 tag 后自动构建 Nuitka / PyInstaller 四种产物并上传 Release，同时自动在 Release Note 末尾追加下载说明。

- **本地 PyInstaller**：

  ```bash
  uv sync --group dev
  uv run --group dev pyinstaller src/main.py --noconsole --name QQFavoriteExtract --add-data "src/assets;src/assets" --add-data "src/fonts;src/fonts"
  ```
  或者直接使用构建脚本`build.py`

  ```bash
  uv run python build.py --pyinstaller
  ```

- **本地 Nuitka**：

  ```bash
  uv sync --extra build
  uv run python build.py
  ```

  或者直接使用构建脚本`build.py`

  ```bash
  uv run python build.py --nuitka
  ```
- **自动构建脚本`build.py`用法**：

  ```bash
  usage: build.py [-h] [--build-version BUILD_VERSION] [--nuitka | --pyinstaller] [--single | --multi | --both]

  QQFavoriteExtract 构建脚本

  options:
    -h, --help            show this help message and exit
    --build-version BUILD_VERSION
                          指定构建版本号（优先级最高）
    --nuitka              使用 Nuitka 打包（默认）
    --pyinstaller         使用 PyInstaller 打包
    --single              仅打包单文件版
    --multi               仅打包多文件版
    --both                同时打包单文件与多文件版（默认）
  ```

### 开发约定

- **模块划分**：按 `app / core / views / widgets / utils` 组织，一切皆模块。
- **耗时任务**：扫描、排序、导出、图片解码必须放入 `QThread`（见 `core/workers.py`），并携带 generation token 与取消标记，防止竞态与僵尸线程。
- **图片线程安全**：工作线程中使用 `QImage` 解码，`QPixmap` 只能在 UI 线程创建。
- **主题适配**：主题切换使用 `lazy=True` 只重绘可见控件；UI 文本使用主题感知组件（如 `BodyLabel`），不要直接写死颜色。
- **资源路径**：访问 `src/assets`、`src/fonts` 必须使用 `get_asset_path()` / `get_font_path()`，保证开发与 Nuitka onefile 打包环境一致。
- **日志**：通过 `signalBus.logMessage.emit(level, message)` 输出，格式为 `[YYYY-MM-DD HH:MM:SS] LEVEL    Message`，错误信息需附带完整堆栈。
- **UI 路径显示**：展示给用户的路径统一用反斜杠 `\`（`to_display_path`），内部处理保持 `os.path` 原样。

# 反馈BUG 🐛
 - Issue （程序逻辑问题可在此反馈）
 - QQ群 （功能疑问、Bug反馈可加入后艾特群主提问）
    - [1074471035](https://qm.qq.com/q/eGYIxyLRtu)
    - [195260107](https://qm.qq.com/q/KnVT7bcAgy)
    - [621457510](https://qm.qq.com/q/8fhlPfJ6Hm)

**Star History**

## Star History

<a href="https://www.star-history.com/?repos=VanillaNahida%2FQQFavoriteExtract&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=VanillaNahida/QQFavoriteExtract&type=date&theme=dark&legend=top-left&sealed_token=Xjl1OOs-ErpLnBFtIgh6yxAlgFo1LHk5yL5XgoAjtiLalD-lh8p7ncSf4CLDW9P14YflKkBLvFOG_ximf1B_0wckKU5DM7KcICEzgl03241uWOrgaQXpXw" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=VanillaNahida/QQFavoriteExtract&type=date&legend=top-left&sealed_token=Xjl1OOs-ErpLnBFtIgh6yxAlgFo1LHk5yL5XgoAjtiLalD-lh8p7ncSf4CLDW9P14YflKkBLvFOG_ximf1B_0wckKU5DM7KcICEzgl03241uWOrgaQXpXw" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=VanillaNahida/QQFavoriteExtract&type=date&legend=top-left&sealed_token=Xjl1OOs-ErpLnBFtIgh6yxAlgFo1LHk5yL5XgoAjtiLalD-lh8p7ncSf4CLDW9P14YflKkBLvFOG_ximf1B_0wckKU5DM7KcICEzgl03241uWOrgaQXpXw" />
 </picture>
</a>
