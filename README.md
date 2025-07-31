# Clash Config Generator

A GUI tool for generating custom Clash configuration files from subscription links and a local template.

## Features

- **Template-Based**: Builds the final configuration based on a `template.yaml` file, preserving its original structure and most settings.
- **Multiple Subscriptions**: Supports adding multiple speed-test groups, each with its own set of subscription links.
- **Manual Nodes**: Supports adding manually selected nodes.
- **Live Preview**: Modifying subscription links or settings in the UI provides a real-time preview of the final YAML file.
- **Two Export Modes**:
    1.  **Single File**: Merges all nodes and configurations into a single `config.yaml` file.
    2.  **Individual Files**: Generates a separate configuration file for each node, useful for other applications.
- **Cross-Platform**: Built with Python and CustomTkinter, making it theoretically cross-platform.

## How to Use

### For End-Users

1.  Download the `gui_app_v2.exe` file from the `dist` folder (if available).
2.  Ensure `gui_app_v2.exe` and `template.yaml` are in the same directory.
3.  Double-click `gui_app_v2.exe` to run it.
4.  The application will automatically load `template.yaml` on startup. If not found, it will prompt you to select it manually.
5.  Enter your Clash subscription links in the "Speed-Test Groups" section.
6.  Enter links for nodes you want to select manually in the "Manual Selection Group" section.
7.  The right panel will show a live preview of the generated configuration.
8.  Choose between "Single File" or "Individual Files" mode, then click the "Export" button to save your configuration file(s).

### For Developers

#### Prerequisites

You need Python 3 and the following dependencies:

```bash
pip install customtkinter
pip install ruamel.yaml
```

#### Running the Application

Execute the main script directly:

```bash
python gui_app_v2.py
```

#### Building from Source

This project uses `PyInstaller` to create an executable.

1.  Install `PyInstaller`:
    ```bash
    pip install pyinstaller
    ```

2.  Run the build command:
    ```bash
    pyinstaller --noconfirm --onefile --windowed --add-data "template.yaml;." --add-data "convert_subscription.py;." --add-data "converters.py;."  "gui_app_v2.py"
    ```
    The bundled executable will be located in the `dist` directory.