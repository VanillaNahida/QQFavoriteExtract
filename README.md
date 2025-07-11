![QQFavoriteExtract](https://socialify.git.ci/NyaOH-Nahida/QQFavoriteExtract/image?description=1&font=Raleway&forks=1&issues=1&language=1&name=1&owner=1&pattern=Circuit+Board&pulls=1&stargazers=1&theme=Auto)

<img decoding="async" align=right src="https://upload-bbs.miyoushe.com/upload/2024/10/31/285532152/f2e2b1acf5c7696f37a80146e15aa3c7_1753693358022516581.gif" width="35%">

# QQNT表情包批量提取工具  

本仓库Gitee镜像：[点击前往Gitee仓库](https://gitee.com/NyaOH/QQFavoriteExtract)  

使用**Python**编写的QQ表情包批量提取工具  

可**批量**提取QQ账号收藏表情包  

13: 该仓库为**Windows**版，**Android**版请前往[这个仓库](https://github.com/VanillaNahida/QQFavoriteExtract-android)

# 程序界面
![](./img/ui.png)

# 特点  

 - 全自动操作，自动查找表情文件位置，复制文件并重命名  
 - 支持多账号分开提取对应的收藏表情包
 - 图形化界面，操作更友好

# 使用方法  

22: 1. 请前往[GitHub Release](https://github.com/VanillaNahida/QQFavoriteExtract/releases)下载exe文件
  > [!NOTE]
  > 如果你的网络环境较差，无法连接到 Github，可以使用 [GitHub Proxy](https://mirror.ghproxy.com/) 提供的文件代理加速下载服务
  > 或者您可以前往 [Gitee Release](https://gitee.com/NyaOH/QQFavoriteExtract/releases) 下载exe文件（推荐）

2. 下载好后，推荐先打开要提取表情包的QQ账号，随便打开一个聊天页面，刷新表情

  > [!WARNING]
  >
  > 请务必将你的收藏表情包界面**翻到底**，而不是**只打开页面！**必须让所有表情包图片**完全加载**出来再使用本程序，否则程序提取出来的表情包将会是**不完整**的。
  
  ![](./img/1.png)
  
   > [!NOTE]
   > 经过作者测试，QQ在删除收藏表情包后**并不会**将已缓存到本地的表情包一并删除，
   > 所以程序**可能**会提取到账号收藏夹里并不存在的表情包，这是正常的。
   > 后续可能会在程序里添加**一键清除表情包**的功能来避免提取到无关的表情包。

3. 双击运行程序，按照提示选择对应账号和保存位置即可

# 常见问题 ❓

### 1、提取的表情包数量和账号收藏数量不一致

请确保你已将所有收藏表情包加载出来，否则程序提取的表情包数量会偏少 。

后续可能会在程序里添加**一键清除表情包**的功能来避免提取到无关的表情包。

### 2、提示找不到用户配置文件
请安装[最新版NT架构QQ（非怀旧版）](https://im.qq.com/)再试！  
安装后打开并登录账号加载表情文件后即可使用本程序

### 3、配置文件解码失败
<details>
<summary>点击查看解决方法</summary>


请在文件资源管理器上方地址栏，输入如下路径
```
C:\Users\Public\Documents\Tencent\QQ
```
![](./img/2.png)

回车后找到`UserDataInfo.ini`文件  

右键点击**编辑**打开文件（Win11可能需要点击`显示更多选项`来查看）。  

![](./img/3.png)


然后点击左上角**文件**，选择**另存为**

![](./img/4.png)

编码选择**UTF-8**  或者**ANSI**，点击保存

![](./img/5.png)

覆盖原文件

![](./img/6.png)

再次运行本程序即可解决

</details>


# 反馈BUG
 - Issue （程序逻辑问题可在此反馈）
 - QQ群 （功能疑问可在此提问）
    - [195260107](https://qm.qq.com/q/KnVT7bcAgy)
    - [621457510](https://qm.qq.com/q/8fhlPfJ6Hm)
