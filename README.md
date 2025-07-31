# Clash 配置生成器

这是一个图形化界面的 Clash 配置文件生成工具，旨在简化通过订阅链接和本地模版创建自定义 Clash 配置的过程。

## 功能

- **模版化配置**: 基于一个 `模版.yaml` 文件来构建最终配置，保留原始模版的结构和大部分设置。
- **多订阅支持**: 支持添加多个测速组，每个组可以有独立的订阅链接。
- **手动节点**: 支持添加手动选择的节点。
- **动态生成**: 在界面中修改订阅链接或配置即可实时预览最终的 YAML 文件。
- **两种导出模式**:
    1.  **单一文件**: 将所有节点和配置合并成一个单独的 `config.yaml` 文件。
    2.  **独立文件**: 为每个节点生成一个独立的配置文件，方便在其他地方使用。
- **跨平台**: 使用 Python 和 CustomTkinter 构建，理论上可以跨平台运行。

## 如何使用

### 对于普通用户

1.  下载 `dist` 文件夹中的 `gui_app_v2.exe` 文件。
2.  确保 `gui_app_v2.exe` 和 `模版.yaml` 文件在同一个目录下。
3.  双击运行 `gui_app_v2.exe`。
4.  程序启动时会自动加载 `模版.yaml`。如果未找到，会提示手动选择。
5.  在 "测速组" 中输入您的 Clash 订阅链接。
6.  在 "手动选择组订阅" 中输入您想要手动选择的节点链接。
7.  右侧会实时预览生成的配置文件。
8.  根据需要选择 "单一文件" 或 "独立文件" 模式，然后点击 "导出" 按钮保存配置文件。

### 对于开发者

#### 环境准备

需要安装 Python 3 和以下依赖:

```bash
pip install customtkinter
pip install ruamel.yaml
```

#### 运行

直接运行主程序脚本:

```bash
python gui_app_v2.py
```

#### 打包

本项目使用 `PyInstaller` 进行打包。

1.  安装 `PyInstaller`:
    ```bash
    pip install pyinstaller
    ```

2.  执行打包命令:
    ```bash
    pyinstaller --noconfirm --onefile --windowed --add-data "模版.yaml;." --add-data "convert_subscription.py;." --add-data "converters.py;."  "gui_app_v2.py"
    ```
    打包后的 `exe` 文件会生成在 `dist` 目录下。