<div align="center">
  
  ![:name](https://count.getloli.com/@QQFavoriteExtract?name=QQFavoriteExtract&theme=minecraft&padding=6&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

</div>

<div align="center">
  
  [![GitHub license](https://img.shields.io/github/license/VanillaNahida/QQFavoriteExtract?style=flat-square)](https://github.com/VanillaNahida/QQFavoriteExtract/blob/main/LICENSE)
  [![GitHub stars](https://img.shields.io/github/stars/VanillaNahida/QQFavoriteExtract?style=flat-square)](https://github.com/VanillaNahida/QQFavoriteExtract/stargazers)
  [![GitHub forks](https://img.shields.io/github/forks/VanillaNahida/QQFavoriteExtract?style=flat-square)](https://github.com/VanillaNahida/QQFavoriteExtract/network)
  [![GitHub issues](https://img.shields.io/github/issues/VanillaNahida/QQFavoriteExtract?style=flat-square)](https://github.com/VanillaNahida/QQFavoriteExtract/issues)
  [![Platform](https://img.shields.io/badge/Platform-Windows-brightgreen.svg?style=flat-square)]()
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
  <p>程序主界面（浅色）</p> 

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
