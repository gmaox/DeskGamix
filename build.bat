@echo off
chcp 65001 >nul
echo 正在使用 PyInstaller 打包 ...
C:\Users\gcpdbat\AppData\Local\Programs\Python\Python38\python.exe -m PyInstaller --add-data "fav.ico;." --add-data "SDL2.dll;." --add-data "1.png;." --add-data "pssuspend64.exe;." -w Simplenite.py -i "fav.ico" --uac-admin --noconfirm
if %ERRORLEVEL% equ 0 (
    echo.
    echo 打包完成。输出目录: dist\QuickStreamAppAdd.exe
) else (
    echo 打包失败，请检查是否已安装: pip install pyinstaller
    pause
)
