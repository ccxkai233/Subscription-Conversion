@echo off
REM 切换到脚本所在的目录
cd /d "%~dp0"

REM 设置 Python 解释器，可以根据需要修改为您的 python.exe 路径
set PYTHON_EXE=python

REM 检查 customtkinter 是否安装
%PYTHON_EXE% -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] customtkinter 未安装，正在尝试安装...
    %PYTHON_EXE% -m pip install customtkinter
)

REM 检查 ruamel.yaml 是否安装
%PYTHON_EXE% -c "import ruamel.yaml" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] ruamel.yaml 未安装，正在尝试安装...
    %PYTHON_EXE% -m pip install ruamel.yaml
)

echo [INFO] 依赖检查完成，正在启动应用...
%PYTHON_EXE% gui_app_v2.py

pause