@echo off
REM �л����ű����ڵ�Ŀ¼
cd /d "%~dp0"

REM ���� Python �����������Ը�����Ҫ�޸�Ϊ���� python.exe ·��
set PYTHON_EXE=python

REM ��� customtkinter �Ƿ�װ
%PYTHON_EXE% -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] customtkinter δ��װ�����ڳ��԰�װ...
    %PYTHON_EXE% -m pip install customtkinter
)

REM ��� ruamel.yaml �Ƿ�װ
%PYTHON_EXE% -c "import ruamel.yaml" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] ruamel.yaml δ��װ�����ڳ��԰�װ...
    %PYTHON_EXE% -m pip install ruamel.yaml
)

echo [INFO] ���������ɣ���������Ӧ��...
%PYTHON_EXE% gui_app_v2.py

pause