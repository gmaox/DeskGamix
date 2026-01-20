import glob
import shutil
import sys
import json
import threading
import winreg
from PyQt5 import QtWidgets
from PyQt5 import QtGui
import pygame, math
from PIL import Image
import win32gui,win32process,psutil,win32api,win32ui
from PyQt5.QtWidgets import QApplication, QListWidgetItem, QMainWindow, QMessageBox, QScroller, QSystemTrayIcon, QMenu , QVBoxLayout, QDialog, QGridLayout, QWidget, QPushButton, QLabel, QDesktopWidget, QHBoxLayout, QFileDialog, QSlider, QLineEdit, QProgressBar, QScrollArea, QFrame
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont, QPixmap, QIcon, QColor, QLinearGradient
from PyQt5.QtCore import QDateTime, QSize, Qt, QThread, pyqtSignal, QTimer, QPoint, QProcess, QPropertyAnimation, QRect, QObject
import subprocess, time, os,win32con, ctypes, re, win32com.client, ctypes, time, pyautogui
from ctypes import wintypes
#& C:/Users/86150/AppData/Local/Programs/Python/Python38/python.exe -m PyInstaller --add-data "fav.ico;." --add-data '1.png;.' --add-data 'pssuspend64.exe;.' -w DesktopGame.py -i '.\fav.ico' --uac-admin --noconfirm
# 定义 Windows API 函数
SetWindowPos = ctypes.windll.user32.SetWindowPos
SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
FindWindow = ctypes.windll.user32.FindWindowW
# 定义常量
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
# 定义 SetWindowPos 函数的参数类型和返回类型
SetWindowPos.restype = wintypes.BOOL
SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
SetForegroundWindow.restype = wintypes.BOOL
SetForegroundWindow.argtypes = [wintypes.HWND]

pyautogui.FAILSAFE = False    # 禁用角落快速退出
pyautogui.PAUSE = 0           # 禁用自动暂停，确保动作即时响应
#确认你的sunshine安装目录
def get_app_install_path():
    app_name = "sunshine"
    try:
        # 打开注册表键，定位到安装路径信息
        registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                      r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        # 遍历注册表中的子项，查找对应应用名称
        for i in range(winreg.QueryInfoKey(registry_key)[0]):
            subkey_name = winreg.EnumKey(registry_key, i)
            subkey = winreg.OpenKey(registry_key, subkey_name)
            try:
                display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                if app_name.lower() in display_name.lower():
                    install_location, _ = winreg.QueryValueEx(subkey, "DisplayIcon")
                    if os.path.exists(install_location):
                        return os.path.dirname(install_location)
            except FileNotFoundError:
                continue
    except Exception as e:
        print(f"Error: {e}")
    print(f"未检测到安装目录！")
    return os.path.dirname(sys.executable)
APP_INSTALL_PATH=get_app_install_path()
if ctypes.windll.shell32.IsUserAnAdmin()==0:
    ADMIN = False
elif ctypes.windll.shell32.IsUserAnAdmin()==1:
    ADMIN = True
if getattr(sys, 'frozen', False):
    # 如果是打包后的可执行文件
    program_directory = os.path.dirname(sys.executable)
    getattrs = True
else:
    # 如果是脚本运行
    program_directory = os.path.dirname(os.path.abspath(__file__))
    getattrs = False
# 将工作目录更改为上一级目录
os.chdir(program_directory)
# 读取设置文件
settings_path = "set.json"
settings = {
    "favorites": [],
    "last_played": [],
    "more_favorites": [],
    "more_last_used": [],
    "extra_paths": [],
    "scale_factor": 1.0  # 添加缩放因数的默认值
}
try:
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
except Exception as e:
    print(f"Error loading settings: {e}")

def get_target_path(lnk_file):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(lnk_file)
    return shortcut.TargetPath

def load_apps():
    """加载有效的应用程序列表"""
    global valid_apps, games
    # 读取 JSON 数据
    json_path = f"{APP_INSTALL_PATH}\\config\\apps.json"
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        # 如果普通 utf-8 读取失败，尝试用带 BOM 的 utf-8-sig 读取并回写为纯 utf-8
        try:
            with open(json_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            except Exception as e2:
                print(f"保存为 utf-8 失败: {e2}")
        except Exception as e2:
            print(f"读取 apps.json 失败: {e} / {e2}")
            # 使用 Win32 API弹窗提示
            try:
                msg = f"读取 apps.json 失败：\n{e}\n{e2}\n。"
                ctypes.windll.user32.MessageBoxW(0, msg, "读取错误", 0x10)  # 0x10 = MB_ICONERROR
            except Exception:
                pass
            data = {"apps": []}

    ###下面俩行代码用于QuickStreamAppAdd的伪排序清除，若感到困惑可删除###
    for idx, entry in enumerate(data.get("apps", [])):
        entry["name"] = re.sub(r'^\d{2} ', '', entry.get("name", ""))
    # 仅保留 name 不是 Desktop/Steam Big Picture 且 image-path 存在且非空的条目
    games = [
        app for app in data.get("apps", [])
        if app.get("name") not in ("Desktop", "Steam Big Picture")
        and str(app.get("image-path", "")).strip() != ""
    ]
    print(f"+++++检测到 {len(games)} 个游戏")

    # 存储解析后的有效软件条目
    valid_apps = []
    for app in data.get("apps", []):
        cmda = app.get("cmd")
        if cmda is None:
            continue  # 跳过无 cmd 的条目
        cmd = cmda.strip('"')
        # 新增2：如果app["name"]已存在于settings["custom_valid_apps"]的"name"，则跳过
        if "custom_valid_apps" in settings and any(app["name"] == item["name"] for item in settings["custom_valid_apps"]):
            continue
        if cmd:
            # 如果cmd是快捷方式路径（.lnk）
            if cmd.lower().endswith('.lnk'):
                try:
                    target_path = get_target_path(cmd)
                    valid_apps.append({"name": app["name"], "path": target_path})#os.path.splitext(file_name)[0]；file_name = os.path.basename(full_path)
                except Exception as e:
                    print(f"无法解析快捷方式 {cmd}：{e}")
            # 如果cmd是.exe文件路径
            elif cmd.lower().endswith('.exe'):
                valid_apps.append({"name": app["name"], "path": cmd})
        if "last_played" in settings:
            if app["name"] not in settings["last_played"]:
                settings["last_played"].insert(0, app["name"])
        else:
            settings["last_played"] = [app["name"]]
    # 加载自定义 valid_apps
    if "custom_valid_apps" in settings:
        for item in settings["custom_valid_apps"]:
            if "name" in item and "path" in item:
                valid_apps.append({"name": item["name"], "path": item["path"]})
    #print(f"已加载 {valid_apps} 个有效应用程序")
load_apps()

more_apps = []
def load_morefloder_shortcuts():
    """解析 ./morefloder 文件夹下的快捷方式并添加到 more_apps"""
    more_apps.clear()  # 清空 more_apps 列表
    morefloder_path = os.path.join(program_directory, "morefloder")
    if not os.path.exists(morefloder_path):
        print(f"目录 {morefloder_path} 不存在")
        return

    # 遍历文件夹下的所有 .lnk 文件
    shortcut_files = glob.glob(os.path.join(morefloder_path, "*.lnk"))
    for shortcut_file in shortcut_files:
        try:
            target_path = get_target_path(shortcut_file)
            app_name = os.path.splitext(os.path.basename(shortcut_file))[0]
            more_apps.append({"name": app_name, "path": target_path})
        except Exception as e:
            print(f"无法解析快捷方式 {shortcut_file}：{e}")
load_morefloder_shortcuts()
#print(more_apps)
#print(valid_apps)

def get_desktop_listview():
    # 先找WorkerW窗口
    def callback(hwnd, result):
        if win32gui.GetClassName(hwnd) == "WorkerW":
            defview = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
            if defview:
                result.append(defview)
    result = []
    win32gui.EnumWindows(callback, result)
    if result:
        return win32gui.FindWindowEx(result[0], 0, "SysListView32", None)
    # 兼容老方式
    progman = win32gui.FindWindow("Progman", None)
    defview = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
    if defview:
        return win32gui.FindWindowEx(defview, 0, "SysListView32", None)
    return None

def hide_desktop_icons():
    listview = get_desktop_listview()
    if listview:
        win32gui.ShowWindow(listview, win32con.SW_HIDE)

def show_desktop_icons():
    listview = get_desktop_listview()
    if listview:
        win32gui.ShowWindow(listview, win32con.SW_SHOW)
def toggle_taskbar():
    # 获取任务栏窗口句柄
    taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
    # 获取当前任务栏状态
    is_visible = win32gui.IsWindowVisible(taskbar)
    # 切换显示状态
    ctypes.windll.user32.ShowWindow(taskbar, 0 if is_visible else 5)  # 0=隐藏, 5=显示

def hide_taskbar():
    taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
    ctypes.windll.user32.ShowWindow(taskbar, 0)  # 隐藏

def show_taskbar():
    taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
    ctypes.windll.user32.ShowWindow(taskbar, 5)  # 显示

# 获取系统的屏幕边界
def get_screen_rect():
    user32 = ctypes.windll.user32
    return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))

# 获取当前的工作区域（最大化时的边界）
def get_work_area():
    # 获取整个屏幕区域
    user32 = ctypes.windll.user32
    screen_rect = (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
    # 获取任务栏窗口句柄
    taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
    if not taskbar:
        return screen_rect
    # 获取任务栏位置和大小
    rect = win32gui.GetWindowRect(taskbar)
    # 判断任务栏在屏幕的哪一边
    left, top, right, bottom = rect
    sw, sh = screen_rect[2], screen_rect[3]
    # 默认工作区为全屏
    work_left, work_top, work_right, work_bottom = 0, 0, sw, sh
    # 判断任务栏位置
    if left <= 0 and right >= sw:  # 顶部或底部
        if top == 0:
            work_top = bottom  # 任务栏在顶部
        else:
            work_bottom = top  # 任务栏在底部
    elif top <= 0 and bottom >= sh:  # 左侧或右侧
        if left == 0:
            work_left = right  # 任务栏在左侧
        else:
            work_right = left  # 任务栏在右侧
    return (work_left, work_top, work_right, work_bottom)

# 设置工作区域
def set_work_area(left, top, right, bottom):
    SPI_SETWORKAREA = 0x002F
    rect = ctypes.wintypes.RECT(left, top, right, bottom)
    res = ctypes.windll.user32.SystemParametersInfoW(SPI_SETWORKAREA, 0, ctypes.byref(rect), 1)
    return res != 0

class TaskbarWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowStaysOnBottomHint |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.7)
        self.setStyleSheet("""
            QDialog {
                background-color: #2E2E2E;
                border: 1px solid #222;
            }
            QLabel {
                color: #CCCCCC;
                font-size: 22px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #aaa, stop:1 #888);
                border: 1px solid #222;
                font-size: 26px;
                min-width: 120px;
                min-height: 60px;
            }
            QPushButton:hover {
                background: #bbb;
            }
            QSlider::groove:horizontal {
                height: 10px;
                border: 1px solid #666;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #999, stop:1 #666
                );
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #000;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
        """)
        def get_desktop_parent():
            progman = win32gui.FindWindow("Progman", None)
            defview = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
            if defview:
                return defview
            # 查找WorkerW
            result = []
            def callback(hwnd, result):
                if win32gui.GetClassName(hwnd) == "WorkerW":
                    child = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
                    if child:
                        result.append(child)
            win32gui.EnumWindows(callback, result)
            if result:
                return result[0]
            return win32gui.GetDesktopWindow()
        desktop_parent = get_desktop_parent()
        self.winId()  # 确保窗口已创建
        ctypes.windll.user32.SetParent(int(self.winId()), desktop_parent)
        # taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
        # rect = win32gui.GetWindowRect(taskbar)
        # taskbar_height = rect[3] - rect[1]
        # taskbar_width = rect[2] - rect[0]
        # self.resize(taskbar_width, taskbar_height)
        # self.move(rect[0], rect[1])
        screen = QApplication.primaryScreen().geometry()
        # 让主窗口全屏
        self.setGeometry(0, 0, screen.width(), screen.height())
        self.setWindowOpacity(0.9)

        # 主部件和布局
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 创建一个居中容器用于放置按钮
        btn_container = QWidget(self.centralWidget())
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        # 回到桌面按钮
        btn_desktop = QPushButton("🖥️回到桌面", self)
        btn_desktop.setStyleSheet("font-size: 15px;")
        btn_desktop.clicked.connect(self.on_back_to_desktop)
        btn_layout.addWidget(btn_desktop)

        # Win+Tab按钮
        btn_wintab = QPushButton("🗒️任务视图", self)
        btn_wintab.setStyleSheet("font-size: 15px;")
        btn_wintab.clicked.connect(self.on_win_tab)
        btn_layout.addWidget(btn_wintab)

        # 打开资源管理器按钮
        btn_explorer = QPushButton("📦️打开前端", self)
        btn_explorer.setStyleSheet("font-size: 15px;")
        btn_explorer.clicked.connect(self.on_open_dgmix)
        btn_layout.addWidget(btn_explorer)

        # 将按钮容器添加到主布局并居中
        layout.addWidget(btn_container, alignment=Qt.AlignCenter)

        # 全屏隐藏按钮（中空，四个区域覆盖，按钮区域不覆盖）
        self.btn_hide_top = QPushButton("", self)
        self.btn_hide_top.setStyleSheet("background: rgba(0,0,0,0.01); border: none;")
        self.btn_hide_top.clicked.connect(self.on_hide_all)
        self.btn_hide_top.setVisible(True)

        self.btn_hide_bottom = QPushButton("", self)
        self.btn_hide_bottom.setStyleSheet("background: rgba(0,0,0,0.01); border: none;")
        self.btn_hide_bottom.clicked.connect(self.on_hide_all)
        self.btn_hide_bottom.setVisible(True)

        self.btn_hide_left = QPushButton("", self)
        self.btn_hide_left.setStyleSheet("background: rgba(0,0,0,0.01); border: none;")
        self.btn_hide_left.clicked.connect(self.on_hide_all)
        self.btn_hide_left.setVisible(True)

        self.btn_hide_right = QPushButton("", self)
        self.btn_hide_right.setStyleSheet("background: rgba(0,0,0,0.01); border: none;")
        self.btn_hide_right.clicked.connect(self.on_hide_all)
        self.btn_hide_right.setVisible(True)

        # 跟随窗口和btn_container大小变化调整隐藏按钮大小和位置
        self.resizeEvent = self._resizeEvent

        # 重写show方法，在显示窗口时执行相关代码
        old_show = self.show
        def new_show():
            # 获取屏幕工作区，保存供恢复
            self._original_work_area = get_work_area()
            screen_rect = get_screen_rect()
            set_work_area(*screen_rect)
            old_show()
        self.show = new_show

    def _resizeEvent(self, event):
        # 获取btn_container的几何信息
        btn_container = self.centralWidget().findChild(QWidget)
        if btn_container:
            # 重新计算中间空白区域的位置和大小
            screen = QApplication.primaryScreen().geometry()
            width = int(screen.width() * 0.33)
            height = int(screen.height() * 0.1)
            x = (screen.width() - width) // 2
            y = (screen.height() - height) // 2
            btn_container.setGeometry(x, y, width, height)
            btn_container.setFixedSize(width, height)
            c_geo = btn_container.geometry()
            # 顶部按钮
            self.btn_hide_top.setGeometry(
                0, 0, self.width(), c_geo.top()
            )
            # 底部按钮
            self.btn_hide_bottom.setGeometry(
                0, c_geo.bottom() + 1, self.width(), self.height() - c_geo.bottom() - 1
            )
            # 左侧按钮
            self.btn_hide_left.setGeometry(
                0, c_geo.top(), c_geo.left(), c_geo.height()
            )
            # 右侧按钮
            self.btn_hide_right.setGeometry(
                c_geo.right() + 1, c_geo.top(), self.width() - c_geo.right() - 1, c_geo.height()
            )
        if hasattr(super(), 'resizeEvent'):
            super().resizeEvent(event)
    def on_back_to_desktop(self):
        show_desktop_icons()
        show_taskbar()
        set_work_area(*getattr(self, "_original_work_area", get_work_area()))
        self.close()
    def on_win_tab(self):
        # 模拟 Win+Tab
        pyautogui.hotkey('win', 'tab')
    def on_hide_all(self):
        # 模拟 Win+D
        pyautogui.hotkey('win', 'd')
    def on_open_dgmix(self):
        global GSHWND
        ctypes.windll.user32.ShowWindow(GSHWND, 9) # 9=SW_RESTORE            
        ctypes.windll.user32.SetForegroundWindow(GSHWND)

# 游戏运行状态监听线程
class MonitorRunningAppsThread(QThread):
    play_reload_signal = pyqtSignal()  # 用于通知主线程重载
    play_app_name_signal = pyqtSignal(list)  # 用于传递 play_app_name 到主线程

    def __init__(self, play_lock, play_app_name):
        super().__init__()
        self.play_lock = play_lock
        self.play_app_name = play_app_name
        self.running = True

    def check_running_apps(self):
        """检查当前运行的应用"""
        global valid_apps
        # 获取当前运行的所有进程
        current_running_apps = set()
        exe_to_names = {}
        for app in valid_apps:
            exe_to_names.setdefault(app['path'].lower(), []).append(app['name'])

        for process in psutil.process_iter(['pid', 'exe']):
            try:
                exe_path = process.info['exe']
                if exe_path:
                    exe_path_lower = exe_path.lower()
                    if exe_path_lower in exe_to_names:
                        # 只保留last_played靠前的游戏名
                        for game_name in settings.get("last_played", []):
                            if game_name in exe_to_names[exe_path_lower]:
                                current_running_apps.add(game_name)
                                break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # 如果当前运行的应用和 play_app_name 中的内容不同，更新 play_app_name
        with self.play_lock:  # 加锁，确保修改时线程安全
            if current_running_apps != set(self.play_app_name):
                self.play_app_name = list(current_running_apps)
                self.play_reload_signal.emit()  # 发出信号通知主线程
                self.play_app_name_signal.emit(self.play_app_name)  # 将 play_app_name 发送到主线程
            else:
                play_reload = False

    def run(self):
        """后台线程的运行方法"""
        while self.running:
            self.check_running_apps()  # 检查运行的应用
            time.sleep(1)  # 每秒检查一次进程

    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()  # 等待线程结束
class ScreenshotScannerThread(QThread):
    """后台线程用于扫描截图目录"""
    screenshots_scanned = pyqtSignal(list)  # 信号，用于通知主线程扫描完成

    def __init__(self):
        super().__init__()
        self.running = True

    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()  # 等待线程结束

    def run(self):
        """扫描截图目录，加载文件路径和元数据"""
        all_screenshots = []
        base_dir = "screenshot"
        if self.running and os.path.isdir(base_dir):
            for game in os.listdir(base_dir):
                if not self.running:  # 检查是否需要停止
                    break
                game_dir = os.path.join(base_dir, game)
                if os.path.isdir(game_dir):
                    for fname in os.listdir(game_dir):
                        if not self.running:  # 检查是否需要停止
                            break
                        if fname.lower().endswith(".png"):
                            path = os.path.join(game_dir, fname)
                            ts = os.path.getmtime(path)
                            all_screenshots.append((path, game, ts))
        
        if self.running:  # 只有在没有停止的情况下才发送信号
            all_screenshots.sort(key=lambda x: x[2], reverse=True)
            self.screenshots_scanned.emit(all_screenshots)

class ScreenshotLoaderThread(QThread):
    """后台线程用于加载和缩放图片"""
    screenshot_loaded = pyqtSignal(list)  # 信号，用于通知主线程全部加载完成
    screenshot_single_loaded = pyqtSignal(int, tuple)  # 信号，用于通知主线程单张图片加载完成 (索引, (thumb, path, game, ts))

    def __init__(self, screenshots, icon_size, image_indices=None):
        super().__init__()
        self.screenshots = screenshots
        self.icon_size = icon_size
        self.running = True
        # 如果没有指定索引，默认加载所有图片
        self.image_indices = image_indices if image_indices is not None else list(range(len(screenshots)))

    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()  # 等待线程结束

    def run(self):
        """批量加载图片并定期释放UI线程"""
        loaded_screenshots = []
        for idx in self.image_indices:
            if not self.running:  # 检查是否需要停止
                break
            try:
                if 0 <= idx < len(self.screenshots):
                    path, game, ts = self.screenshots[idx]
                    pixmap = QtGui.QPixmap(path)
                    thumb = pixmap.scaled(
                        int(self.icon_size), int(self.icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    loaded_screenshots.append((thumb, path, game, ts))
                    
                    # 发送单张图片加载完成信号，让UI线程立即更新
                    self.screenshot_single_loaded.emit(idx, (thumb, path, game, ts))
                    
                    # 短暂休眠，给UI线程处理事件的机会
                    self.msleep(1)
                    
            except Exception as e:
                print(f"加载图片失败: {path}, 错误: {e}")
        
        if self.running:  # 只有在没有停止的情况下才发送信号
            self.screenshot_loaded.emit(loaded_screenshots)

class ScreenshotWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_dialog = None  # 新增：记录当前弹窗
        self.filter_game_name = None  # 当前筛选的游戏名
        self.setWindowTitle("截图浏览")
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 从父类获取缩放因子，如果父类没有则从设置中读取
        self.scale_factor = getattr(parent, 'scale_factor', settings.get("scale_factor", 1.0))
        
        # 获取屏幕信息
        screen = QDesktopWidget().screenGeometry()
        screen_width = screen.width()
        
        # 计算高度：从屏幕顶端到GameSelector的divider之上
        # 获取父窗口（GameSelector）的高度
        parent_height = getattr(parent, 'height', lambda: screen.height)()
        if callable(parent_height):
            parent_height = parent_height()

        # 设置ScreenshotWindow的高度为父窗口高度减去底部区域高度
        window_height = parent_height - int(70 * self.scale_factor)
        
        # 调整大小
        self.resize(screen_width, window_height)
        # 将窗口定位在屏幕左上角
        self.move(0, 0)
        
        self.icon_size = 256 * self.scale_factor
        # ScreenshotWindow.__init__ 内左侧面板部分
        # 统一按钮样式
        btn_style = f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * self.scale_factor)}px;
                border: none;
                font-size: {int(30 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """

        BTN_HEIGHT = int(90 * self.scale_factor)  # 统一按钮高度

        def on_backup_save_clicked():
            open_maobackup("--quick-dgaction")
        def on_backup_restore_clicked(): 
            open_maobackup("--quick-dgrestore")
        def on_view_backup_list_clicked(): 
            open_maobackup("-backuplist")
        def open_maobackup(sysargv):
            exe_path = os.path.join(program_directory, "maobackup.exe")
            game_name = self.game_name_label.text()
            self.parent().startopenmaobackup(sysargv, game_name, exe_path)
            self.safe_close()  # 关闭当前窗口
        def on_mapping_clicked():
            game_name = self.game_name_label.text()
            # 读取 set.json 的 on_mapping_clicked 列表
            if "on_mapping_clicked" not in settings:
                settings["on_mapping_clicked"] = []
            if game_name in settings["on_mapping_clicked"]:
                settings["on_mapping_clicked"].remove(game_name)
                self.btn_mapping.setText("游玩时开启映射(×)")
            else:
                settings["on_mapping_clicked"].append(game_name)
                self.btn_mapping.setText("游玩时开启映射(✔)")
            # 保存到 set.json
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        def on_freeze_clicked():
            game_name = self.game_name_label.text()
            #options = ["跟随全局", "不冻结", "内置核心冻结", "调用雪藏冻结"]
            options = ["跟随全局"]
            if "freeze_mode" not in settings:
                settings["freeze_mode"] = {}
            current_mode = settings["freeze_mode"].get(game_name, "跟随全局")
        
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("选择冻结方式")
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: rgba(46, 46, 46, 0.98);
                    border-radius: 12px;
                    border: 2px solid #444444;
                }
            """)
            layout = QtWidgets.QVBoxLayout(dialog)
            layout.setSpacing(12)
            layout.setContentsMargins(20, 20, 20, 20)
        
            info_label = QLabel("请选择该游戏的冻结方式")
            info_label.setStyleSheet("color: #aaa; font-size: 18px;")
            layout.addWidget(info_label)
        
            dialog.buttons = []
            dialog.current_index = 0
        
            def update_highlight():
                for i, btn in enumerate(dialog.buttons):
                    if i == dialog.current_index:
                        btn.setStyleSheet("background-color: #93ffff; color: #222; font-size: 18px; border-radius: 8px;")
                    else:
                        btn.setStyleSheet("background-color: #444444; color: white; font-size: 18px; border-radius: 8px;")
            dialog.update_highlight = update_highlight
        
            def select_option(idx):
                mode = options[idx]
                settings["freeze_mode"][game_name] = mode
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4, ensure_ascii=False)
                self.btn_freeze.setText(f"冻结方式({mode})")
                dialog.accept()
        
            for idx, opt in enumerate(options):
                btn = QPushButton(opt)
                btn.clicked.connect(lambda checked=False, idx=idx: select_option(idx))
                layout.addWidget(btn)
                dialog.buttons.append(btn)
        
            dialog.setLayout(layout)
            dialog.update_highlight()
        
            def keyPressEvent(event):
                if event.key() in (Qt.Key_Up, Qt.Key_W):
                    dialog.current_index = (dialog.current_index - 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif event.key() in (Qt.Key_Down, Qt.Key_S):
                    dialog.current_index = (dialog.current_index + 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                    dialog.buttons[dialog.current_index].click()
            dialog.keyPressEvent = keyPressEvent
        
            def handle_gamepad_input(action):
                if action in ('UP',):
                    dialog.current_index = (dialog.current_index - 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif action in ('DOWN',):
                    dialog.current_index = (dialog.current_index + 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif action in ('A',):
                    dialog.buttons[dialog.current_index].click()
                elif action in ('B',):
                    dialog.close()
            dialog.handle_gamepad_input = handle_gamepad_input
            self.active_dialog = dialog  # 记录当前弹窗
            dialog.exec_()
            self.active_dialog = None    # 关闭后清空
            
        def on_custom_proc_clicked(): 
            self.parent().custom_valid_show(self.game_name_label.text()) if self.parent() and hasattr(self.parent(), "custom_valid_show") else None 
            self.safe_close()  # 关闭当前窗口
        def on_tools_clicked():
            game_name = self.game_name_label.text()
            if "custom_tools" not in settings:
                settings["custom_tools"] = []
            found = next((item for item in settings["custom_tools"] if item["name"] == game_name), None)
            tools = found["tools"] if found else []
            tool_names = [app["name"] for app in more_apps]
            tool_paths = {app["name"]: app["path"] for app in more_apps}
        
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("选择要关联的工具")
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: rgba(46, 46, 46, 0.98);
                    border-radius: 12px;
                    border: 2px solid #444444;
                }
            """)
            layout = QtWidgets.QVBoxLayout(dialog)
            layout.setSpacing(12)
            layout.setContentsMargins(20, 20, 20, 20)
        
            info_label = QLabel("点击工具添加到游戏连携启动")
            info_label.setStyleSheet("color: #aaa; font-size: 18px;")
            layout.addWidget(info_label)
        
            dialog.buttons = []
            dialog.current_index = 0
        
            def update_btn_text(btn, tool_name):
                if any(t["name"] == tool_name for t in tools):
                    btn.setText(f"✔ {tool_name}")
                else:
                    btn.setText(tool_name)
        
            def update_highlight():
                for i, btn in enumerate(dialog.buttons):
                    if i == dialog.current_index:
                        btn.setStyleSheet("background-color: #93ffff; color: #222; font-size: 18px; border-radius: 8px;")
                    else:
                        btn.setStyleSheet("background-color: #444444; color: white; font-size: 18px; border-radius: 8px;")
            dialog.update_highlight = update_highlight
        
            def on_click(tool):
                if any(t["name"] == tool for t in tools):
                    tools[:] = [t for t in tools if t["name"] != tool]
                else:
                    tool_entry = {"name": tool, "path": tool_paths[tool]}
                    if found:
                        found["tools"].append(tool_entry)
                    else:
                        settings["custom_tools"].append({"name": game_name, "tools": [tool_entry]})
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4, ensure_ascii=False)
                count = len(found["tools"]) if found else 1
                self.btn_tools.setText(f"附加工具启动({count})")
                for idx, btn in enumerate(dialog.buttons):
                    update_btn_text(btn, tool_names[idx])
                dialog.update_highlight()
        
            for tool_name in tool_names:
                btn = QPushButton()
                update_btn_text(btn, tool_name)
                btn.clicked.connect(lambda checked=False, tool=tool_name: on_click(tool))
                layout.addWidget(btn)
                dialog.buttons.append(btn)
        
            dialog.setLayout(layout)
            dialog.update_highlight()
        
            def keyPressEvent(event):
                if event.key() in (Qt.Key_Up, Qt.Key_W):
                    dialog.current_index = (dialog.current_index - 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif event.key() in (Qt.Key_Down, Qt.Key_S):
                    dialog.current_index = (dialog.current_index + 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                    dialog.buttons[dialog.current_index].click()
            dialog.keyPressEvent = keyPressEvent
        
            def handle_gamepad_input(action):
                if action in ('UP',):
                    dialog.current_index = (dialog.current_index - 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif action in ('DOWN',):
                    dialog.current_index = (dialog.current_index + 1) % len(dialog.buttons)
                    dialog.update_highlight()
                elif action in ('A',):
                    dialog.buttons[dialog.current_index].click()
                elif action in ('B',):
                    dialog.close()
            dialog.handle_gamepad_input = handle_gamepad_input
            self.active_dialog = dialog  # 记录当前弹窗
            dialog.exec_()
            self.active_dialog = None    # 关闭后清空
            
        def on_cover_clicked():
            self.qsaa_thread = QuickStreamAppAddThread(args=["-choosecover", str(self.game_name_label.text())])
            if self.parent() and hasattr(self.parent(), "deep_reload_games"):
                self.qsaa_thread.finished_signal.connect(self.parent().deep_reload_games)
            self.qsaa_thread.start()
        def on_rename_clicked():
            # 自定义重命名对话框，支持“使用存档游戏名称”按钮
            old_name = self.game_name_label.text()
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("重命名游戏")
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            vbox = QtWidgets.QVBoxLayout(dialog)
            prompt = QLabel('<span style="color:white;">请输入新的游戏名称：</span>')
            prompt.setTextFormat(Qt.RichText)
            # 放大一倍的字体大小并设为白色
            large_font_px = int(40 * self.scale_factor)
            prompt.setStyleSheet(f"color: white; font-size: {large_font_px}px;")
            vbox.addWidget(prompt)
            edit = QLineEdit(old_name)
            edit.setStyleSheet(f"color: white; font-size: {large_font_px}px; background-color: #333333; border: 1px solid #555555; padding: 8px;")
            edit.setFixedHeight(int(BTN_HEIGHT))
            vbox.addWidget(edit)
            hbox = QtWidgets.QHBoxLayout()
            use_btn = QPushButton("使用存档游戏名称")
            ok_btn = QPushButton("确定")
            cancel_btn = QPushButton("取消")
            btn_h = int(BTN_HEIGHT)
            btn_style_big = f"background-color: #444444; color: white; font-size: {large_font_px}px; padding: {int(12 * self.scale_factor)}px; border: none; border-radius: 8px;"
            use_btn.setStyleSheet(btn_style_big)
            ok_btn.setStyleSheet(btn_style_big)
            cancel_btn.setStyleSheet(btn_style_big)
            use_btn.setFixedHeight(btn_h)
            ok_btn.setFixedHeight(btn_h)
            cancel_btn.setFixedHeight(btn_h)
            hbox.addWidget(use_btn)
            hbox.addStretch(1)
            hbox.addWidget(ok_btn)
            hbox.addWidget(cancel_btn)
            vbox.addLayout(hbox)

            def use_save_name():
                config_path = os.path.join(program_directory, "webdav_config.json")
                if not os.path.exists(config_path):
                    QMessageBox.warning(dialog, "提示", "未找到 webdav_config.json")
                    return
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    names = [g.get("name") for g in cfg.get("games", []) if isinstance(g, dict) and g.get("name")]
                except Exception as e:
                    QMessageBox.warning(dialog, "提示", f"读取配置失败：{e}")
                    return
                if not names:
                    QMessageBox.warning(dialog, "提示", "配置文件中未找到游戏名称")
                    return
                # 使用自定义列表对话框以支持键盘/触屏操作
                select_dlg = QtWidgets.QDialog(dialog)
                select_dlg.setWindowTitle("选择存档游戏名称")
                select_dlg.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
                # 统一外观样式，圆角半透明背景
                select_dlg.setStyleSheet("""
                    QDialog { background-color: rgba(46,46,46,0.98); border-radius: 12px; border: 2px solid #444444; }
                """)
                select_layout = QtWidgets.QVBoxLayout(select_dlg)
                select_layout.setContentsMargins(16, 12, 16, 12)
                select_layout.setSpacing(12)

                list_widget = QtWidgets.QListWidget(select_dlg)
                list_widget.setFrameShape(QtWidgets.QFrame.NoFrame)
                list_widget.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
                list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
                list_widget.setSpacing(int(8 * self.scale_factor))
                list_widget.setStyleSheet(f"""
                    QListWidget {{ color: white; background-color: #2b2b2b; border-radius: 8px; padding: 8px; }}
                    QListWidget::item {{ padding: 12px; }}
                    QListWidget::item:selected {{ background-color: #93ffff; color: #222; border-radius: 6px; }}
                    QScrollBar:vertical {{ background: transparent; width: 14px; margin: 0px 0px 0px 0px; }}
                    QScrollBar::handle:vertical {{ background: #555; border-radius: 7px; min-height: 20px; }}
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
                """)
                # 填充列表项并调整每项高度以便可读
                item_h = int( (large_font_px * 1.6) )
                for name in names:
                    it = QtWidgets.QListWidgetItem(name)
                    it.setSizeHint(QSize(0, item_h))
                    list_widget.addItem(it)
                list_widget.setCurrentRow(0)
                select_layout.addWidget(list_widget)

                # 按钮区域：居中显示
                btn_h_small = int(BTN_HEIGHT * 1.2)
                btn_ok2 = QPushButton("确定", select_dlg)
                btn_cancel2 = QPushButton("取消", select_dlg)
                btn_ok2.setFixedHeight(btn_h_small)
                btn_cancel2.setFixedHeight(btn_h_small)
                btn_ok2.setStyleSheet(f"background-color: #444444; color: white; font-size: {int(24 * self.scale_factor)}px; border: none; border-radius: 8px;")
                btn_cancel2.setStyleSheet(f"background-color: #444444; color: white; font-size: {int(24 * self.scale_factor)}px; border: none; border-radius: 8px;")
                h2 = QtWidgets.QHBoxLayout()
                h2.setSpacing(int(12 * self.scale_factor))
                btn_ok2.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                btn_cancel2.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                h2.addWidget(btn_ok2, 1)
                h2.addWidget(btn_cancel2, 1)
                select_layout.addLayout(h2)

                # 支持触屏拖动滚动（若可用）
                try:
                    QScroller.grabGesture(list_widget.viewport(), QScroller.LeftMouseButtonGesture)
                except Exception:
                    pass

                # 回车选择、双击选择
                def on_accept():
                    cur = list_widget.currentItem()
                    if cur:
                        edit.setText(cur.text())
                    select_dlg.accept()
                def on_reject():
                    select_dlg.reject()
                btn_ok2.clicked.connect(on_accept)
                btn_cancel2.clicked.connect(on_reject)
                list_widget.itemDoubleClicked.connect(lambda it: (edit.setText(it.text()), select_dlg.accept()))

                # 键盘事件：Enter 接受, Esc 取消
                def list_key_event(event):
                    if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                        on_accept()
                    elif event.key() == Qt.Key_Escape:
                        on_reject()
                    else:
                        return QtWidgets.QListWidget.keyPressEvent(list_widget, event)
                list_widget.keyPressEvent = list_key_event

                # 限制对话框大小，以避免列表项过度拉伸
                dlg_w = min(int(self.width() * 0.6), int(900 * self.scale_factor))
                dlg_h = min(int(self.height() * 0.6), int(600 * self.scale_factor))
                select_dlg.setFixedSize(dlg_w, dlg_h)

                # 标记为当前活动弹窗，便于手柄事件转发
                self.active_dialog = select_dlg
                try:
                    if select_dlg.exec_() == QDialog.Accepted:
                        pass
                finally:
                    self.active_dialog = None

            use_btn.clicked.connect(use_save_name)
            ok_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)

            if dialog.exec_() == QDialog.Accepted:
                new_name = edit.text().strip()
                if new_name and new_name != old_name:
                    # 直接修改 apps.json
                    json_path = f"{APP_INSTALL_PATH}\\config\\apps.json"
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        changed = False
                        for app in data.get("apps", []):
                            if app.get("name") == old_name:
                                app["name"] = new_name
                                changed = True
                        if changed:
                            with open(json_path, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=4, ensure_ascii=False)
                        else:
                            QMessageBox.warning(self, "提示", "未找到要重命名的游戏")
                    except Exception as e:
                        QMessageBox.warning(self, "提示", f"重命名失败：{e}")
                        return

                    # 替换 set.json 中所有 old_name
                    try:
                        set_path = "set.json"
                        if os.path.exists(set_path):
                            with open(set_path, "r", encoding="utf-8") as f:
                                set_data = json.load(f)
                            def replace_name(obj):
                                if isinstance(obj, list):
                                    return [replace_name(x) for x in obj]
                                elif isinstance(obj, dict):
                                    return {k: replace_name(v) for k, v in obj.items()}
                                elif isinstance(obj, str):
                                    return new_name if obj == old_name else obj
                                else:
                                    return obj
                            set_data = replace_name(set_data)
                            with open(set_path, "w", encoding="utf-8") as f:
                                json.dump(set_data, f, indent=4, ensure_ascii=False)
                    except Exception as e:
                        QMessageBox.warning(self, "提示", f"set.json替换失败：{e}")
                    # 刷新游戏列表
                    if self.parent() and hasattr(self.parent(), "deep_reload_games"):
                        self.parent().deep_reload_games()
                    # 关闭窗口
                    self.close()
        def on_open_folder_clicked():
            # 打开当前游戏的文件夹
            game_name = self.game_name_label.text()
            # 在 valid_apps 里查找对应游戏的路径
            game_path = None
            for app in valid_apps:
                if app["name"] == game_name:
                    game_path = app["path"]
                    break
            if game_path and os.path.exists(game_path):
                folder = os.path.dirname(game_path)
                if os.path.exists(folder):
                    subprocess.Popen(f'explorer "{folder}"')
                else:
                    QMessageBox.warning(self, "提示", "未找到游戏文件夹。")
            else:
                QMessageBox.warning(self, "提示", "未找到游戏路径。")
        def on_remove_clicked():
            # 创建确认弹窗
            self.confirm_dialog = ConfirmDialog("确认从游戏列表移除该游戏吗？\n（不会删除游戏数据）", scale_factor=self.scale_factor)
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            self.confirm_dialog = ConfirmDialog("确认从游戏列表移除该游戏吗？\n（二次确认）", scale_factor=self.scale_factor)
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            self.qsaa_thread = QuickStreamAppAddThread(args=["-delete", str(self.game_name_label.text())])
            if self.parent() and hasattr(self.parent(), "deep_reload_games"):
                self.qsaa_thread.finished_signal.connect(self.parent().deep_reload_games)
                self.qsaa_thread.finished_signal.connect(self.safe_close)
            self.qsaa_thread.start()


        # 主水平布局
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(int(10 * self.scale_factor), int(10 * self.scale_factor), int(10 * self.scale_factor), int(10 * self.scale_factor))
        self.main_layout.setSpacing(int(10 * self.scale_factor))

        # 左侧信息面板
        self.left_panel = QWidget(self)
        left_panel_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_panel_layout.setAlignment(Qt.AlignTop)

        # 游戏名标签
        self.game_name_label = QLabel("游戏名称", self.left_panel)
        self.game_name_label.setStyleSheet(f"color: white; font-size: {int(40 * self.scale_factor)}px; font-weight: bold;")
        self.game_name_label.setMaximumWidth(self.width() // 2 - int(150 * self.scale_factor))
        self.play_time_label = QLabel(self.left_panel)
        self.play_time_label.setStyleSheet(f"color: white; font-size: {int(30 * self.scale_factor)}px; font-weight: normal;")
        left_panel_layout.addWidget(self.game_name_label)
        left_panel_layout.setSpacing(int(10 * self.scale_factor))
        left_panel_layout.addWidget(self.play_time_label)
        left_panel_layout.setSpacing(int(19 * self.scale_factor))

        # 开头单独按钮
        btn_toolx = QPushButton("同步游戏存档", self.left_panel)
        btn_toolx.setFixedHeight(BTN_HEIGHT)
        btn_toolx.setStyleSheet(btn_style)
        btn_toolx.clicked.connect(on_backup_save_clicked)
        left_panel_layout.addWidget(btn_toolx)

        # 第一排：恢复/查看存档列表
        row1 = QHBoxLayout()
        btn_backup = QPushButton("恢复游戏存档", self.left_panel)
        btn_backup.setFixedHeight(BTN_HEIGHT)
        btn_backup.setStyleSheet(btn_style)
        btn_backup.clicked.connect(on_backup_restore_clicked)
        row1.addWidget(btn_backup)

        btn_restore = QPushButton("查看存档列表", self.left_panel)
        btn_restore.setFixedHeight(BTN_HEIGHT)
        btn_restore.setStyleSheet(btn_style)
        btn_restore.clicked.connect(on_view_backup_list_clicked)
        row1.addWidget(btn_restore)
        left_panel_layout.addLayout(row1)

        self.info_label2 = QLabel("---------------------------------------------游戏特性相关---------------------------------------------", self)
        self.info_label2.setStyleSheet(f"color: #aaa; font-size: {int(16 * self.scale_factor)}px; padding: 0px;")
        self.info_label2.setAlignment(Qt.AlignCenter)
        left_panel_layout.addWidget(self.info_label2)
        # 第二排：映射/冻结
        row2 = QHBoxLayout()
        self.btn_mapping = QPushButton("游玩时开启映射(×)", self.left_panel)
        self.btn_mapping.setFixedHeight(BTN_HEIGHT)
        self.btn_mapping.setStyleSheet(btn_style)
        # 新增：根据 set.json 设置初始状态
        if "on_mapping_clicked" in settings and self.game_name_label.text() in settings["on_mapping_clicked"]:
            self.btn_mapping.setText("游玩时开启映射(✔)")
        self.btn_mapping.clicked.connect(on_mapping_clicked)
        row2.addWidget(self.btn_mapping)

        self.btn_freeze = QPushButton("冻结方式(跟随全局)", self.left_panel)
        if "freeze_mode" in settings and self.game_name_label.text() in settings["freeze_mode"]:
            self.btn_freeze.setText(f"冻结方式({settings['freeze_mode'][self.game_name_label.text()]})")
        self.btn_freeze.setFixedHeight(BTN_HEIGHT)
        self.btn_freeze.setStyleSheet(btn_style)
        self.btn_freeze.clicked.connect(on_freeze_clicked)
        row2.addWidget(self.btn_freeze)
        left_panel_layout.addLayout(row2)

        # 第三排：配置自定义进程 + 附加工具启动
        row3 = QHBoxLayout()
        self.btn_custom_proc = QPushButton("配置自定义进程(×)", self.left_panel)
        if "custom_valid_apps" in settings and any(item["name"] == self.game_name_label.text() for item in settings["custom_valid_apps"]):
            self.btn_custom_proc.setText("配置自定义进程(✔)")
        self.btn_custom_proc.setFixedHeight(BTN_HEIGHT)
        self.btn_custom_proc.setStyleSheet(btn_style)
        self.btn_custom_proc.clicked.connect(on_custom_proc_clicked)
        row3.addWidget(self.btn_custom_proc)

        self.btn_tools = QPushButton("附加工具启动(0)", self.left_panel)
        if "custom_tools" in settings:
            for item in settings["custom_tools"]:
                if item["name"] == self.game_name_label.text():
                    self.btn_tools.setText(f"附加工具启动({len(item['tools'])})")
        self.btn_tools.setFixedHeight(BTN_HEIGHT)
        self.btn_tools.setStyleSheet(btn_style)
        self.btn_tools.clicked.connect(on_tools_clicked)
        row3.addWidget(self.btn_tools)
        left_panel_layout.addLayout(row3)
        self.info_label1 = QLabel("---------------------------------------------游戏数据相关---------------------------------------------", self)
        self.info_label1.setStyleSheet(f"color: #aaa; font-size: {int(16 * self.scale_factor)}px; padding: 0px;")
        self.info_label1.setAlignment(Qt.AlignCenter)
        left_panel_layout.addWidget(self.info_label1)

        # 第四排：自定义封面/重命名
        row4 = QHBoxLayout()
        btn_cover = QPushButton("自定义封面", self.left_panel)
        btn_cover.setFixedHeight(BTN_HEIGHT)
        btn_cover.setStyleSheet(btn_style)
        btn_cover.clicked.connect(on_cover_clicked)
        row4.addWidget(btn_cover)

        btn_rename = QPushButton("重命名游戏名称", self.left_panel)
        btn_rename.setFixedHeight(BTN_HEIGHT)
        btn_rename.setStyleSheet(btn_style)
        btn_rename.clicked.connect(on_rename_clicked)
        row4.addWidget(btn_rename)
        left_panel_layout.addLayout(row4)

        # 第五排：打开文件夹/移除游戏
        row5 = QHBoxLayout()
        btn_open_folder = QPushButton("打开游戏文件夹", self.left_panel)
        btn_open_folder.setFixedHeight(BTN_HEIGHT)
        btn_open_folder.setStyleSheet(btn_style)
        btn_open_folder.clicked.connect(on_open_folder_clicked)
        row5.addWidget(btn_open_folder)

        btn_remove = QPushButton("移除游戏", self.left_panel)
        btn_remove.setFixedHeight(BTN_HEIGHT)
        btn_remove.setStyleSheet(btn_style)
        btn_remove.clicked.connect(on_remove_clicked)
        row5.addWidget(btn_remove)
        left_panel_layout.addLayout(row5)
        # 截图列表控件
        self.listWidget = QtWidgets.QListWidget(self)
        self.listWidget.setViewMode(QtWidgets.QListView.IconMode)
        self.listWidget.setIconSize(QSize(int(self.icon_size), int(self.icon_size)))
        self.listWidget.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.listWidget.setMovement(QtWidgets.QListView.Static)
        self.listWidget.setSpacing(int(10 * self.scale_factor))
        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.listWidget.itemClicked.connect(self.on_item_clicked)
        self.listWidget.setFocus()
        # 添加鼠标左键拖动滚动手势
        QScroller.grabGesture(self.listWidget.viewport(), QScroller.LeftMouseButtonGesture)

        # 右侧布局（包含listWidget）
        right_panel = QWidget(self)
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(int(10 * self.scale_factor))
        # 不在此处设置对齐，改为保存布局供后续动态调整
        right_layout.addWidget(self.listWidget)
        self.right_panel = right_panel
        self.right_layout = right_layout
        self.info_label = QLabel(self)
        self.info_label.setStyleSheet(f"color: #aaa; font-size: {int(18 * self.scale_factor)}px; padding: {int(8 * self.scale_factor)}px;")
        self.info_label.setAlignment(Qt.AlignLeft)
        right_layout.addWidget(self.info_label)
        # 初始使列表靠右以匹配带左侧面板的布局
        self.right_layout.setAlignment(self.listWidget, Qt.AlignRight)

        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(right_panel)

        # 用 QWidget 包裹 main_layout
        main_widget = QWidget(self)
        main_widget.setLayout(self.main_layout)
        main_widget.setFixedWidth(int(1800 * self.scale_factor))

        # 外层垂直布局
        layout = QtWidgets.QVBoxLayout(self)
        # 关闭按钮放在最上面
        self.closeButton = QPushButton("关闭", self)
        self.closeButton.setFixedHeight(int(50 * self.scale_factor))
        self.closeButton.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                font-size: 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.closeButton.clicked.connect(self.close)
        layout.addWidget(self.closeButton)

        # 使用水平包装布局在左右两侧添加弹性间距，使主内容固定为1800且居中
        h_wrapper = QtWidgets.QHBoxLayout()
        h_wrapper.addStretch(1)
        h_wrapper.addWidget(main_widget)
        h_wrapper.addStretch(1)
        layout.addLayout(h_wrapper)

        self.setLayout(layout)
        self.all_screenshots = []
        self.current_screenshots = []
        # 事件过滤：拦截按键处理快捷操作
        self.listWidget.installEventFilter(self)
        self.batch_mode = False

        # 添加手柄输入相关属性
        self.current_index = 0
        self.current_button_index = 0  # 当前焦点按钮索引
        self.in_left_panel = False     # 是否在左侧按钮区域
        self.left_panel_buttons = [] # 用于存储左侧按钮
        self.disable_left_panel_switch = False
        self.last_input_time = 0
        self.input_delay = 200
        self.ignore_input_until = 0
        self.buttons = []  # 用于存储列表项
        self.init_left_panel_buttons() # 初始化左侧按钮
        self.load_all_images = False  # 新增：是否加载全部图片的标志
        #self.update_highlight()  # 初始化高亮状态

    def on_item_clicked(self, item):
        if QApplication.mouseButtons() == Qt.RightButton:  # 检测是否为右键点击
            img_path = item.data(Qt.UserRole)  # 获取图片路径
            if os.path.exists(img_path):
                subprocess.Popen(f'explorer /select,"{img_path}"')  # 使用文件管理器打开图片位置
        self.start_fullscreen_preview()
    def showEvent(self, event):
        """窗口显示时触发重新加载截图"""
        super().showEvent(event)
        #self.reload_screenshots()
        self.raise_()

    def reload_screenshots(self):
        """重新加载截图目录并启动后台线程"""
        # 清除原图片并显示加载提示
        self.listWidget.clear()
        item = QListWidgetItem()
        item.setFlags(Qt.NoItemFlags)
        label = QLabel("正在扫描截图目录...")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color: #aaa; font-size: 28px;")
        label.setMinimumHeight(220)
        label.setMinimumWidth(self.listWidget.viewport().width() - 40)
        self.listWidget.addItem(item)
        self.listWidget.setItemWidget(item, label)
        item.setSizeHint(label.sizeHint())
        # 判断是否筛选了具体游戏
        if self.filter_game_name and self.filter_game_name != "全部游戏":
            filtered = [item for item in self.all_screenshots if item[1] == self.filter_game_name]
            if not getattr(self, "load_all_images", False):
                self.current_screenshots = filtered[:6]
                self.has_load_more_button = len(filtered) > 6
            else:
                self.current_screenshots = filtered
                self.has_load_more_button = False
            # 显示左侧面板并恢复合理最大宽度
            self.left_panel.setVisible(True)
            self.left_panel.setMaximumWidth(int(950 * self.scale_factor))
            self.listWidget.setFixedWidth(int(950 * self.scale_factor))
            self.icon_size = int(256 * self.scale_factor * 1.75)
            if hasattr(self, 'right_layout'):
                self.right_layout.setAlignment(self.listWidget, Qt.AlignRight)
        else:
            self.current_screenshots = list(self.all_screenshots)
            # 隐藏左侧面板并将其最大宽度设为0，避免残留占位
            self.left_panel.setVisible(False)
            self.left_panel.setMaximumWidth(0)
            self.listWidget.setFixedWidth(int(1630 * self.scale_factor))
            self.icon_size = 256 * self.scale_factor
            if hasattr(self, 'right_layout'):
                self.right_layout.setAlignment(self.listWidget, Qt.AlignHCenter)
            self.has_load_more_button = False

        self.listWidget.setIconSize(QSize(int(self.icon_size), int(self.icon_size)))
        
        # 启动后台线程扫描截图目录
        self.scanner_thread = ScreenshotScannerThread()
        self.scanner_thread.screenshots_scanned.connect(self.on_screenshots_scanned)
        self.scanner_thread.start()

        # 启动后台线程加载所有图片
        self.loader_thread = ScreenshotLoaderThread(self.current_screenshots, self.icon_size)
        self.loader_thread.screenshot_loaded.connect(self.on_screenshots_loaded)
        self.loader_thread.finished.connect(self.update_highlight)
        self.loader_thread.start()
    
    def on_screenshots_scanned(self, all_screenshots):
        """处理扫描完成的截图列表"""
        self.all_screenshots = all_screenshots
        
        # 根据筛选条件过滤截图
        if self.filter_game_name and self.filter_game_name != "全部游戏":
            filtered = [item for item in self.all_screenshots if item[1] == self.filter_game_name]
            self.current_screenshots = filtered
        else:
            self.current_screenshots = list(self.all_screenshots)
        
        # 取消"加载全部图片"按钮逻辑
        self.has_load_more_button = False
        
        # 立即创建所有图片占位符
        self.listWidget.clear()
        
        # 没有截图时显示提示文字
        if not self.current_screenshots:
            item = QListWidgetItem()
            item.setFlags(Qt.NoItemFlags)
            label = QLabel("还没有截图\n在游戏中按下L3+R3记录美好时刻～")
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            label.setStyleSheet("color: #aaa; font-size: 28px;")
            label.setMinimumHeight(int(220 * self.scale_factor))
            label.setMinimumWidth(self.listWidget.viewport().width() - int(40 * self.scale_factor))
            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, label)
            item.setSizeHint(label.sizeHint())
            return
        
        # 创建所有图片占位符
        self.image_items = []
        for _ in range(len(self.current_screenshots)):
            item = QListWidgetItem()
            # 设置图片项大小为图标大小
            item.setSizeHint(QSize(int(self.icon_size), int(self.icon_size * 9 / 16)))
            self.listWidget.addItem(item)
            self.image_items.append(item)
        
        # 计算初始加载数量
        initial_count = 30 if getattr(self, 'disable_left_panel_switch', False) else 6
        # 确保初始数量不超过截图总数
        initial_count = min(initial_count, len(self.current_screenshots))
        
        # 记录已加载的图片数量
        self.loaded_image_count = initial_count
        
        # 启动后台线程加载初始图片
        initial_indices = list(range(initial_count))
        self.loader_thread = ScreenshotLoaderThread(self.current_screenshots, self.icon_size, initial_indices)
        self.loader_thread.screenshot_loaded.connect(self.on_screenshots_loaded)
        self.loader_thread.screenshot_single_loaded.connect(self.on_screenshot_single_loaded)
        self.loader_thread.finished.connect(self.update_highlight)
        self.loader_thread.start()
        
        # 添加滚动事件监听器，实现懒加载
        self.listWidget.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.listWidget.horizontalScrollBar().valueChanged.connect(self.on_scroll)
        # 为listWidget的viewport添加事件过滤器，捕获鼠标滚轮事件
        self.listWidget.viewport().installEventFilter(self)

    def update_highlight(self):
        """更新高亮状态"""
        self.buttons = [self.listWidget.item(i) for i in range(self.listWidget.count())]
        info_text = ""
        if self.buttons:
            self.current_index = max(0, min(self.current_index, len(self.buttons) - 1))
            if not self.in_left_panel:
                self.listWidget.setCurrentItem(self.buttons[self.current_index])
                self.listWidget.scrollToItem(self.buttons[self.current_index])
                for i, item in enumerate(self.buttons):
                    if i == self.current_index:
                        item.setBackground(QColor("#93ffff"))
                        # 显示信息
                        img_path = item.data(Qt.UserRole)
                        # 查找截图元数据并获取索引
                        allidx = len(self.current_screenshots)
                        for idx, (path, game, ts) in enumerate(self.current_screenshots):
                            if path == img_path:
                                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
                                info_text = f"{game} / {timestamp}  （{idx + 1}/{allidx}）"
                                print(info_text)
                                break
                    else:
                        item.setBackground(QColor("transparent"))
            else:
                for item in self.buttons:
                    item.setBackground(QColor("transparent"))
                info_text = ""
        self.info_label.setText(info_text)
        
    def eventFilter(self, source, event):
        """事件过滤器，捕获listWidget的鼠标滚轮事件"""
        if source == self.listWidget.viewport() and event.type() == event.Wheel:
            # 触发懒加载
            self.on_scroll()
        return super().eventFilter(source, event)
        
    def on_scroll(self):
        """处理滚动事件，实现懒加载"""
        # 如果所有图片已经加载完成，或者正在加载中，就直接返回
        if hasattr(self, 'all_images_loaded') and self.all_images_loaded:
            return
        
        if hasattr(self, 'is_loading_images') and self.is_loading_images:
            return
        
        # 检查必要属性是否存在
        if not hasattr(self, 'loaded_image_count') or not hasattr(self, 'current_screenshots'):
            return
        
        # 标记正在加载图片
        self.is_loading_images = True
        
        # 计算需要加载的剩余图片索引
        remaining_indices = list(range(self.loaded_image_count, len(self.current_screenshots)))
        
        # 启动后台线程加载剩余图片
        self.loader_thread = ScreenshotLoaderThread(self.current_screenshots, self.icon_size, remaining_indices)
        self.loader_thread.screenshot_loaded.connect(self.on_remaining_screenshots_loaded)
        self.loader_thread.screenshot_single_loaded.connect(self.on_screenshot_single_loaded)
        self.loader_thread.finished.connect(self.update_highlight)
        self.loader_thread.start()
        
    def on_remaining_screenshots_loaded(self, loaded_screenshots):
        """处理剩余图片加载完成事件"""
        # 标记所有图片已加载完成
        self.all_images_loaded = True
        # 清除正在加载标记
        self.is_loading_images = False
        
    def wheelEvent(self, event):
        """处理鼠标滚轮事件，实现懒加载"""
        # 先调用父类方法处理滚轮事件
        super().wheelEvent(event)
        # 触发懒加载
        self.on_scroll()
        
    def load_screenshots(self):
        """扫描截图目录，加载文件路径和元数据"""
        self.all_screenshots = []
        base_dir = "screenshot"
        if not os.path.isdir(base_dir):
            return
        for game in os.listdir(base_dir):
            game_dir = os.path.join(base_dir, game)
            if not os.path.isdir(game_dir):
                continue
            for fname in os.listdir(game_dir):
                if fname.lower().endswith(".png"):
                    path = os.path.join(game_dir, fname)
                    ts = os.path.getmtime(path)
                    self.all_screenshots.append((path, game, ts))
        self.all_screenshots.sort(key=lambda x: x[2], reverse=True)
        self.current_screenshots = list(self.all_screenshots)

    def on_screenshots_loaded(self, loaded_screenshots):
        """处理所有图片加载完成的事件"""
        # 图片已通过 on_screenshot_single_loaded 逐个加载完成并更新UI
        # 这里只需处理加载完成后的收尾工作
        
        # 移除"加载全部图片"按钮相关逻辑
        self.load_more_item_index = None
        
        # 加载完成后恢复索引并高亮
        if hasattr(self, "restore_index_after_load"):
            self.current_index = min(self.restore_index_after_load, self.listWidget.count() - 1)
            del self.restore_index_after_load
    
    def on_screenshot_single_loaded(self, index, screenshot_data):
        """处理单张图片加载完成信号，立即更新UI"""
        if index < len(self.image_items):
            thumb, path, game, ts = screenshot_data
            item = self.image_items[index]
            icon = QtGui.QIcon(thumb)
            item.setIcon(icon)
            item.setText("")
            item.setData(Qt.UserRole, path)
    
    def get_row_count(self):
        """获取每行的缩略图数量"""
        if self.filter_game_name and self.filter_game_name != "全部游戏":
            return 2
        else:
            return 6
    def move_selection(self, offset):
        """移动选择的截图或左侧按钮"""
        if self.in_left_panel:
            # 左侧按钮区域上下移动
            self.current_button_index = (self.current_button_index + (1 if offset > 0 else -1)) % len(self.left_panel_buttons)
            self.update_left_panel_button_styles()
        else:
            total_buttons = len(self.buttons)
            new_index = self.current_index + offset
            row_count = self.get_row_count()
            # 上下键逻辑，循环跳转
            if offset == -row_count:  # 上移一行
                if new_index < 0:
                    column = self.current_index % row_count
                    new_index = (total_buttons - 1) - (total_buttons - 1) % row_count + column
                    if new_index >= total_buttons:
                        new_index -= row_count
            elif offset == row_count:  # 下移一行
                if new_index >= total_buttons:
                    column = self.current_index % row_count
                    new_index = column
            # 左右键逻辑，循环跳转
            if offset == -1 and new_index < 0:
                new_index = total_buttons - 1
            elif offset == 1 and new_index >= total_buttons:
                new_index = 0
            self.current_index = new_index
            self.update_highlight()

    def handle_gamepad_input(self, action):
        """处理手柄输入，支持左侧按钮和截图框切换"""
        current_time = pygame.time.get_ticks()
        if current_time < self.ignore_input_until:
            return
        if current_time - self.last_input_time < self.input_delay:
            return
        if hasattr(self, 'confirm_dialog') and self.confirm_dialog and self.confirm_dialog.isVisible():
            self.confirm_dialog.handle_gamepad_input(action)
            return
        # 新增：如果有弹窗，转发给弹窗
        if hasattr(self, "active_dialog") and self.active_dialog is not None:
            if hasattr(self.active_dialog, "handle_gamepad_input"):
                self.active_dialog.handle_gamepad_input(action)
            return
        # 全屏预览等原有逻辑...
        if hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview:
            if getattr(self, "has_load_more_button", False):
                allidx = len(self.current_screenshots) + 1  
            else:
                allidx = len(self.current_screenshots)
            if action == 'LEFT':
                self.preview_index = (self.preview_index - 1) % allidx
                self.is_fullscreen_preview.load_preview(self.preview_index)  # 修复调用
                return
            elif action == 'RIGHT':
                self.preview_index = (self.preview_index + 1) % allidx
                self.is_fullscreen_preview.load_preview(self.preview_index)  # 修复调用
                return
            elif action == 'LB':  # 添加LB键切换到上一张
                self.preview_index = (self.preview_index - 1) % allidx
                self.is_fullscreen_preview.load_preview(self.preview_index)  # 修复调用
                return
            elif action == 'RB':  # 添加RB键切换到下一张
                self.preview_index = (self.preview_index + 1) % allidx
                self.is_fullscreen_preview.load_preview(self.preview_index)  # 修复调用
                return
            elif action == "X":
                current_item = self.listWidget.currentItem()
                if current_item:
                    img_path = current_item.data(Qt.UserRole)
                    if img_path and os.path.exists(img_path):
                        subprocess.Popen(f'explorer /select,"{img_path}"')
                return
            elif action == 'Y':
                self.delete_selected_items()
            elif action in ('A', 'B'):
                self.is_fullscreen_preview.close()  # 修复调用
                self.is_fullscreen_preview = None  # 清除引用
                return

        # 新增：左侧按钮区域手柄操作
        if self.in_left_panel:
            if action in ('UP',):
                if self.current_button_index == 0:
                    return  # 如果在第一行的第一个按钮，不能上移
                if self.current_button_index == 1:
                    self.current_button_index = (self.current_button_index - 1) % len(self.left_panel_buttons)
                else:
                    self.current_button_index = (self.current_button_index - 2) % len(self.left_panel_buttons)
                self.update_left_panel_button_styles()
            elif action in ('DOWN',):
                if self.current_button_index == 0:
                    self.current_button_index = (self.current_button_index + 1) % len(self.left_panel_buttons)
                # 如果在倒数第二个或最后一个按钮，不能下移
                elif self.current_button_index >= len(self.left_panel_buttons) - 2:
                    return
                else:
                    self.current_button_index = (self.current_button_index + 2) % len(self.left_panel_buttons)
                self.update_left_panel_button_styles()
            elif action in ('A',):
                self.left_panel_buttons[self.current_button_index].click()
                self.ignore_input_until = pygame.time.get_ticks() + 350  
            elif action in ('LEFT',):
                if self.current_button_index == 0:
                    return
                if self.current_button_index % 2 == 0:
                    self.current_button_index = (self.current_button_index - 1) % len(self.left_panel_buttons)
                    self.update_left_panel_button_styles()
                #else:
                #    # 切换到截图框区域
                #    self.in_left_panel = False
                #    self.update_left_panel_button_styles()
                #    self.update_highlight()
            elif action in ('RIGHT',):
                if (self.current_button_index+1) % 2 == 0:
                    self.current_button_index = (self.current_button_index + 1) % len(self.left_panel_buttons)
                    self.update_left_panel_button_styles()
                else:
                    # 切换到截图框区域
                    self.in_left_panel = False
                    self.update_left_panel_button_styles()
                    self.update_highlight()
            elif action in ('B',):
                self.safe_close()
            self.last_input_time = current_time
            return

        # 截图框区域手柄操作
        if not self.in_left_panel:
            if action == 'A':
                self.start_fullscreen_preview()
            elif action == 'X':
                self.start_filter_mode()
            elif action == 'Y':
                self.delete_selected_items()
            elif action == 'B':
                self.safe_close()
            elif action == 'UP':
                self.move_selection(-self.get_row_count())
            elif action == 'DOWN':
                self.move_selection(self.get_row_count())
            elif action == 'LEFT':
                if self.current_index % 2 == 0 and self.disable_left_panel_switch == False:
                    self.in_left_panel = True
                    self.update_left_panel_button_styles()
                    self.update_highlight()
                else:
                    self.current_index = max(0, self.current_index - 1)
                    self.update_highlight()
            elif action == 'RIGHT':
                if self.current_index % 2 != 0 and self.disable_left_panel_switch == False:
                    return
                else:
                    self.current_index = min(len(self.buttons) - 1, self.current_index + 1)
                    self.update_highlight()
            elif action == 'START':
                self.safe_close()
            self.last_input_time = current_time

    def handle_info_bar_link(self, link):
        if getattr(self, "has_load_more_button", False):
            allidx = len(self.current_screenshots) + 1  
        else:
            allidx = len(self.current_screenshots)
        if link == "prev":
            self.preview_index = (self.preview_index - 1) % allidx
            self.is_fullscreen_preview.load_preview(self.preview_index)
        elif link == "next":
            self.preview_index = (self.preview_index + 1) % allidx
            self.is_fullscreen_preview.load_preview(self.preview_index)
        elif link == "action1":
            self.delete_selected_items()
            #if hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview:
            #    self.is_fullscreen_preview.close()  # 修复调用
            #    self.is_fullscreen_preview = None  # 清除引用
            #self.start_fullscreen_preview()  # 重新打开预览窗口
        elif link == "action2":
            current_item = self.listWidget.currentItem()
            if current_item:
                img_path = current_item.data(Qt.UserRole)
                if img_path and os.path.exists(img_path):
                    subprocess.Popen(f'explorer /select,"{img_path}"')
        elif link == "action3":
            if hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview:
                self.is_fullscreen_preview.close()  # 修复调用
                self.is_fullscreen_preview = None  # 清除引用    

    def init_left_panel_buttons(self):
        # 初始化左侧面板按钮
        self.left_panel_buttons = []  # 存储按钮引用
        for i, btn in enumerate(self.left_panel.findChildren(QPushButton)):
            self.left_panel_buttons.append(btn)
        self.update_left_panel_button_styles()

    def update_left_panel_button_styles(self):
        # 更新左侧面板按钮样式
        for i, button in enumerate(self.left_panel_buttons):
            if i == self.current_button_index and self.in_left_panel:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #444444;
                        color: white;
                        text-align: center;
                        padding: {int(10 * self.scale_factor)}px;
                        border: {int(2 * self.scale_factor)}px solid #93ffff;
                        font-size: {int(30 * self.scale_factor)}px;
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #444444;
                        color: white;
                        text-align: center;
                        padding: {int(10 * self.scale_factor)}px;
                        border: none;
                        font-size: {int(30 * self.scale_factor)}px;
                    }}
                    QPushButton:hover {{
                        background-color: #555555;
                    }}
                """)

    def start_fullscreen_preview(self):
        """显示当前选中图片的全屏预览对话框"""
        global FSPREVIEWHWND
        current_item = self.listWidget.currentItem()
        if not current_item:
            return
        path = current_item.data(Qt.UserRole)
        try:
            index = [item[0] for item in self.current_screenshots].index(path)
        except ValueError:
            index = 0
        self.preview_index = index
    
        self.is_fullscreen_preview = QtWidgets.QDialog(self, flags=Qt.Dialog)
        self.is_fullscreen_preview.setWindowFlag(Qt.FramelessWindowHint)
        # 初始窗口透明度为0，随后播放淡入动画
        try:
            self.is_fullscreen_preview.setWindowOpacity(0.0)
        except Exception:
            pass
        self.is_fullscreen_preview.showFullScreen()
        FSPREVIEWHWND = int(self.is_fullscreen_preview.winId())
        # 窗口淡入动画（保存引用以防被垃圾回收）
        try:
            fade_in_win = QPropertyAnimation(self.is_fullscreen_preview, b"windowOpacity")
            fade_in_win.setDuration(100)
            fade_in_win.setStartValue(0.0)
            fade_in_win.setEndValue(1.0)
            self._fsp_window_fade_in = fade_in_win
            fade_in_win.start()
        except Exception:
            pass
        
        # 创建主布局
        main_layout = QtWidgets.QVBoxLayout(self.is_fullscreen_preview)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        #self.is_fullscreen_preview.setAttribute(Qt.WA_TranslucentBackground)
        #self.is_fullscreen_preview.setStyleSheet("""
        #    QDialog {
        #    background-color: rgba(0, 0, 0, 0.6); /* 设置半透明背景 */
        #    }
        #""")
        
        # 添加信息栏到顶部
        info_bar = QtWidgets.QLabel(self.is_fullscreen_preview)
        info_bar.setStyleSheet(f"""
            QLabel {{ 
                background-color: rgba(0, 0, 0, 0.8); /* 半透明黑色背景 */
                color: white;
                font-size: {int(18 * self.scale_factor)}px;
                padding: {int(12 * self.scale_factor)}px {int(20 * self.scale_factor)}px;
                border-bottom: {int(1 * self.scale_factor)}px solid rgba(255, 255, 255, 0.1);
            }} 
        """)
        info_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        info_bar.setFixedHeight(int(50 * self.scale_factor))  # 调整高度
        info_bar.setTextFormat(Qt.RichText)
        info_bar.setTextInteractionFlags(Qt.TextBrowserInteraction)
        info_bar.setOpenExternalLinks(False)  # 不自动打开外部链接
        info_bar.linkActivated.connect(self.handle_info_bar_link)
        def close_fullscreen_preview(event):
            """关闭全屏预览窗口（使用淡出动画）"""
            if not (hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview):
                return
            dlg = self.is_fullscreen_preview
            try:
                # 创建淡出动画并在完成后真正关闭对话框
                fade_out_win = QPropertyAnimation(dlg, b"windowOpacity")
                fade_out_win.setDuration(100)
                fade_out_win.setStartValue(dlg.windowOpacity() if hasattr(dlg, 'windowOpacity') else 1.0)
                fade_out_win.setEndValue(0.0)
                def _on_fade_finished():
                    try:
                        QtWidgets.QDialog.close(dlg)
                    except Exception:
                        try:
                            dlg.close()
                        except Exception:
                            pass
                    # 清除引用
                    if hasattr(self, 'is_fullscreen_preview'):
                        self.is_fullscreen_preview = None
                fade_out_win.finished.connect(_on_fade_finished)
                self._fsp_window_fade_out = fade_out_win
                fade_out_win.start()
            except Exception:
                try:
                    self.is_fullscreen_preview.close()
                except Exception:
                    pass
                self.is_fullscreen_preview = None
        #info_bar.mousePressEvent = close_fullscreen_preview
        # 绑定实例的 close 方法，使外部直接调用 close() 时也能使用淡出动画
        def _close_no_event():
            close_fullscreen_preview(None)
        try:
            self.is_fullscreen_preview.close = _close_no_event
        except Exception:
            pass
        main_layout.addWidget(info_bar)
        
        # 创建图片标签
        label = QtWidgets.QLabel(self.is_fullscreen_preview)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: black;")
        label.mousePressEvent = close_fullscreen_preview
        # 为 label 添加不透明度效果，QLabel 本身没有 "opacity" 属性
        effect = QtWidgets.QGraphicsOpacityEffect(label)
        label.setGraphicsEffect(effect)
        effect.setOpacity(1.0)
        # 添加鼠标滚轮支持
        def wheelEvent(event):
            delta = event.angleDelta().y()
            if delta > 0:  # 向上滚动，切换到上一张
                self.preview_index = (self.preview_index - 1) % len(self.current_screenshots)
            else:  # 向下滚动，切换到下一张
                self.preview_index = (self.preview_index + 1) % len(self.current_screenshots)
            self.is_fullscreen_preview.load_preview(self.preview_index)
        label.wheelEvent = wheelEvent
        # 添加图片标签和切换按钮
        # 创建水平布局来容纳左右按钮和图片
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)
        
        # 左侧切换按钮
        left_btn = QtWidgets.QPushButton("←")
        left_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: rgba(0, 0, 0, 0.3);
                color: white;
                font-size: {int(36 * self.scale_factor)}px;
                border: none;
                width: {int(50 * self.scale_factor)}px;
                height: {int(1000 * self.scale_factor)}px;
                opacity: 0.5;
            }} 
            QPushButton:hover {{ 
                opacity: 0.9;
            }} 
        """)
        left_btn.clicked.connect(lambda: (
            setattr(self, 'preview_index', (self.preview_index - 1) % len(self.current_screenshots)),
            self.is_fullscreen_preview.load_preview(self.preview_index)
        ))
        h_layout.addWidget(left_btn, alignment=Qt.AlignVCenter)
        
        # 将图片标签添加到布局中心
        h_layout.addWidget(label, 1)
        
        # 右侧切换按钮
        right_btn = QtWidgets.QPushButton("→")
        right_btn.setStyleSheet(f"""
            QPushButton {{ 
                background-color: rgba(0, 0, 0, 0.3);
                color: white;
                font-size: {int(36 * self.scale_factor)}px;
                border: none;
                width: {int(50 * self.scale_factor)}px;
                height: {int(1000 * self.scale_factor)}px;
                opacity: 0.5;
            }} 
            QPushButton:hover {{ 
                opacity: 0.9;
            }} 
        """)
        right_btn.clicked.connect(lambda: (
            setattr(self, 'preview_index', (self.preview_index + 1) % len(self.current_screenshots)),
            self.is_fullscreen_preview.load_preview(self.preview_index)
        ))
        h_layout.addWidget(right_btn, alignment=Qt.AlignVCenter)
        
        # 将水平布局添加到主布局
        main_layout.addLayout(h_layout, 1)
    
        def load_preview(idx):
            # --- 新增：如果只加载了6张且有更多，且向右到第6张，自动加载全部 ---
            if (
                getattr(self, "has_load_more_button", False)
                and idx == 6
                and not getattr(self, "load_all_images", False)
            ):
                # 记录当前图片路径
                current_path = self.current_screenshots[idx - 1][0]
                self.load_all_images = True
                self.reload_screenshots()
                # 重新定位到第6张（原第7张）
                self.preview_index = 6
                QTimer.singleShot(200, lambda: self.is_fullscreen_preview.load_preview(self.preview_index))
                return
    
            path = self.current_screenshots[idx][0]
            pix = QtGui.QPixmap(path)
            screen = QtWidgets.QApplication.primaryScreen().size()
            # 计算90%的尺寸
            scaled_width = int(screen.width() * 0.95)
            scaled_height = int(screen.height() * 0.95)
            scaled = pix.scaled(scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # 添加淡入淡出动画（针对 QGraphicsOpacityEffect）
            def animate_image():
                # 淡出当前图片 — 动画目标为 effect
                fade_out = QPropertyAnimation(effect, b"opacity")
                fade_out.setDuration(50)
                fade_out.setStartValue(1.0)
                fade_out.setEndValue(0.0)

                def on_fade_out_finished():
                    # 设置新图片并淡入
                    label.setPixmap(scaled)
                    fade_in = QPropertyAnimation(effect, b"opacity")
                    fade_in.setDuration(50)
                    fade_in.setStartValue(0.0)
                    fade_in.setEndValue(1.0)
                    # 保存引用以防被垃圾回收
                    self._preview_fade_in = fade_in
                    fade_in.start()

                # 保存引用以防被垃圾回收
                self._preview_fade_out = fade_out
                fade_out.finished.connect(on_fade_out_finished)
                fade_out.start()
            
            animate_image()
            if getattr(self, "has_load_more_button", False):
                allidx = ".."
            else:
                allidx = len(self.current_screenshots)
            # 更新信息栏内容
            game_name = self.current_screenshots[idx][1]
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.current_screenshots[idx][2]))
            info_bar.setText(
                f"{game_name} / {timestamp}  （{idx + 1}/{allidx}）    "
                "<a href='prev' style='color: white;'>← 左切换</a>    "
                "<a href='next' style='color: white;'>→ 右切换</a>     "
                "<a href='action1' style='color: white;'>Y/删除图片</a>    "
                "<a href='action2' style='color: white;'>X/打开图片位置</a>    "
                "<a href='action3' style='color: white;'>A,B/返回</a>"
            )
    
        # 将 load_preview 方法绑定到 is_fullscreen_preview 对象
        self.is_fullscreen_preview.load_preview = load_preview
        self.is_fullscreen_preview.load_preview(self.preview_index)
    
        def preview_key(event):
            key = event.key()
            if key == Qt.Key_Left:
                self.preview_index = (self.preview_index - 1) % len(self.current_screenshots)
                self.is_fullscreen_preview.load_preview(self.preview_index)
            elif key == Qt.Key_Right:
                self.preview_index = (self.preview_index + 1) % len(self.current_screenshots)
                self.is_fullscreen_preview.load_preview(self.preview_index)
            elif key in (Qt.Key_Escape, Qt.Key_A, Qt.Key_B):
                self.is_fullscreen_preview.close()
    
        self.is_fullscreen_preview.keyPressEvent = preview_key
        self.is_fullscreen_preview.raise_()

    def start_filter_mode(self, game_name=None):
        """弹出对话框选择游戏名进行筛选，支持直接传入游戏名（即使没有截图也能筛选）"""
        games = ["全部游戏"] + sorted({g for (_, g, _) in self.all_screenshots})
        if game_name is not None:
            # 只要不是全部游戏，都允许筛选（即使没有截图）
            if game_name == "全部游戏":
                self.filter_game_name = None
            else:
                self.filter_game_name = game_name
            game = game_name
            ok = True
        else:
            game, ok = QtWidgets.QInputDialog.getItem(self, "筛选游戏", "选择游戏：", games, 0, False)
            self.filter_game_name = game if ok and game != "全部游戏" else None
        if ok and game:
            self.game_name_label.setText(game)
            # 新增：同步按钮状态
            if "freeze_mode" in settings and game in settings["freeze_mode"]:
                self.btn_freeze.setText(f"冻结方式({settings['freeze_mode'][game]})")
            else:
                self.btn_freeze.setText("冻结方式(跟随全局)")
            if "custom_tools" in settings:
                for item in settings["custom_tools"]:
                    if item["name"] == game:
                        self.btn_tools.setText(f"附加工具启动({len(item['tools'])})")
                        break
                else:
                    self.btn_tools.setText("附加工具启动(0)")
            else:
                self.btn_tools.setText("附加工具启动(0)")
            if "custom_valid_apps" in settings and game in [item["name"] for item in settings["custom_valid_apps"]]:
                self.btn_custom_proc.setText("配置自定义进程(✔)")
            else:
                self.btn_custom_proc.setText("配置自定义进程(×)")
            if "on_mapping_clicked" in settings and game in settings["on_mapping_clicked"]:
                self.btn_mapping.setText("游玩时开启映射(✔)")
            else:
                self.btn_mapping.setText("游玩时开启映射(×)")
            # 新增：显示游玩时间
            play_time = settings.get("play_time", {}).get(game, 0)
            if play_time < 60:
                play_time_str = f"游玩时间：{play_time} 分钟"
            else:
                hours = play_time // 60
                minutes = play_time % 60
                play_time_str = f"游玩时间：{hours} 小时 {minutes} 分钟"
            self.play_time_label.setText(play_time_str)
            self.reload_screenshots()

    def clear_filter(self):
        self.filter_game_name = None
        self.game_name_label.setText("全部游戏")
        self.reload_screenshots()


    #def toggle_batch_mode(self):
    #    """切换批量多选模式"""
    #    if not self.batch_mode:
    #        # 进入多选模式
    #        self.batch_mode = True
    #        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
    #    else:
    #        # 退出多选模式
    #        self.batch_mode = False
    #        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    #        self.listWidget.clearSelection()
    def delete_selected_items(self):
        """删除选中的截图文件"""
        if hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview:
            # 使用 self.preview_index 获取当前放大显示的图片路径
            path = self.current_screenshots[self.preview_index][0]  # 获取当前预览图片的路径
            self.confirm_dialog = ConfirmDialog(f"确认删除选中的截图？\n{path}", scale_factor=self.scale_factor)
            if self.confirm_dialog.exec_():
                if os.path.exists(path):
                    os.remove(path)
                # 从列表中移除
                self.all_screenshots = [s for s in self.all_screenshots if s[0] != path]
                self.current_screenshots = [s for s in self.current_screenshots if s[0] != path]
                self.reload_screenshots()
                # 修正：如果没有截图了，关闭全屏预览
                if not self.current_screenshots:
                    if hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview:
                        self.is_fullscreen_preview.close()
                        self.is_fullscreen_preview = None
                else:
                    # 修正：删除后索引可能越界，重置为0
                    self.preview_index = min(self.preview_index, len(self.current_screenshots) - 1)
                    self.is_fullscreen_preview.load_preview(self.preview_index)
        else:
            items = self.listWidget.selectedItems()
            if not items:
                return
            # 弹出确认对话框
            for item in items:
                path = item.data(Qt.UserRole)  # 修复：从选中项获取路径
                self.confirm_dialog = ConfirmDialog(f"确认删除选中的截图？\n{path}", scale_factor=self.scale_factor)
                if self.confirm_dialog.exec_():
                    if os.path.exists(path):
                        os.remove(path)
                    row = self.listWidget.row(item)
                    self.listWidget.takeItem(row)
                    # 同时从数据列表移除
                    self.all_screenshots = [s for s in self.all_screenshots if s[0] != path]
                    self.current_screenshots = [s for s in self.current_screenshots if s[0] != path]
                    self.reload_screenshots()

    def safe_close(self):
        """安全关闭窗口，确保停止所有后台线程"""
        # 检查并停止 ScreenshotLoaderThread
        if hasattr(self, 'loader_thread') and self.loader_thread:
            if self.loader_thread.isRunning():
                self.loader_thread.stop()
        # 关闭窗口
        self.close()

    def closeEvent(self, event):
        """窗口关闭事件，确保停止所有后台线程并重置状态"""
        # 检查并停止 ScreenshotLoaderThread
        if hasattr(self, 'loader_thread') and self.loader_thread:
            if self.loader_thread.isRunning():
                self.loader_thread.stop()
        
        # 重置懒加载状态变量
        if hasattr(self, 'all_images_loaded'):
            del self.all_images_loaded
        if hasattr(self, 'is_loading_images'):
            del self.is_loading_images
        if hasattr(self, 'loaded_image_count'):
            del self.loaded_image_count
        
        # 调用父类的 closeEvent
        super().closeEvent(event)
class Overlay(QWidget):
    """全屏灰色覆盖层类"""
    def __init__(self, parent=None):
        super().__init__()
        # 作为独立的顶级窗口，不设置parent
        # 可使用 Qt.WindowTransparentForInput 让事件穿过覆盖层
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        # 使用纯色背景，确保可以看到
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.2);")  # 半透明灰色
        self.setGeometry(QApplication.primaryScreen().geometry())  # 覆盖全屏
        self.setWindowOpacity(0.0)  # 初始透明度为0
        self._fade_anim = None
        self._is_fading = False
    
    def fade_in(self, duration=180):
        """淡入效果"""
        if self._is_fading:
            return
        self._is_fading = True
        # 确保覆盖层显示
        self.show()
        # 确保覆盖层在对话框之下
        self.lower()
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(0.2)  # 半透明
        anim.finished.connect(lambda: setattr(self, '_is_fading', False))
        self._fade_anim = anim
        anim.start()
    
    def fade_out(self, duration=180):
        """淡出效果"""
        if self._is_fading:
            return
        self._is_fading = True
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(duration)
        anim.setStartValue(0.2)  # 半透明
        anim.setEndValue(0.0)
        def on_finished():
            self.hide()
            self._is_fading = False
        anim.finished.connect(on_finished)
        self._fade_anim = anim
        anim.start()

def get_dialog_qss(scale_factor):
    """根据缩放因子生成对话框样式表"""
    return f"""
            QDialog {{
                background-color: #2E2E2E;
                border: {int(5 * scale_factor)}px solid #4CAF50;
                border-radius: {int(8 * scale_factor)}px;
            }}
            QLabel {{
                font-size: {int(36 * scale_factor)}px;
                color: #FFFFFF;
                margin-bottom: {int(40 * scale_factor)}px;
                text-align: center;
            }}
            QPushButton {{
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: {int(20 * scale_factor)}px 0;
                font-size: {int(32 * scale_factor)}px;
                margin: 0;
                width: 100%;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
            QPushButton:pressed {{
                background-color: #388e3c;
            }}
            QVBoxLayout {{
                margin: {int(40 * scale_factor)}px;
                spacing: 0;
            }}
            QHBoxLayout {{
                justify-content: center;
                spacing: 0;
            }}
        """
class ConfirmDialog(QDialog):
    def __init__(self, variable1, scale_factor=1.0):
        super().__init__()
        self.variable1 = variable1
        self.scale_factor = scale_factor
        self.setWindowTitle("游戏确认")
        # 添加 Qt.WindowStaysOnTopHint 确保对话框在 Overlay 之上
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setFixedSize(int(800 * self.scale_factor), int(400 * self.scale_factor))  # 更新后的固定尺寸
        self.setStyleSheet(get_dialog_qss(self.scale_factor))
        # 初始透明度为 0，使用动画淡入
        try:
            self.setWindowOpacity(0.0)
        except Exception:
            pass
        self._fade_anim = None
        self._is_fading = False
        
        # 创建覆盖层
        self.overlay = Overlay(self)
        
        self.init_ui()
        self.current_index = 1  # 当前选中的按钮索引
        self.buttons = [self.cancel_button, self.confirm_button]  # 按钮列表
        self.last_input_time = 0  # 最后一次处理输入的时间
        self.input_delay = 300  # 去抖延迟时间，单位：毫秒
        self.ignore_input_until = 0  # 忽略输入的时间戳
        self.update_highlight()  # 初始化时更新高亮状态

    def init_ui(self):
        layout = QVBoxLayout()

        # 显示提示文本
        self.label = QLabel(self.variable1)
        self.label.setAlignment(Qt.AlignCenter)  # 设置文本居中
        if "※" in self.variable1:
            self.label.setStyleSheet(f"font-size: {24 * self.scale_factor}px; color: #FFFFFF; margin-bottom: 40px; text-align: center;")
        layout.addWidget(self.label)

        # 创建按钮区域
        button_layout = QHBoxLayout()

        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_action)
        button_layout.addWidget(self.cancel_button)

        # 确认按钮
        self.confirm_button = QPushButton("确认")
        self.confirm_button.clicked.connect(self.confirm_action)
        button_layout.addWidget(self.confirm_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def confirm_action(self): 
        print("用户点击了确认按钮")
        # 使用淡出动画后再 accept
        try:
            self.fade_out_and_accept()
        except Exception:
            self.accept()

    def cancel_action(self):
        print("用户点击了取消按钮")
        # 使用淡出动画后再 reject
        try:
            self.fade_out_and_reject()
        except Exception:
            self.reject()
    
    def showEvent(self, event):
        """窗口显示时的事件处理"""
        super().showEvent(event)
        try:
            self.fade_in()
        except Exception:
            pass
        self.ignore_input_until = pygame.time.get_ticks() + 350  # 打开窗口后1秒内忽略输入

    def fade_in(self, duration=180):
        try:
            if self._is_fading:
                return
            self._is_fading = True
            
            # 先淡入覆盖层
            self.overlay.fade_in(duration)
            
            # 显示对话框并确保在覆盖层之上
            self.show()
            self.raise_()
            
            # 再淡入对话框
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setDuration(duration)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.finished.connect(lambda: setattr(self, '_is_fading', False))
            self._fade_anim = anim
            anim.start()
        except Exception:
            pass

    def fade_out_and_accept(self, duration=180):
        try:
            if self._is_fading:
                return
            self._is_fading = True
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setDuration(duration)
            anim.setStartValue(self.windowOpacity())
            anim.setEndValue(0.0)
            def on_finished():
                try:
                    # 先淡出对话框，再淡出覆盖层
                    self.overlay.fade_out(duration)
                    self._is_fading = False
                    super(ConfirmDialog, self).accept()
                except Exception:
                    pass
            anim.finished.connect(on_finished)
            self._fade_anim = anim
            anim.start()
        except Exception:
            self.overlay.fade_out(duration)
            super(ConfirmDialog, self).accept()

    def fade_out_and_reject(self, duration=180):
        try:
            if self._is_fading:
                return
            self._is_fading = True
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setDuration(duration)
            anim.setStartValue(self.windowOpacity())
            anim.setEndValue(0.0)
            def on_finished():
                try:
                    # 先淡出对话框，再淡出覆盖层
                    self.overlay.fade_out(duration)
                    self._is_fading = False
                    super(ConfirmDialog, self).reject()
                except Exception:
                    pass
            anim.finished.connect(on_finished)
            self._fade_anim = anim
            anim.start()
        except Exception:
            self.overlay.fade_out(duration)
            super(ConfirmDialog, self).reject()

    def keyPressEvent(self, event):
        """处理键盘事件"""
        current_time = pygame.time.get_ticks()  # 获取当前时间（毫秒）
        # 如果在忽略输入的时间段内，则不处理
        if current_time < self.ignore_input_until:
            return
        # 如果按键间隔太短，则不处理
        if current_time - self.last_input_time < self.input_delay:
            return
        
        if event.key() == Qt.Key_Left:
            self.current_index = max(0, self.current_index - 1)
            self.update_highlight()
        elif event.key() == Qt.Key_Right:
            self.current_index = min(len(self.buttons) - 1, self.current_index + 1)
            self.update_highlight()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.buttons[self.current_index].click()
        # 更新最后一次按键时间
        self.last_input_time = current_time

    def handle_gamepad_input(self, action):
        """处理手柄输入"""
        current_time = pygame.time.get_ticks()  # 获取当前时间（毫秒）
        # 如果在忽略输入的时间段内，则不处理
        if current_time < self.ignore_input_until:
            return
        # 如果按键间隔太短，则不处理
        if current_time - self.last_input_time < self.input_delay:
            return
        if action == 'LEFT':
            self.current_index = max(0, self.current_index - 1)
            self.update_highlight()
        elif action == 'RIGHT':
            self.current_index = min(len(self.buttons) - 1, self.current_index + 1)
            self.update_highlight()
        elif action == 'A':
            self.buttons[self.current_index].click()
        elif action == 'B':
            self.cancel_action()
        # 更新最后一次按键时间
        self.last_input_time = current_time

    def update_highlight(self):
        """更新按钮高亮状态"""
        for index, button in enumerate(self.buttons):
            if index == self.current_index:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #45a049;
                        color: white;
                        border: 1px solid #93ffff;
                        padding: 20px 0;
                        font-size: 32px;
                        margin: 0;
                        width: 100%;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        padding: 20px 0;
                        font-size: 32px;
                        margin: 0;
                        width: 100%;
                    }
                """)
class LoadingDialog(QDialog):
    """通用加载窗口，显示一条提示信息并保持在最上层。"""
    def __init__(self, message="加载中...", scale_factor=1.0, parent=None):
        super().__init__(parent)
        self.message = message
        self.scale_factor = scale_factor
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        #self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(int(800 * self.scale_factor), int(400 * self.scale_factor))  # 更新后的固定尺寸
        # 初始透明度为 0，使用动画淡入
        try:
            self.setWindowOpacity(0.0)
        except Exception:
            pass
        self._fade_anim = None
        self._is_fading = False
        
        # 创建覆盖层
        self.overlay = Overlay(self)
        
        self.init_ui()

    def init_ui(self):
        # 使样式与 ConfirmDialog 对齐
        self.setStyleSheet(get_dialog_qss(self.scale_factor))
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.label = QLabel(self.message)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 24px; color: #FFFFFF;")
        layout.addWidget(self.label)
        # 添加无限加载进度条作为加载动画（不依赖外部资源）
        try:
            from PyQt5.QtWidgets import QProgressBar
            self.progress = QProgressBar()
            self.progress.setTextVisible(False)
            self.progress.setFixedHeight(int(10 * self.scale_factor))
            self.progress.setRange(0, 0)  # 不确定进度的忙碌指示器
            # 样式与对话框风格对齐
            self.progress.setStyleSheet("QProgressBar { background-color: rgba(255,255,255,0.06); border-radius: 5px; } QProgressBar::chunk { background-color: #4CAF50; }")
            layout.addWidget(self.progress)
        except Exception:
            self.progress = None
        self.setLayout(layout)

    def showEvent(self, event):
        try:
            # 在显示时启用等待光标并淡入
            try:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            except Exception:
                pass
            self.fade_in()
        except Exception:
            pass
        super().showEvent(event)

    def fade_in(self, duration=180):
        try:
            if self._is_fading:
                return
            self._is_fading = True
            
            # 先淡入覆盖层
            self.overlay.fade_in(duration)
            
            # 显示对话框并确保在覆盖层之上
            self.show()
            self.raise_()
            
            # 再淡入对话框
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setDuration(duration)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.finished.connect(lambda: setattr(self, '_is_fading', False))
            self._fade_anim = anim
            anim.start()
        except Exception:
            pass

    def fade_out_and_close(self, duration=180):
        try:
            # 如果已有动画，则先停止它，确保可以强制开始淡出
            try:
                if self._fade_anim is not None:
                    self._fade_anim.stop()
            except Exception:
                pass
            self._is_fading = True
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setDuration(duration)
            try:
                start_val = float(self.windowOpacity())
            except Exception:
                start_val = 1.0
            anim.setStartValue(start_val)
            anim.setEndValue(0.0)
            def on_finished():
                try:
                    # 先淡出对话框，再淡出覆盖层
                    self.overlay.fade_out(duration)
                    self._is_fading = False
                    try:
                        QApplication.restoreOverrideCursor()
                    except Exception:
                        pass
                    super(LoadingDialog, self).close()
                except Exception:
                    pass
            anim.finished.connect(on_finished)
            self._fade_anim = anim
            anim.start()
        except Exception:
            try:
                # 淡出覆盖层
                self.overlay.fade_out(duration)
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            super(LoadingDialog, self).close()

    def close(self):
        # 强制使用淡出动画再真正关闭（停止任何正在进行的淡入）
        try:
            self.fade_out_and_close()
        except Exception:
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            super(LoadingDialog, self).close()

    def closeEvent(self, event):
        try:
            QApplication.restoreOverrideCursor()
        except Exception:
            pass
        super().closeEvent(event)

    def setMessage(self, msg):
        self.message = msg
        self.label.setText(msg)


class LaunchOverlay(QWidget):
    """启动游戏的悬浮窗"""
    class _ProcessCheckThread(QThread):
        """在后台检查指定可执行文件是否运行并返回内存使用情况，避免阻塞主线程。"""
        status_signal = pyqtSignal(bool, float)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.game_path = None
            self._running = True

        def run(self):
            while getattr(self, '_running', True):
                game_running = False
                memory_mb = 0.0
                try:
                    gp = self.game_path
                    if gp:
                        for process in psutil.process_iter(['pid', 'exe', 'memory_info']):
                            try:
                                exe = process.info.get('exe') or ''
                                if exe and exe.lower() == gp.lower():
                                    game_running = True
                                    memory_info = process.info.get('memory_info')
                                    if memory_info:
                                        memory_mb = memory_info.rss / (1024 * 1024)
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                continue
                except Exception:
                    pass

                try:
                    self.status_signal.emit(game_running, memory_mb)
                except Exception:
                    pass

                # sleep in short increments so stop() can be responsive
                for _ in range(5):
                    if not getattr(self, '_running', False):
                        break
                    QThread.msleep(100)

        def stop(self):
            self._running = False

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("launchOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)        
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.bg = QWidget(self)
        self.bg.setGeometry(0, 0, self.parent.width(), self.parent.height())
        self.bg.setAttribute(Qt.WA_StyledBackground, True)
        self.bg.setStyleSheet("background-color: rgba(46,46,46,230);")
        self.bg.show()
        self.bg.raise_()
        
        # 设置悬浮窗大小为父窗口大小
        self.setFixedSize(self.parent.size())
        
        # 使用绝对定位，不使用布局
        #self.setLayout(None) （会卡住）
        
        # 创建图片标签（用于封面动画）
        self.overlay_image = QLabel(self)
        self.overlay_image.setAlignment(Qt.AlignCenter)
        self.overlay_image.setScaledContents(False)
        self.overlay_image.hide()
        
        # 创建背景图片标签（用于放大后的背景）
        self.overlay_bg_image = QLabel(self)
        self.overlay_bg_image.setAlignment(Qt.AlignCenter)
        self.overlay_bg_image.setScaledContents(True)
        self.overlay_bg_image.hide()
        
        # 创建文本标签（启动文字）- 添加文字阴影效果
        self.overlay_text = QLabel(self)
        self.overlay_text.setAlignment(Qt.AlignCenter)
        # 改进文字样式：更大字体、文字阴影、更好的字体
        self.overlay_text.setStyleSheet(f"""
            font-size: {int(42 * self.parent.scale_factor)}px; 
            color: #EEEEEE; 
            background: transparent;
        """)
        # 添加文字阴影效果
        text_shadow = QtWidgets.QGraphicsDropShadowEffect(self.overlay_text)
        text_shadow.setBlurRadius(15)
        text_shadow.setXOffset(2)
        text_shadow.setYOffset(2)
        text_shadow.setColor(QColor(0, 0, 0, 180))
        self.overlay_text.setGraphicsEffect(text_shadow)
        self.overlay_text.hide()
        
        # 创建加载条 - 改进视觉效果
        self.overlay_progress = QProgressBar(self)
        self.overlay_progress.setTextVisible(False)
        progress_height = int(8 * self.parent.scale_factor)
        self.overlay_progress.setFixedHeight(progress_height)
        self.overlay_progress.setRange(0, 0)  # 不确定进度的忙碌指示器
        # 改进加载条样式：渐变、发光效果
        self.overlay_progress.setStyleSheet("""
            QProgressBar { 
                background-color: rgba(30, 30, 30, 0.8); 
                border: 2px solid rgba(100, 100, 100, 0.3);
                border-radius: 4px; 
            } 
            QProgressBar::chunk { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50,
                    stop:0.5 #66BB6A,
                    stop:1 #4CAF50);
                border-radius: 2px;
            }
        """)
        # 添加发光效果
        progress_glow = QtWidgets.QGraphicsDropShadowEffect(self.overlay_progress)
        progress_glow.setBlurRadius(10)
        progress_glow.setXOffset(0)
        progress_glow.setYOffset(0)
        progress_glow.setColor(QColor(76, 175, 80, 100))
        self.overlay_progress.setGraphicsEffect(progress_glow)
        self.overlay_progress.hide()
        
        # 创建状态标签（右下角显示进程状态）- 添加背景和阴影
        self.overlay_status = QLabel(self)
        self.overlay_status.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        # 改进状态标签样式：半透明背景、圆角、阴影
        self.overlay_status.setStyleSheet(f"""
            font-size: {int(18 * self.parent.scale_factor)}px; 
            font-weight: 500;
            color: #E0E0E0; 
            background-color: rgba(20, 20, 20, 0.7);
            border-radius: {int(8 * self.parent.scale_factor)}px;
            padding: {int(12 * self.parent.scale_factor)}px {int(16 * self.parent.scale_factor)}px;
        """)
        # 添加状态标签阴影
        status_shadow = QtWidgets.QGraphicsDropShadowEffect(self.overlay_status)
        status_shadow.setBlurRadius(8)
        status_shadow.setXOffset(0)
        status_shadow.setYOffset(2)
        status_shadow.setColor(QColor(0, 0, 0, 150))
        self.overlay_status.setGraphicsEffect(status_shadow)
        self.overlay_status.hide()
        
        # 动画相关变量
        self.launch_animations = []
        self.status_timer = None
        self.focus_check_timer = None
        self._process_check_thread = None
        self.current_game_name = None
        self.current_game_path = None
        
        # 初始时隐藏
        self.hide()
    
    def mousePressEvent(self, event):
        """点击悬浮窗时隐藏"""
        self.hide()
        self._stop_launch_animations()
    
    def show_launch_window(self, game_name, image_path):
        """显示启动游戏的悬浮窗"""
        # 停止之前的动画和定时器
        self._stop_launch_animations()
        
        # 保存游戏信息
        self.current_game_name = game_name
        # 查找游戏路径
        self.current_game_path = None
        for app in valid_apps:
            if app["name"] == game_name:
                self.current_game_path = app["path"]
                break
        
        # 重置所有组件状态
        self.setWindowOpacity(0.0)
        self.overlay_image.hide()
        self.overlay_bg_image.hide()
        self.overlay_text.hide()
        self.overlay_progress.hide()
        self.overlay_status.hide()
        
        # 获取父窗口大小
        parent_size = self.parent.size()
        parent_width = parent_size.width()
        parent_height = parent_size.height()
        
        # 更新悬浮窗大小
        self.setFixedSize(parent_width, parent_height)
        
        # 获取当前按钮位置（光标位置，参考4328行）
        start_pos = None
        if hasattr(self.parent, 'buttons') and self.parent.buttons and hasattr(self.parent, 'current_index'):
            try:
                current_button = self.parent.buttons[self.parent.current_index]
                # 获取按钮在父窗口中的位置
                button_pos = current_button.mapTo(self.parent, QPoint(0, 0))
                button_size = current_button.size()
                start_pos = QPoint(
                    button_pos.x() + button_size.width() // 2,
                    button_pos.y() + button_size.height() // 2
                )
            except Exception:
                pass
        
        # 如果没有找到按钮位置，使用屏幕中心
        if start_pos is None:
            start_pos = QPoint(parent_width // 2, parent_height // 2)
        
        # 目标位置（屏幕中心）
        target_x = parent_width // 2
        target_y = parent_height // 2
        
        # 根据图片比例计算封面尺寸
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # 读取原始宽高，按比例缩放，目标宽度 400*scale_factor
                cover_width = int(400 * self.parent.scale_factor)
                cover_height = int(pixmap.height() * cover_width / pixmap.width())
            else:
                cover_width = int(400 * self.parent.scale_factor)
                cover_height = int(533 * self.parent.scale_factor)
        else:
            cover_width = int(400 * self.parent.scale_factor)
            cover_height = int(533 * self.parent.scale_factor)
        
        # 加载并设置封面图片
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(
                cover_width,
                cover_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.overlay_image.setPixmap(scaled_pixmap)
            # 设置初始位置和大小
            self.overlay_image.setGeometry(
                start_pos.x() - cover_width // 2,
                start_pos.y() - cover_height // 2,
                cover_width,
                cover_height
            )
            self.overlay_image.show()
        else:
            self.overlay_image.hide()
        
        # 设置文本
        self.overlay_text.setText(f"正在启动 {game_name}")
        text_width = int(1600 * self.parent.scale_factor)
        text_height = int(50 * self.parent.scale_factor)
        # 初始位置在屏幕下方中央
        self.overlay_text.setGeometry(
            (parent_width - text_width) // 2,
            parent_height - text_height - int(100 * self.parent.scale_factor),
            text_width,
            text_height
        )
        self.overlay_text.hide()
        
        # 设置加载条位置（底部）
        progress_width = int(800 * self.parent.scale_factor)
        progress_height = int(10 * self.parent.scale_factor)
        self.overlay_progress.setGeometry(
            (parent_width - progress_width) // 2,
            parent_height - progress_height - int(50 * self.parent.scale_factor),
            progress_width,
            progress_height
        )
        
        # 设置状态标签位置（右下角）
        status_width = int(400 * self.parent.scale_factor)
        status_height = int(60 * self.parent.scale_factor)
        self.overlay_status.setGeometry(
            parent_width - status_width - int(20 * self.parent.scale_factor),
            parent_height - status_height - int(20 * self.parent.scale_factor),
            status_width,
            status_height
        )
        
        # 将悬浮窗置于最上层并显示
        self.raise_()
        self.show()
        
        # 第一阶段：淡入悬浮窗
        self.overlay_text.setAlignment(Qt.AlignCenter)
        fade_in = QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(300)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        self.launch_animations.append(fade_in)
        
        def on_fade_in_finished():
            # 第二阶段：封面从光标位置移动到中央，同时添加缩放和变暗效果
            if self.overlay_image.isVisible():
                # 位置动画
                move_anim = QPropertyAnimation(self.overlay_image, b"pos")
                move_anim.setDuration(700)
                move_anim.setStartValue(QPoint(
                    start_pos.x() - cover_width // 2,
                    start_pos.y() - cover_height // 2
                ))
                move_anim.setEndValue(QPoint(
                    target_x - cover_width // 2,
                    target_y - cover_height // 2
                ))
                try:
                    from PyQt5.QtCore import QEasingCurve
                    move_anim.setEasingCurve(QEasingCurve.OutCubic)
                except Exception:
                    pass
                self.launch_animations.append(move_anim)
                
                # 缩放动画：从稍小到正常大小，增加层次感
                scale_anim = QPropertyAnimation(self.overlay_image, b"geometry")
                scale_anim.setDuration(700)
                start_rect = QRect(
                    start_pos.x() - cover_width // 2,
                    start_pos.y() - cover_height // 2,
                    int(cover_width * 0.8),  # 起始时稍小
                    int(cover_height * 0.8)
                )
                end_rect = QRect(
                    target_x - cover_width // 2,
                    target_y - cover_height // 2,
                    cover_width,
                    cover_height
                )
                scale_anim.setStartValue(start_rect)
                scale_anim.setEndValue(end_rect)
                try:
                    from PyQt5.QtCore import QEasingCurve
                    scale_anim.setEasingCurve(QEasingCurve.OutCubic)
                except Exception:
                    pass
                self.launch_animations.append(scale_anim)
                
                # 变暗效果：从完全不透明到半透明
                if not hasattr(self.overlay_image, 'opacity_effect'):
                    opacity_effect = QtWidgets.QGraphicsOpacityEffect(self.overlay_image)
                    self.overlay_image.setGraphicsEffect(opacity_effect)
                    self.overlay_image.opacity_effect = opacity_effect
                else:
                    opacity_effect = self.overlay_image.opacity_effect
                    opacity_effect.setOpacity(1.0)  # 重置为完全不透明
                
                dim_anim = QPropertyAnimation(opacity_effect, b"opacity")
                dim_anim.setDuration(700)
                dim_anim.setStartValue(1.0)
                dim_anim.setEndValue(0.6)  # 变暗到60%透明度，保持更好的可见性
                try:
                    from PyQt5.QtCore import QEasingCurve
                    dim_anim.setEasingCurve(QEasingCurve.OutCubic)
                except Exception:
                    pass
                self.launch_animations.append(dim_anim)
                
                # 同时启动所有动画
                move_anim.start()
                scale_anim.start()
                dim_anim.start()
                
                def on_move_finished():
                    # 第三阶段：文字淡入，同时从下方滑入
                    self.overlay_text.show()
                    
                    # 文字淡入效果
                    text_effect = QtWidgets.QGraphicsOpacityEffect(self.overlay_text)
                    self.overlay_text.setGraphicsEffect(text_effect)
                    text_fade_in = QPropertyAnimation(text_effect, b"opacity")
                    text_fade_in.setDuration(500)
                    text_fade_in.setStartValue(0.0)
                    text_fade_in.setEndValue(1.0)
                    try:
                        from PyQt5.QtCore import QEasingCurve
                        text_fade_in.setEasingCurve(QEasingCurve.OutCubic)
                    except Exception:
                        pass
                    self.launch_animations.append(text_fade_in)
                    
                    # 文字位置动画：从下方滑入
                    text_start_y = parent_height
                    text_end_y = parent_height - text_height - int(100 * self.parent.scale_factor)
                    text_pos_anim = QPropertyAnimation(self.overlay_text, b"pos")
                    text_pos_anim.setDuration(500)
                    text_pos_anim.setStartValue(QPoint(
                        (parent_width - text_width) // 2,
                        text_start_y
                    ))
                    text_pos_anim.setEndValue(QPoint(
                        (parent_width - text_width) // 2,
                        text_end_y
                    ))
                    try:
                        from PyQt5.QtCore import QEasingCurve
                        text_pos_anim.setEasingCurve(QEasingCurve.OutCubic)
                    except Exception:
                        pass
                    self.launch_animations.append(text_pos_anim)
                    
                    def on_text_fade_in_finished():
                        # 停留1秒后进入第四阶段
                        QTimer.singleShot(800, start_phase4)
                    
                    text_fade_in.finished.connect(on_text_fade_in_finished)
                    text_fade_in.start()
                    text_pos_anim.start()
                
                # 使用scale_anim的完成信号，因为它是最后一个动画
                scale_anim.finished.connect(on_move_finished)
            else:
                # 如果没有图片，直接显示文字
                self.overlay_text.show()
                text_effect = QtWidgets.QGraphicsOpacityEffect(self.overlay_text)
                self.overlay_text.setGraphicsEffect(text_effect)
                text_fade_in = QPropertyAnimation(text_effect, b"opacity")
                text_fade_in.setDuration(400)
                text_fade_in.setStartValue(0.0)
                text_fade_in.setEndValue(1.0)
                self.launch_animations.append(text_fade_in)
                
                def on_text_fade_in_finished():
                    QTimer.singleShot(1000, start_phase4)
                
                text_fade_in.finished.connect(on_text_fade_in_finished)
                text_fade_in.start()
        
        fade_in.finished.connect(on_fade_in_finished)
        fade_in.start()
        
        def start_phase4():
            """第四阶段：图片变暗放大做背景，文字移动到左上角，显示加载条和状态"""
            # 隐藏原封面图片（淡出效果）
            if self.overlay_image.isVisible():
                if hasattr(self.overlay_image, 'opacity_effect'):
                    fade_out = QPropertyAnimation(self.overlay_image.opacity_effect, b"opacity")
                    fade_out.setDuration(400)
                    fade_out.setStartValue(self.overlay_image.opacity_effect.opacity())
                    fade_out.setEndValue(0.0)
                    fade_out.finished.connect(lambda: self.overlay_image.hide())
                    fade_out.start()
                    self.launch_animations.append(fade_out)
                else:
                    self.overlay_image.hide()
            
            # 创建背景图片（变暗放大）- 添加渐变遮罩和模糊效果
            if image_path and os.path.exists(image_path):
                bg_pixmap = QPixmap(image_path)
                # 放大到覆盖整个屏幕宽度，稍微放大一点以支持模糊
                scale_factor = 1.1
                bg_scaled = bg_pixmap.scaled(
                    int(parent_width * scale_factor),
                    int(parent_width * bg_pixmap.height() / bg_pixmap.width() * scale_factor),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                
                # 创建渐变遮罩效果（从顶部到底部逐渐变暗）
                dark_pixmap = QPixmap(bg_scaled.size())
                dark_pixmap.fill(Qt.transparent)
                painter = QPainter(dark_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # 先绘制原图
                painter.drawPixmap(0, 0, bg_scaled)
                
                # 添加渐变遮罩（从透明到半透明黑色）
                gradient = QColor(0, 0, 0, 0)
                gradient_end = QColor(0, 0, 0, 230)
                linear_gradient = QLinearGradient(0, 0, 0, dark_pixmap.height())
                linear_gradient.setColorAt(0, gradient)
                linear_gradient.setColorAt(0.3, QColor(0, 0, 0, 100))
                linear_gradient.setColorAt(1, gradient_end)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                painter.fillRect(dark_pixmap.rect(), linear_gradient)
                painter.end()
                
                self.overlay_bg_image.setPixmap(dark_pixmap)
                # 居中显示，稍微偏移以创建模糊效果
                bg_x = int((parent_width - dark_pixmap.width()) / 2)
                bg_y = int((parent_height - dark_pixmap.height()) / 2)
                self.overlay_bg_image.setGeometry(bg_x, bg_y, dark_pixmap.width(), dark_pixmap.height())
                
                # 添加模糊效果
                blur_effect = QtWidgets.QGraphicsBlurEffect(self.overlay_bg_image)
                blur_effect.setBlurRadius(20)
                self.overlay_bg_image.setGraphicsEffect(blur_effect)
                
                # 淡入显示背景
                bg_opacity = QtWidgets.QGraphicsOpacityEffect(self.overlay_bg_image)
                self.overlay_bg_image.setGraphicsEffect(bg_opacity)
                bg_opacity.setOpacity(0.0)
                self.overlay_bg_image.show()
                
                bg_fade_in = QPropertyAnimation(bg_opacity, b"opacity")
                bg_fade_in.setDuration(600)
                bg_fade_in.setStartValue(0.0)
                bg_fade_in.setEndValue(1.0)
                try:
                    from PyQt5.QtCore import QEasingCurve
                    bg_fade_in.setEasingCurve(QEasingCurve.InOutCubic)
                except Exception:
                    pass
                bg_fade_in.start()
                self.launch_animations.append(bg_fade_in)
            
            # 文字移动到左上角
            text_effect = self.overlay_text.graphicsEffect()
            if text_effect:
                self.overlay_text.setGraphicsEffect(None)
            
            # 文字移动到左上角，同时缩小字体
            text_move = QPropertyAnimation(self.overlay_text, b"pos")
            text_move.setDuration(200)
            text_move.setStartValue(self.overlay_text.pos())
            text_move.setEndValue(QPoint(
                int(20 * self.parent.scale_factor),
                int(20 * self.parent.scale_factor)
            ))
            try:
                from PyQt5.QtCore import QEasingCurve
                text_move.setEasingCurve(QEasingCurve.InOutCubic)
            except Exception:
                pass
            self.launch_animations.append(text_move)
            # 去掉“正在启动”前缀，仅保留游戏名称
            current_text = self.overlay_text.text()
            if current_text.startswith("正在启动 "):
                current_text = current_text[5:]  # 去掉前5个字符
                self.overlay_text.setText(current_text)
                # 动画结束后设置为左对齐
                self.overlay_text.setAlignment(Qt.AlignLeft)

            font_size = int(14 * self.parent.scale_factor)
            self.overlay_text.setFont(QFont(self.overlay_text.font().family(), font_size))
            
            def on_text_move_finished():
                # 显示加载条和状态（带淡入动画）
                # 将加载条放在状态标签底部（相对定位并做边界检测）
                status_geom = self.overlay_status.geometry()
                prog_w = max(int(300 * self.parent.scale_factor), status_geom.width())
                prog_h = max(int(8 * self.parent.scale_factor), self.overlay_progress.height() if self.overlay_progress else int(8 * self.parent.scale_factor))
                prog_x = status_geom.x() + max(0, (status_geom.width() - prog_w) // 2)
                prog_y = status_geom.y() + status_geom.height() + int(8 * self.parent.scale_factor)

                # 如果超出屏幕底部则向上调整到边界内
                if prog_y + prog_h > parent_height - int(10 * self.parent.scale_factor):
                    prog_y = parent_height - prog_h - int(10 * self.parent.scale_factor)

                # 应用几何并淡入显示加载条
                self.overlay_progress.setGeometry(prog_x, prog_y, prog_w, prog_h)
                progress_opacity = QtWidgets.QGraphicsOpacityEffect(self.overlay_progress)
                self.overlay_progress.setGraphicsEffect(progress_opacity)
                progress_opacity.setOpacity(0.0)
                self.overlay_progress.show()

                progress_fade = QPropertyAnimation(progress_opacity, b"opacity")
                progress_fade.setDuration(400)
                progress_fade.setStartValue(0.0)
                progress_fade.setEndValue(1.0)
                progress_fade.start()
                self.launch_animations.append(progress_fade)

                # 状态标签淡入（保持原位）
                status_opacity = QtWidgets.QGraphicsOpacityEffect(self.overlay_status)
                self.overlay_status.setGraphicsEffect(status_opacity)
                status_opacity.setOpacity(0.0)
                self.overlay_status.show()

                status_fade = QPropertyAnimation(status_opacity, b"opacity")
                status_fade.setDuration(400)
                status_fade.setStartValue(0.0)
                status_fade.setEndValue(1.0)
                status_fade.start()
                self.launch_animations.append(status_fade)
                
                # 开始更新状态
                self._start_status_update()
                # 开始焦点监听
                self._start_focus_monitoring()
            
            text_move.finished.connect(on_text_move_finished)
            text_move.start()
        
        # 保持窗口在最上层
        self.selection_count = 0
        def keep_on_top():
            if self.isVisible():
                self.raise_()
                self.selection_count += 1
                if self.selection_count < 200:  # 持续约30秒
                    QTimer.singleShot(150, keep_on_top)
        
        QTimer.singleShot(150, keep_on_top)
    
    def _stop_launch_animations(self):
        """停止所有启动动画"""
        for anim in self.launch_animations:
            try:
                anim.stop()
            except Exception:
                pass
        self.launch_animations.clear()
        
        if self.status_timer:
            self.status_timer.stop()
            self.status_timer = None
        
        if self.focus_check_timer:
            self.focus_check_timer.stop()
            self.focus_check_timer = None
        # 停止后台进程检查线程（如果存在）
        if getattr(self, '_process_check_thread', None):
            try:
                self._process_check_thread.stop()
                self._process_check_thread.wait(500)
            except Exception:
                pass
            self._process_check_thread = None
    
    def _start_status_update(self):
        """开始更新游戏进程状态"""
        if not self.current_game_path:
            return

        # 如果已有后台检查线程，先停止它
        if getattr(self, '_process_check_thread', None):
            try:
                self._process_check_thread.stop()
                self._process_check_thread.wait(500)
            except Exception:
                pass
            self._process_check_thread = None

        # 启动后台线程进行进程检查，避免在主线程中使用 psutil 导致卡顿
        self._process_check_thread = self._ProcessCheckThread(self)
        self._process_check_thread.game_path = self.current_game_path

        def on_status(game_running, memory_mb):
            if not self.isVisible():
                return
            try:
                status_text = f"运行中 | 内存: {memory_mb:.0f} MB" if game_running else "正在启动"
                self.overlay_status.setText(status_text)
            except Exception:
                self.overlay_status.setText("状态未知")

        self._process_check_thread.status_signal.connect(on_status)
        self._process_check_thread.start()
    
    def _start_focus_monitoring(self):
        """开始监听焦点变化"""
        self.last_focus_hwnd = GSHWND  # 初始化为GSHWND，因为悬浮窗显示时焦点应该在GSHWND
        
        def check_focus():
            if not self.isVisible():
                if self.focus_check_timer:
                    self.focus_check_timer.stop()
                return
            
            try:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    # 检查是否是全屏游戏窗口（不是GSHWND）
                    if hwnd != GSHWND:
                        # 焦点切换到其他窗口（全屏游戏窗口）
                        # 如果之前焦点在GSHWND，现在切换到了全屏窗口，关闭悬浮窗
                        if self.last_focus_hwnd == GSHWND:
                            # 焦点从GSHWND切换到全屏窗口，关闭悬浮窗
                            self.hide()
                            self._stop_launch_animations()
                            return
                        
                        # 焦点在其他窗口，隐藏加载条和状态文字
                        self.overlay_progress.hide()
                        self.overlay_status.hide()
                        self.last_focus_hwnd = hwnd
                    else:
                        # 焦点在GSHWND
                        # 如果之前焦点不在GSHWND，现在切换回来了，关闭悬浮窗
                        if self.last_focus_hwnd is not None and self.last_focus_hwnd != GSHWND:
                            # 焦点从其他窗口切换回GSHWND，关闭悬浮窗
                            self.hide()
                            self._stop_launch_animations()
                            return
                        
                        # 显示加载条和状态
                        if self.current_game_path:
                            self.overlay_progress.show()
                            self.overlay_status.show()
                        self.last_focus_hwnd = hwnd
            except Exception:
                pass
        
        # 每0.2秒检查一次焦点
        self.focus_check_timer = QTimer(self)
        self.focus_check_timer.timeout.connect(check_focus)
        self.focus_check_timer.start(200)


class QuickStreamAppAddThread(QThread):
    finished_signal = pyqtSignal()

    def __init__(self, args=None, parent=None):
        super().__init__(parent)
        self.args = args if args else []


    def run(self):
        # 支持传入启动参数
        # 检查 QuickStreamAppAdd.exe 是否存在
        if not os.path.exists("QuickStreamAppAdd.exe"):
            print("QuickStreamAppAdd.exe 未找到，无法执行。")
            # 弹窗告知用户
            QMessageBox.warning(None, "提示", "未找到 QuickStreamAppAdd.exe，无法执行相关操作。")
            self.finished_signal.emit()
            return
        cmd = ["QuickStreamAppAdd.exe"] + self.args
        try:
            proc = subprocess.Popen(cmd, shell=True)
            proc.wait()
            print("QuickStreamAppAdd.exe 已结束")
        except Exception as e:
            print(f"QuickStreamAppAddThread error: {e}")
        self.finished_signal.emit()

class GameSelector(QWidget): 
    def __init__(self):
        global play_reload, GSHWND
        super().__init__()
        self.back_start_pressed_time = None  # 初始化按键按下时间
        self.back_start_action = set()
        self.is_mouse_simulation_running = False
        self.ignore_input_until = 0  # 初始化防抖时间戳
        self.current_section = 0  # 0=游戏选择区域，1=控制按钮区域
        GSHWND = int(self.winId())
        self.setWindowIcon(QIcon('./_internal/fav.ico'))
        #if STARTUP:
        #    self.setWindowOpacity(0.0)  # 设置窗口透明度为全透明
        self.more_section = 0  # 0=主页面，1=更多页面
        self.setWindowTitle("游戏选择器")
        QApplication.setFont(QFont("Microsoft YaHei"))  # 设置字体为微软雅黑
        # 获取屏幕的分辨率
        screen = QDesktopWidget().screenGeometry()
        # 设置窗口大小为屏幕分辨率
        self.resize(1, 1)  # 初始设置为1x1，后续会调整为全屏
        self.setWindowFlags(Qt.FramelessWindowHint)  # 全屏无边框
        self.setStyleSheet("background-color: #1e1e1e;")  # 设置深灰背景色
        self.killexplorer = settings.get("killexplorer", False)
        self.freeze = settings.get("freeze", False)
        self.freezeapp = None
        self.winTaskbar = TaskbarWindow()
        if self.killexplorer == True and STARTUP == False:
            self.wintaskbarshow()
        self.showFullScreen()
        # 确保窗口捕获焦点
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.activateWindow()
        self.raise_()
        if STARTUP:
            hwnd = int(self.winId())
            ctypes.windll.user32.ShowWindow(hwnd, 0) # 0=SW_HIDE
        self.resize(screen.width(), screen.height()) # 设置窗口大小为屏幕分辨率
        
        # 初始化缩放因子
        self.scale_factor = 1.0  # 初始缩放因子，将由 resizeEvent / 初始化逻辑更新
        self.scale_factor2 = self.scale_factor * 2  # 用于按钮和图像的缩放因数
        
        # 缩放参数（事件驱动模式）
        self.base_height = 1080
        self.min_scale = 0.45
        self.max_scale = 2.5
        self.precision = 2
        self.threshold = 0.01

        # 立即根据屏幕高度计算并应用初始缩放，避免启动时因 widget 几何尚未准备好导致尺寸异常
        try:
            raw = float(screen.height()) / float(self.base_height)
            initial_scale = round(raw, self.precision)
            initial_scale = max(self.min_scale, min(initial_scale, self.max_scale))
            # 使用事件驱动更新一次初始缩放
            try:
                self.on_scale_factor_updated(initial_scale)
            except Exception:
                self.scale_factor = initial_scale
                self.scale_factor2 = self.scale_factor * 2
        except Exception:
            pass
        # 游戏索引和布局
        self.player = {}
        self.current_index = 0  # 从第一个按钮开始
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(int(20 * self.scale_factor))  # 设置按钮之间的间距


        # 从设置中读取 row_count，如果不存在则使用默认值
        self.row_count = settings.get("row_count", 6)  # 每行显示的按钮数量

        # 从设置中读取主页游戏数量，如果不存在则使用默认值
        self.buttonsindexset = settings.get("buttonsindexset", 4)

        # 创建顶部布局
        self.top_layout = QHBoxLayout()
        self.top_layout.setContentsMargins(int(20 * self.scale_factor), 0, int(20 * self.scale_factor), 0)  # 添加左右边距

        # 创建左侧布局（用于"更多"按钮）
        self.left_layout = QHBoxLayout()
        self.left_layout.setAlignment(Qt.AlignLeft)

        # 创建中间布局（用于游戏标题）
        self.center_layout = QHBoxLayout()
        self.center_layout.setAlignment(Qt.AlignCenter)

        # 创建右侧布局（用于收藏和退出按钮）
        self.right_layout = QHBoxLayout()
        self.right_layout.setAlignment(Qt.AlignRight)

        # 创建更多按钮
        self.more_button = QPushButton("工具")
        self.more_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.more_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: {int(2 * self.scale_factor)}px solid #888888;
                color: white;
                font-size: {int(16 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor)}px solid #555555;
            }}
        """)
        self.more_button.clicked.connect(self.show_more_window)

        # 添加收藏按钮
        self.favorite_button = QPushButton("收藏")
        self.favorite_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.favorite_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: {int(2 * self.scale_factor)}px solid #888888;
                color: white;
                font-size: {int(16 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor)}px solid #555555;
            }}
        """)
        self.favorite_button.clicked.connect(self.toggle_favorite)

        # 创建退出按钮
        self.quit_button = QPushButton("最小化")
        self.quit_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.quit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: {int(2 * self.scale_factor)}px solid #888888;
                color: white;
                font-size: {int(16 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor)}px solid #555555;
            }}
        """)
        self.quit_button.clicked.connect(self.exitbutton)

        # 创建设置按钮
        self.settings_button = QPushButton("设置")
        self.settings_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.settings_button.setFont(QFont("Microsoft YaHei", 40))
        self.settings_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: {int(2 * self.scale_factor)}px solid #888888;
                color: white;
                font-size: {int(16 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor)}px solid #555555;
            }}
        """)
        self.settings_button.clicked.connect(self.show_settings_window)

        # 新增：截图按钮
        self.screenshot_button = QPushButton("游戏详情")
        self.screenshot_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
        self.screenshot_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; 
                border-radius: {int(20 * self.scale_factor)}px; 
                border: {int(2 * self.scale_factor)}px solid #888888;
                color: white;
                font-size: {int(16 * self.scale_factor)}px;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor)}px solid #555555;
            }}
        """)
        self.screenshot_button.clicked.connect(self.open_selected_game_screenshot)

        # 创建游戏标题标签
        sorted_games = self.sort_games()
        if sorted_games:  # 检查是否有游戏
            self.game_name_label = QLabel(sorted_games[self.current_index]["name"])
        else:
            self.game_name_label = QLabel("没有找到游戏")  # 显示提示信息
        
        self.game_name_label.setAlignment(Qt.AlignCenter)
        self.game_name_label.setStyleSheet(f"""
            QLabel {{
                color: #1e1e1e;
                font-size: {int(20 * self.scale_factor)}px;
                font-weight: bold;
                padding: 0 {int(20 * self.scale_factor)}px;
            }}
        """)
        # 创建时间显示标签
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {int(25 * self.scale_factor)}px;
                padding-top: {int(10 * self.scale_factor)}px;
                padding-bottom: {int(10 * self.scale_factor)}px;
                padding-right: {int(20 * self.scale_factor)}px;
            }}
        """)
        self.update_time()  # 初始化时间显示
        self.right_layout.addWidget(self.time_label)  # 添加到右侧布局，在 quit_button 之前
        # 添加收藏按钮到左侧布局
        self.right_layout.addWidget(self.favorite_button)
        # 将按钮和标签添加到对应的布局
        self.left_layout.addWidget(self.more_button)
        self.center_layout.addWidget(self.game_name_label)
        self.right_layout.addWidget(self.quit_button)

        # 设置定时器每秒更新一次时间
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)
        # 将三个布局添加到顶部布局
        self.top_layout.addLayout(self.left_layout, 1)  # stretch=1
        self.top_layout.addLayout(self.center_layout, 2)  # stretch=2，让中间部分占据更多空间
        self.top_layout.addLayout(self.right_layout, 1)  # stretch=1

        # 创建悬浮窗
        self.floating_window = None
        # 添加游戏按钮
        self.buttons = []
        if sorted_games:  # 只在有游戏时添加按钮
            for index, game in enumerate(sorted_games[:self.buttonsindexset]):
                button = self.create_game_button(game, index)
                #self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)    #由self.buttonsindexset和sorted_games的长度决定是否要添加更多按钮（暂时不做
                self.grid_layout.addWidget(button, 0, index)
                self.buttons.append(button)
            
            # 添加"更多"按钮
            more_button = QPushButton("🟦🟦\n🟦🟦")
            more_button.setFont(QFont("Microsoft YaHei", 40))
            more_button.setFixedSize(int(140 * self.scale_factor2), int(140 * self.scale_factor2))
            more_button.clicked.connect(self.switch_to_all_software)  # 绑定"更多"按钮的功能
            self.grid_layout.addWidget(more_button, 0, len(sorted_games[:self.buttonsindexset]))  # 添加到最后一列
            self.buttons.append(more_button)

        else:
            # 添加一个提示按钮
            no_games_button = QPushButton("没有发现游戏\n点击设置-管理-按钮 了解该软件游戏库工作原理")
            no_games_button.setFixedSize(int(700 * self.scale_factor), int(200 * self.scale_factor))
            no_games_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2e2e2e; 
                    border-radius: {int(10 * self.scale_factor)}px; 
                    border: {int(2 * self.scale_factor)}px solid #444444;
                    color: white;
                    font-size: {int(30 * self.scale_factor)}px;
                }}
            """)
            self.grid_layout.addWidget(no_games_button, 0, 0)
            self.buttons.append(no_games_button)

        # 获取排序后的游戏列表
        sorted_games = self.sort_games()
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        main_layout.setSpacing(0)  # 设置间距为0
        main_layout.addLayout(self.top_layout)  # 添加顶部布局
        main_layout.setAlignment(Qt.AlignTop)

        # 创建一个新的布局容器用于放置游戏按钮网格
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(int(320 * self.scale_factor *2.4))  # 设置高度为90% 
        self.scroll_area.setFixedWidth(int(self.width()))  # 设置宽度为100%
        self.scroll_area.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        # 启用触摸滑动手势
        QScroller.grabGesture(self.scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self.update_additional_game_name_label_position)
        # 垂直的self.scroll_area.verticalScrollBar().valueChanged.connect(self.update_additional_game_name_label_position)

        # 隐藏滚动条和边框
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                width: 0px;
                height: 0px;
            }
        """)

        # 创建一个 QWidget 作为滚动区域的容器
        self.scroll_widget = QWidget()
        self.scroll_widget.setLayout(self.grid_layout)
        self.scroll_area.setWidget(self.scroll_widget)

        # 将滚动区域添加到主布局
        main_layout.addWidget(self.scroll_area)

        self.setLayout(main_layout)

        # 启动游戏运行状态监听线程
        self.play_reload = False
        self.play_lock = threading.Lock()
        self.play_app_name = []
        self.monitor_thread = MonitorRunningAppsThread(self.play_lock, self.play_app_name)
        self.monitor_thread.play_app_name_signal.connect(self.update_play_app_name)  # 连接信号到槽
        self.monitor_thread.play_reload_signal.connect(self.handle_reload_signal)  # 连接信号到槽
        self.monitor_thread.start() 
        
        # 创建启动游戏的悬浮窗
        self.launch_overlay = LaunchOverlay(self)
        
        # 启动手柄输入监听线程
        self.controller_thread = GameControllerThread(self)
        self.controller_thread.gamepad_signal.connect(self.handle_gamepad_input)
        self.controller_thread.start()

        # 按键去抖的间隔时间（单位：毫秒）
        self.last_input_time = 0  # 最后一次处理输入的时间
        self.input_delay = 200  # 去抖延迟时间，单位：毫秒

        # 添加悬浮窗开关防抖
        self.last_window_toggle_time = 0
        self.window_toggle_delay = 300  # 设置300毫秒的防抖延迟

        # 将设置按钮添加到左侧布局
        self.left_layout.addWidget(self.settings_button)
        self.left_layout.addWidget(self.screenshot_button)

        # 初始化时隐藏悬浮窗
        self.control_buttons = []
        # 初始化后台任务相关变量
        self.background_windows = []  # 存储后台窗口信息
        self.background_app_index = 0  # 后台应用的当前显示起始索引
        self.show_background_apps = False  # 是否显示全部后台应用
        self.texta_layout = None  # 保存对 texta_layout 的引用
        self.extra_buttons_container = None  # 额外按钮容器
        # 初始化 control_layout
        self.control_layout = QHBoxLayout()
        self.control_layout.setSpacing(int(50 * self.scale_factor))  # 设置按钮之间的间距
        # 创建一个 QWidget 作为容器
        control_widget = QWidget()
        control_widget.setLayout(self.control_layout)
        
        # 设置最大宽度为屏幕宽度的 75%
        max_width = int(screen.width()*0.75)
        control_widget.setMaximumWidth(max_width)
        # 创建一个水平布局用于居中显示
        centered_layout = QHBoxLayout()
        centered_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        centered_layout.setSpacing(0)  # 设置间距为0
        centered_layout.addStretch()  # 左侧弹性空间
        centered_layout.addWidget(control_widget)  # 添加控制按钮容器
        centered_layout.addStretch()  # 右侧弹性空间
        # 将居中布局添加到主布局
        main_layout.addLayout(centered_layout)
        main_layout.setSpacing(0)  # 设置主布局的间距为0
        # 创建7个圆形按钮
        self.control_button_modes = {}  # 存储每个按钮的当前模式
        for i in range(7):
            btn = QPushButton()
            btn.setFixedSize(int(125 * self.scale_factor), int(125 * self.scale_factor))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #575757;
                    border-radius: 62%;
                    font-size: {int(40 * self.scale_factor)}px; 
                    border: {int(5 * self.scale_factor)}px solid #282828;
                }}
                QPushButton:checked {{
                    background-color: #45a049;
                    border: {int(6 * self.scale_factor)}px solid #ffff00;
                }}
            """)
            # 记录模式并统一连接到点击处理器，处理器会实现"第一次点击只聚焦，第二次执行"逻辑
            if i == 0 or i == 1 or i == 2:
                # 前3个按钮为后台任务切换按钮
                self.control_button_modes[i] = 'background'
            elif i == 3:
                self.control_button_modes[i] = 'mouse'
                btn.setText("🖱️")
            elif i == 4:
                self.control_button_modes[i] = 'image'
                btn.setText("🗺️")
            elif i == 5:
                self.control_button_modes[i] = 'sleep'
                btn.setText("💤")
            elif i == 6:
                self.control_button_modes[i] = 'shutdown'
                btn.setText("🔌")
            # 统一使用本类处理器，以支持首次点击只聚焦的行为
            btn.clicked.connect(lambda checked=False, idx=i: self.handle_control_button_click(idx))
            self.control_buttons.append(btn)
            self.control_layout.addWidget(btn)
        
        # 将控制区域添加到主布局
        main_layout.addLayout(self.control_layout)
        # 创建分割线和文字布局
        divider_layout = QHBoxLayout()
        divider_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        divider_layout.setSpacing(0)  # 设置间距为0
        
        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setFixedHeight(int(4 * self.scale_factor))  # 设置分割线高度
        divider.setStyleSheet("""
            background-color: #444444;  /* 设置背景颜色 */
            border: none;              /* 移除边框 */
        """)
        divider_layout.addWidget(divider)
        
        # 包装分割线布局到 QWidget
        divider_widget = QWidget()
        divider_widget.setLayout(divider_layout)
        
        # 创建文字布局
        texta_layout = QHBoxLayout()
        texta_layout.setContentsMargins(0, 0, 0, 0)  # 设置边距为0
        texta_layout.setSpacing(0)  # 设置控件之间的间距为0
        
        # 左侧文字
        self.left_label = QLabel("🎮️未连接手柄")
        self.left_label.setStyleSheet(f"""
            QLabel {{
                font-family: "Microsoft YaHei"; 
                color: white;
                font-size: {int(25 * self.scale_factor)}px;
                padding-bottom: {int(10 * self.scale_factor)}px;
                padding-left: {int(50 * self.scale_factor)}px;
            }}
        """)
        texta_layout.addWidget(self.left_label, alignment=Qt.AlignLeft)
        # 保存对 texta_layout 的引用，用于添加额外的后台应用按钮
        self.texta_layout = texta_layout
        self.extra_buttons_container = None
        # 连接手柄连接信号到槽函数
        self.controller_thread.controller_connected_signal.connect(self.update_controller_status)
        for controller_data in self.controller_thread.controllers.values():
            controller_name = controller_data['controller'].get_name()
            self.update_controller_status(controller_name)
        # 右侧文字
        self.right_label = QLabel("A / 进入游戏        B / 最小化        Y / 收藏        X / 更多            📦️DeskGamix v0.95.4")
        self.right_label.setStyleSheet(f"""
            QLabel {{
                font-family: "Microsoft YaHei"; 
                color: white;
                font-size: {int(25 * self.scale_factor)}px;
                padding-bottom: {int(10 * self.scale_factor)}px;
                padding-right: {int(50 * self.scale_factor)}px;
            }}
        """)
        texta_layout.addWidget(self.right_label, alignment=Qt.AlignRight)
        
        # 包装文字布局到 QWidget
        texta_widget = QWidget()
        texta_widget.setLayout(texta_layout)
        
        # 创建一个垂直布局，将分割线和文字布局组合
        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(divider_widget)
        bottom_layout.addWidget(texta_widget)
        
        # 包装到一个 QWidget 中
        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom_layout)
        
        # 将底部布局添加到主布局，并设置对齐方式为底部
        main_layout.addWidget(bottom_widget, alignment=Qt.AlignBottom)
        # 初始化完成后立即高亮第一个项目
        self.update_highlight()
        #if STARTUP:
        #    # 设置窗口标志，使其不在任务栏显示
        #    self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        #    # 重新显示窗口以应用新的窗口标志
        #    self.show()
        #    # 立即隐藏窗口
        #    self.hide()
        #    # 延迟一小段时间以确保窗口完全初始化
        #    QTimer.singleShot(100, self.hide)
        # 在 GameSelector 的 __init__ 方法中添加以下代码
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("./_internal/fav.ico"))  # 设置托盘图标为 fav.ico
        self.tray_icon.setToolTip("DeskGamix")
        def build_tray_menu():
            # 重用已有的 QMenu 实例以避免重复创建导致的资源和状态问题
            if hasattr(self, '_tray_menu') and isinstance(self._tray_menu, QMenu):
                tray_menu = self._tray_menu
                try:
                    tray_menu.clear()
                except Exception:
                    # 如果清理失败则重建菜单
                    tray_menu = QMenu(self)
                    self._tray_menu = tray_menu
            else:
                tray_menu = QMenu(self)
                self._tray_menu = tray_menu
            sorted_games = self.sort_games()
            # 缓存已解析图标，避免重复解析
            if not hasattr(self, "_icon_cache"):
                self._icon_cache = {}

            # 辅助：从文件或可执行中提取图标，优先用 icoextract 提取 exe/dll 图标，否则尝试作为图片加载
            def _icon_from_file(fp, size=24):
                try:
                    key = os.path.abspath(fp) if fp else ""
                except Exception:
                    key = str(fp)
                # 缓存命中直接返回
                if key and key in self._icon_cache:
                    return self._icon_cache[key]
                icon = QIcon()
                try:
                    from icoextract import IconExtractor
                    extractor = IconExtractor(fp)
                    bio = extractor.get_icon(num=0)
                    data = bio.getvalue()
                    pix = QPixmap()
                    if pix.loadFromData(data):
                        pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        icon = QIcon(pix)
                except Exception:
                    # 忽略 icoextract 失败，继续尝试作为图片加载
                    pass
                if icon.isNull():
                    try:
                        pix = QPixmap(fp)
                        if not pix.isNull():
                            pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            icon = QIcon(pix)
                    except Exception:
                        pass
                # 保存到缓存（即使是空图标也缓存，避免重复尝试）
                try:
                    if key:
                        self._icon_cache[key] = icon
                except Exception:
                    pass
                return icon

            # 辅助：解析可能含参数或是快捷方式的启动路径，返回可用的 exe 路径或目录
            def _resolve_exec_path(raw_path):
                if not raw_path:
                    return raw_path
                p = raw_path.strip()
                candidate = None
                if p.startswith('"'):
                    m = re.match(r'^\"([^\"]+)\"', p)
                    if m:
                        candidate = m.group(1)
                if not candidate:
                    exts = ['.exe', '.lnk', '.bat', '.cmd', '.com', '.ps1']
                    lower = p.lower()
                    for ext in exts:
                        idx = lower.find(ext)
                        if idx != -1:
                            candidate = p[:idx + len(ext)]
                            break
                if not candidate:
                    candidate = p.split(' ')[0]
                candidate = candidate.strip('"')
                if os.path.exists(candidate):
                    return candidate
                if candidate.lower().endswith('.lnk'):
                    try:
                        from win32com.client import Dispatch
                        shell = Dispatch('WScript.Shell')
                        shortcut = shell.CreateShortCut(candidate)
                        target = shortcut.Targetpath
                        if target and os.path.exists(target):
                            return target
                    except Exception:
                        pass
                if os.path.isdir(candidate):
                    try:
                        for fname in os.listdir(candidate):
                            if fname.lower().endswith('.exe'):
                                cand = os.path.join(candidate, fname)
                                if os.path.exists(cand):
                                    return cand
                    except Exception:
                        pass
                return candidate

            if sorted_games:
                tray_menu.addSeparator()
                for idx, game in enumerate(reversed(sorted_games[:self.buttonsindexset])):
                    icon = QIcon()
                    exec_path_raw = game.get("path", "")
                    if not exec_path_raw:
                        try:
                            for v in valid_apps:
                                if v.get("name") == game.get("name") and v.get("path"):
                                    exec_path_raw = v.get("path")
                                    break
                        except Exception:
                            pass

                    exec_path = _resolve_exec_path(exec_path_raw)
                    exists_flag = os.path.exists(exec_path) if exec_path else False
                    if exec_path and exists_flag:
                        icon = _icon_from_file(exec_path, 24)
                    if icon.isNull():
                        image_path = game.get("image-path", "")
                        if image_path and not os.path.isabs(image_path):
                            image_path = f"{APP_INSTALL_PATH}\\config\\covers\\{image_path}"
                        icon = _icon_from_file(image_path, 24)

                    text = game["name"][:24] + "..." if len(game["name"]) > 24 else game["name"]
                    game_action = tray_menu.addAction(icon, text)
                    # 使用默认参数捕获索引，避免闭包问题
                    game_index = len(sorted_games[:self.buttonsindexset]) - 1 - idx
                    game_action.triggered.connect(lambda checked=False, i=game_index: (self.tray_icon.contextMenu().hide(), self.launch_game(i)))
            tray_menu.addSeparator()
            # 新增“工具”子菜单
            tools_menu = QMenu("工具", self)
            tools_menu.setStyleSheet("""
                QMenu, QMenu::item {
                    color: white;
                    background-color: #232323;
                }
                QMenu::item:selected,
                QMenu QMenu::item:selected {
                    color: black;
                    background-color: #93ffff;
                }
            """)
            for app in more_apps:
                icon = QIcon()
                path = app.get("path", "")
                if path and os.path.exists(path):
                    icon = _icon_from_file(path, 24)
                if icon.isNull():
                    image_path = app.get("image-path", "")
                    if image_path and not os.path.isabs(image_path):
                        image_path = f"{APP_INSTALL_PATH}\\config\\covers\\{image_path}"
                    icon = _icon_from_file(image_path, 24)

                text = app.get("name", "")
                tool_action = tools_menu.addAction(icon, text)
                def launch_tool(checked=False, path=app.get("path", "")):
                    self.hide_window()
                    if isinstance(path, str) and path.strip():
                        subprocess.Popen(path, shell=True)
                tool_action.triggered.connect(launch_tool)
            tray_menu.addMenu(tools_menu)
            tray_menu.addSeparator()
            restart_action = tray_menu.addAction("重启程序")
            restart_action.triggered.connect(self.restart_program)
            restore_action = tray_menu.addAction("导入新游戏（未完成）")
            exit_action = tray_menu.addAction("退出")
            exit_action.triggered.connect(self.exitdef)
            tray_menu.setStyleSheet("""
                QMenu, QMenu::item {
                    color: white;
                    background-color: #232323;
                }
                QMenu::item:selected,
                QMenu QMenu::item:selected {
                    color: black;
                    background-color: #93ffff;
                }
            """)
            return tray_menu

        # 初始菜单（构建并设置菜单）
        self._tray_menu = build_tray_menu()
        self.tray_icon.setContextMenu(self._tray_menu)

        def tray_icon_activated(reason):
            if self.is_mouse_simulation_running:
                self.is_mouse_simulation_running = False
                return
            if reason == QSystemTrayIcon.Context:  # 右键
                self._tray_menu = build_tray_menu()
                self.tray_icon.setContextMenu(self._tray_menu)
            elif reason == QSystemTrayIcon.Trigger:  # 左键
                self.show_window()
                if self.killexplorer == True:
                    self.wintaskbarshow()

        self.tray_icon.activated.connect(tray_icon_activated)
        self.tray_icon.show()  # 显示托盘图标
        # 新增：每分钟记录游玩时间
        self.play_time_timer = QTimer(self)
        self.play_time_timer.timeout.connect(self.update_play_time)
        self.play_time_timer.start(60 * 1000)  # 60秒
        # ==============================
        # 控制按钮标签和缩略图初始化
        # ==============================
        self._current_control_button_label = None
        self._current_control_button_thumbnail = None
        self._label_fade_anims = []
        
        # ==============================
        # 键盘覆盖层（整合键盘逻辑至 GameSelector）
        # ==============================
        self.keyboard_overlay = None
        self.keyboard_overlay_mapping = None
        self.keyboard_overlay_thread = None
        # 键盘覆盖层内部状态（按需初始化）
        self._kb_rb_last_pressed = False
        self._kb_left_state = {'x': 0.0, 'y': 0.0, 'lb': False, 'rb': False, 'radius': 0.0}
        self._kb_right_state = {'x': 0.0, 'y': 0.0, 'lb': False, 'rb': False, 'radius': 0.0}
        self._kb_last_outer_time = {'left': 0, 'right': 0}
        self._kb_last_zone = {'left': 'dead', 'right': 'dead'}
        self._kb_inner_ignore_until = {'left': 0, 'right': 0}
        self._kb_last_x_pressed = [False, False]
        self._kb_last_y_pressed = [False, False]
        self._kb_last_fkey_move_time = 0
        self._kb_ignore_start_until = 0
        
        # 初始化后台窗口信息并更新按钮
        # 注意：必须在所有UI组件创建完成后调用
        self.update_background_windows()
        self.update_background_buttons()
        # ==============================

    def wintaskbarshow(self):
        hide_desktop_icons()
        hide_taskbar()
        self.winTaskbar.show()
    def update_additional_game_name_label_position(self):
        """在滚动时同步更新additional_game_name_label的位置"""
        if (
            hasattr(self, 'additional_game_name_label')
            and isinstance(self.additional_game_name_label, QLabel)
            and self.current_section == 0
            and self.more_section == 0
            and self.buttons
            and 0 <= self.current_index < len(self.buttons)
        ):
            current_button = self.buttons[self.current_index]
            button_width = current_button.width()
            button_pos = current_button.mapToGlobal(QPoint(0, 0))
            self.additional_game_name_label.move(
                button_pos.x() + (button_width - self.additional_game_name_label.width()) // 2,
                button_pos.y() - self.game_name_label.height() - 20
            )

    def resizeEvent(self, event):
        """在窗口尺寸变化时更新依赖宽度的控件布局和位置。"""
        try:
            # 根据高度变化计算新的缩放因子（事件驱动覆盖原来的轮询逻辑）
            try:
                # 优先使用 frameGeometry 以包含窗口装饰
                current_h = int(self.frameGeometry().height())
            except Exception:
                current_h = int(self.height())
            try:
                raw = float(current_h) / float(getattr(self, 'base_height', 1080))
                new_scale = round(raw, getattr(self, 'precision', 2))
                new_scale = max(getattr(self, 'min_scale', 0.45), min(new_scale, getattr(self, 'max_scale', 2.5)))
                if abs(new_scale - getattr(self, 'scale_factor', 0)) >= getattr(self, 'threshold', 0.01):
                    # 使用现有的更新函数统一处理样式与布局更新
                    try:
                        self.on_scale_factor_updated(new_scale)
                    except Exception:
                        self.scale_factor = new_scale
                        self.scale_factor2 = self.scale_factor * 2
            except Exception:
                pass

            w = int(self.width())
            if hasattr(self, 'scroll_area'):
                try:
                    self.scroll_area.setFixedWidth(w)
                except Exception:
                    pass

            # 调整控制区的最大宽度（control_layout 的容器）
            try:
                if hasattr(self, 'control_layout'):
                    control_widget = self.control_layout.parentWidget()
                    if control_widget:
                        control_widget.setMaximumWidth(int(self.width() * 0.75))
            except Exception:
                pass

            # 重新定位可能依赖按钮位置的标签
            try:
                self.update_additional_game_name_label_position()
            except Exception:
                pass
            
            # 调整ScreenshotWindow的大小和位置（如果它存在）
            try:
                if hasattr(self, 'screenshot_window') and self.screenshot_window.isVisible():
                    # 先关闭旧窗口
                    try:
                        self.screenshot_window.close()
                    except Exception:
                        pass
                    # 创建新窗口
                    self.screenshot_window = ScreenshotWindow(self)
                    self.screenshot_window.show()
            except Exception:
                pass
        except Exception:
            pass
        try:
            super().resizeEvent(event)
        except Exception:
            return
    def animate_scroll(self, orientation, target_value, duration=150):
        """平滑滚动到目标值。orientation: 'horizontal' 或 'vertical'。保留动画引用以防被回收。"""
        try:
            if orientation == 'horizontal':
                scrollbar = self.scroll_area.horizontalScrollBar()
            else:
                scrollbar = self.scroll_area.verticalScrollBar()
            start = scrollbar.value()
            if start == int(target_value):
                return
            anim = QPropertyAnimation(scrollbar, b"value")
            anim.setDuration(duration)
            anim.setStartValue(start)
            anim.setEndValue(int(target_value))
            try:
                from PyQt5.QtCore import QEasingCurve
                anim.setEasingCurve(QEasingCurve.InOutCubic)
            except Exception:
                pass
            if not hasattr(self, '_scroll_animations'):
                self._scroll_animations = []
            self._scroll_animations.append(anim)
            def _on_finished():
                try:
                    self._scroll_animations.remove(anim)
                except Exception:
                    pass
            anim.finished.connect(_on_finished)
            anim.start()
        except Exception:
            try:
                if orientation == 'horizontal':
                    self.scroll_area.horizontalScrollBar().setValue(int(target_value))
                else:
                    self.scroll_area.verticalScrollBar().setValue(int(target_value))
            except Exception:
                pass
    def animate_scroll_area_transition(self, new_height, show_controls=True, duration=180):
        """对 `self.scroll_area` 做淡出 -> 调整高度/显示控制按钮 -> 淡入 的过渡动画。
        new_height: 目标高度（像素）；show_controls: 切换后是否显示控制按钮。
        保留动画引用以防被垃圾回收。
        """
        try:
            # 确保有 opacity effect
            effect = self.scroll_area.graphicsEffect()
            if not isinstance(effect, QtWidgets.QGraphicsOpacityEffect):
                effect = QtWidgets.QGraphicsOpacityEffect(self.scroll_area)
                self.scroll_area.setGraphicsEffect(effect)
            # 淡出
            fade_out = QPropertyAnimation(effect, b"opacity")
            fade_out.setDuration(int(duration * 0.6))
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            try:
                from PyQt5.QtCore import QEasingCurve
                fade_out.setEasingCurve(QEasingCurve.InOutCubic)
            except Exception:
                pass
            # 淡入
            fade_in = QPropertyAnimation(effect, b"opacity")
            fade_in.setDuration(int(duration * 0.6))
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            try:
                from PyQt5.QtCore import QEasingCurve
                fade_in.setEasingCurve(QEasingCurve.InOutCubic)
            except Exception:
                pass

            # 保持引用
            if not hasattr(self, '_scroll_area_fade_anims'):
                self._scroll_area_fade_anims = []
            self._scroll_area_fade_anims.extend([fade_out, fade_in])
            try:
                fade_out.setParent(self)
                fade_in.setParent(self)
            except Exception:
                pass

            # 仅在本函数创建 effect 时，后续在动画完成后移除该 effect，避免影响外部已设置的 effect
            created_effect = False
            try:
                if self.scroll_area.graphicsEffect() is effect:
                    # 如果我们刚刚创建并设置了 effect，则标记为可清理
                    created_effect = True
            except Exception:
                created_effect = False

            def _after_fade_out():
                try:
                    # 调整高度并切换控制按钮
                    self.scroll_area.setFixedHeight(int(new_height))
                    self.toggle_control_buttons(show_controls)
                    # 触发界面重载以应用变化
                    try:
                        self.reload_interface()
                    except Exception:
                        pass
                except Exception:
                    pass
                # 开始淡入
                fade_in.start()

            def _after_fade_in():
                try:
                    # 如果是本函数创建的临时 effect，则移除它，避免影响后续动画或样式
                    if created_effect:
                        try:
                            # 移除 effect 并清理引用
                            self.scroll_area.setGraphicsEffect(None)
                        except Exception:
                            pass
                finally:
                    # 清理动画引用
                    try:
                        if fade_in in self._scroll_area_fade_anims:
                            self._scroll_area_fade_anims.remove(fade_in)
                    except Exception:
                        pass

            def _cleanup_fade_out():
                try:
                    if fade_out in self._scroll_area_fade_anims:
                        self._scroll_area_fade_anims.remove(fade_out)
                except Exception:
                    pass

            fade_out.finished.connect(_after_fade_out)
            fade_in.finished.connect(_after_fade_in)
            fade_out.finished.connect(_cleanup_fade_out)
            fade_out.start()
        except Exception:
            # 如果失败则回退到直接切换
            try:
                self.scroll_area.setFixedHeight(int(new_height))
                self.toggle_control_buttons(show_controls)
                self.reload_interface()
            except Exception:
                pass
    def startopenmaobackup(self, sysargv, game_name, exe_path):
        # 检查是否已有maobackup.exe进程在运行
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == 'maobackup.exe':
                    # 弹窗询问是否关闭
                    self.confirm_dialog = ConfirmDialog("maobackup已经启动，是否要关闭？", scale_factor=self.scale_factor)
                    result = self.confirm_dialog.exec_()
                    if result == QDialog.Accepted:
                        proc.terminate()
                        proc.wait()
                    else:
                        return
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        if os.path.exists(exe_path):
            process = QProcess(self)
            process.setProgram(exe_path)
            process.setArguments([sysargv, game_name])
            process.setProcessChannelMode(QProcess.MergedChannels)
            buffer = b''

            def handle_ready_read():
                nonlocal buffer
                buffer += process.readAllStandardOutput().data()
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    try:
                        msg = json.loads(line.decode(errors='ignore'))
                        if msg.get("type") in ("error", "info", "warning"):
                            self.confirm_dialog = ConfirmDialog("※"+msg.get("message", ""), scale_factor=self.scale_factor)
                            result = self.confirm_dialog.exec_()
                        elif msg.get("type") == "confirm":
                            self.confirm_dialog = ConfirmDialog("※"+msg.get("message", ""))
                            result = self.confirm_dialog.exec_()
                            process.write(("yes\n" if result == QDialog.Accepted else "no\n").encode())
                            process.waitForBytesWritten(100)
                    except Exception as e:
                        print("解析JSON失败：", e)

            def handle_finished(exitCode, exitStatus):
                # 可在此处理进程结束后的逻辑
                pass

            process.readyReadStandardOutput.connect(handle_ready_read)
            process.finished.connect(handle_finished)
            process.start()
        else:
            self.confirm_dialog = ConfirmDialog("未找到maobackup.exe", scale_factor=self.scale_factor).exec_()
    def deep_reload_games(self):
        """深度刷新游戏库：重新读取apps.json并刷新界面"""
        load_apps()  # 重新加载有效应用列表
        self.reload_interface()

    def update_play_time(self):
        """每分钟记录当前活动窗口为游戏时的游玩时间"""
        if "play_time" not in settings:
            settings["play_time"] = {}

        try:
            hwnd = win32gui.GetForegroundWindow()
            pid = win32process.GetWindowThreadProcessId(hwnd)[1]
            proc = psutil.Process(pid)
            exe_path = proc.exe()
            exe_name = os.path.basename(exe_path).lower()
        except Exception as e:
            print(f"获取活动窗口进程失败: {e}")
            return

        # 遍历当前运行的游戏名
        for game_name in self.player:
            print(f"检查游戏: {game_name}")
            # 在 valid_apps 里查找对应游戏的 exe
            for app in valid_apps:
                print(f"  valid_apps项: name={app.get('name')}, path={app.get('path')}")
                if app.get("name") == game_name:
                    game_exe = os.path.basename(app.get("path", "")).lower()
                    print(f"    匹配到游戏，game_exe={game_exe}, 当前窗口exe={exe_name}")
                    if game_exe and game_exe == exe_name:
                        print(f"    活动窗口是该游戏，累计时间+1分钟")
                        settings["play_time"][game_name] = settings["play_time"].get(game_name, 0) + 1
                        try:
                            with open(settings_path, "w", encoding="utf-8") as f:
                                json.dump(settings, f, indent=4)
                        except Exception as e:
                            print(f"保存游玩时间失败: {e}")
                        return  # 只记录一个游戏
    def open_selected_game_screenshot(self):
        current_time = pygame.time.get_ticks()
        self.ignore_input_until = current_time + 500
        if not hasattr(self, 'screenshot_window'):
            self.screenshot_window = ScreenshotWindow(self)
        # 获取当前选中的游戏名
        sorted_games = self.sort_games()
        #self.screenshot_window.clear_filter()
        if sorted_games and 0 <= self.current_index < len(sorted_games):
            game_name = sorted_games[self.current_index]["name"]
        else:
            game_name = None
        self.screenshot_window.show()
        self.screenshot_window.disable_left_panel_switch = False
        self.screenshot_window.current_index = 0
        self.screenshot_window.current_button_index = 0  # 当前焦点按钮索引
        self.screenshot_window.in_left_panel = True     # 是否在左侧按钮区域
        self.screenshot_window.load_all_images = False  # 不加载所有图片，仅加载前6个图片
        self.screenshot_window.update_left_panel_button_styles()
        if game_name:
            self.screenshot_window.start_filter_mode(game_name=game_name)
    def show_img_window(self):
        current_time = pygame.time.get_ticks()
        self.ignore_input_until = current_time + 500
        if not hasattr(self, 'screenshot_window'):
            self.screenshot_window = ScreenshotWindow(self)
        self.screenshot_window.disable_left_panel_switch = True 
        self.screenshot_window.current_index = 0
        self.screenshot_window.in_left_panel = False     # 是否在左侧按钮区域
        self.screenshot_window.load_all_images = True   # 加载所有图片
        self.screenshot_window.clear_filter()
        self.screenshot_window.show()
    def update_time(self):
        """更新时间显示"""
        current_time = QDateTime.currentDateTime().toString(" HH : mm   dddd")
        # 判断网络状态
        is_connected = ctypes.windll.wininet.InternetGetConnectedState(None, 0)
        network_status = "🛜" if is_connected else "✈️"
        # 更新 time_label
        self.time_label.setText(f"{current_time}    {network_status}")
    def show_window(self):
        """显示窗口"""
        hwnd = int(self.winId())
        ctypes.windll.user32.ShowWindow(hwnd, 9) # 9=SW_RESTORE            
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    def exitbutton(self):
        """退出按钮"""
        if self.more_section == 1:
            self.switch_to_main_interface()
        else:
            self.hide_window()
    def hide_window(self):
        """隐藏窗口"""
        hwnd = int(self.winId())
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0=SW_HIDE
    def switch_to_all_software(self):
        """切换到"所有软件"界面"""
        self.scale_factor2 = self.scale_factor  # 用于按钮和图像的缩放因数
        self.current_index = 0
        self.more_section = 1
        # 使用淡出过渡动画改变 scroll_area 大小并隐藏控制按钮
        try:
            target_h = int(self.height() * 0.85)
            self.animate_scroll_area_transition(target_h, show_controls=False, duration=200)
        except Exception:
            self.scroll_area.setFixedHeight(int(self.height() * 0.85))
            self.toggle_control_buttons(False)
            self.reload_interface()
    def switch_to_main_interface(self):
        """切换到主界面"""
        self.scale_factor2 = self.scale_factor * 2  # 用于按钮和图像的缩放因数
        self.current_section = 0
        self.current_index = 0
        self.more_section = 0
        target_h = int(320 * self.scale_factor * 2.4)
        try:
            self.animate_scroll_area_transition(target_h, show_controls=True, duration=200)
        except Exception:
            self.scroll_area.setFixedHeight(target_h)
            self.toggle_control_buttons(True)
            self.reload_interface()

    def toggle_control_buttons(self, show):
        """显示或隐藏控制按钮"""
        for btn in self.control_buttons:
            btn.setVisible(show)
        if hasattr(self, 'control_layout'):
            self.control_layout.setEnabled(show)
            # 获取control_layout所在的容器widget
            control_widget = self.control_layout.parentWidget()
            if control_widget:
                control_widget.setVisible(show)
            # 获取centered_layout
            for i in range(self.layout().count()):
                item = self.layout().itemAt(i)
                if isinstance(item, QHBoxLayout) and item.indexOf(control_widget) != -1:
                    # 找到了包含control_widget的centered_layout
                    for j in range(item.count()):
                        widget = item.itemAt(j).widget()
                        if widget:
                            widget.setVisible(show)


    # ==============================
    # 控制按钮：首次点击仅聚焦（使用 current_section/current_index），已聚焦则执行动作
    # ==============================
    def handle_control_button_click(self, idx):
        """如果当前焦点不是该控制按钮，则把焦点移动到它并返回；否则执行动作。"""
        try:
            # current_section: 0 = 游戏选择区域, 1 = 控制按钮区域
            if self.current_section != 1 or self.current_index != idx:
                self.current_section = 1
                self.current_index = idx
                try:
                    self.update_highlight()
                except Exception:
                    pass
                return
            # 已处于该焦点，执行动作
            self.perform_control_action(idx)
        except Exception:
            try:
                self.perform_control_action(idx)
            except Exception:
                pass

    def perform_control_action(self, idx):
        """根据按钮模式执行对应动作（假定这些方法在类中存在）。"""
        try:
            mode = self.control_button_modes.get(idx)
            if mode == 'background':
                try:
                    self.on_background_button_clicked(idx)
                except Exception:
                    pass
            elif mode == 'mouse':
                try:
                    self.hide_window()
                    self.mouse_simulation()
                except Exception:
                    pass
            elif mode == 'image':
                try:
                    self.show_img_window()
                except Exception:
                    pass
            elif mode == 'sleep':
                try:
                    self.sleep_system()
                except Exception:
                    pass
            elif mode == 'shutdown':
                try:
                    self.shutdown_system()
                except Exception:
                    pass
        except Exception:
            pass
    # ==============================
    # 键盘覆盖层：创建/显示/关闭
    # ==============================
    def show_keyboard_overlay(self, mapping):
        if self.keyboard_overlay and self.keyboard_overlay.isVisible():
            return
        self.keyboard_overlay_mapping = mapping

        # 创建覆盖层窗口
        self.keyboard_overlay = QDialog(self)
        self.keyboard_overlay.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.keyboard_overlay.setAttribute(Qt.WA_TranslucentBackground)
        self.keyboard_overlay.setWindowOpacity(0.9)
        self.keyboard_overlay.setFixedSize(675, 370)

        # 居中于屏幕底部
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        window_width = self.keyboard_overlay.width()
        window_height = self.keyboard_overlay.height()
        x = (screen_width - window_width) // 2
        y = screen_height * 3 // 4 - window_height // 2
        self.keyboard_overlay.move(x, y)

        # 内容
        wrapper = QWidget(self.keyboard_overlay)
        layout = QVBoxLayout(wrapper)
        layout.setSpacing(0)
        layout.setContentsMargins(10, 10, 10, 10)

        self.keyboard_widget = type(self).KeyboardWidget()
        self.keyboard_widget.key_selected_callback = self.on_key_selected
        layout.addWidget(self.keyboard_widget)

        self.selected_key_label = QLabel("L1选择外圈按钮，R1输入选中项。A键空格，B键删除，Y键启用粘滞键，X键F1~F12")
        self.selected_key_label.setStyleSheet(
            "font-size: 16px; color: white; font-weight: bold; padding: 5px; background: rgba(0,0,0,0.5);"
        )
        self.selected_key_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.selected_key_label)

        v = QVBoxLayout(self.keyboard_overlay)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(wrapper)

        # 初始化键盘映射与状态
        self._kb_ignore_start_until = time.time() + 0.5
        self.setup_keyboard_mappings()
        self._kb_rb_last_pressed = False
        self._kb_left_state = {'x': 0.0, 'y': 0.0, 'lb': False, 'rb': False, 'radius': 0.0}
        self._kb_right_state = {'x': 0.0, 'y': 0.0, 'lb': False, 'rb': False, 'radius': 0.0}
        self._kb_last_outer_time = {'left': 0, 'right': 0}
        self._kb_last_zone = {'left': 'dead', 'right': 'dead'}
        self._kb_inner_ignore_until = {'left': 0, 'right': 0}
        self._kb_last_x_pressed = [False, False]
        self._kb_last_y_pressed = [False, False]
        self._kb_last_fkey_move_time = 0
        # 保存窗口原始位置和位移状态
        self._kb_original_position = (x, y)
        self._kb_window_offset = 600  # 位移的距离（像素）
        self._kb_window_shifted = False  # 窗口是否已向下位移
        self._kb_last_back_pressed = False  # 上次back键状态

        # 启动手柄监听线程（用于键盘覆盖层）
        self.keyboard_overlay_thread = type(self).JoystickThread(self.keyboard_overlay_mapping)
        self.keyboard_overlay_thread.joystick_updated.connect(self.on_keyboard_overlay_joystick_updated)
        self.keyboard_overlay_thread.start()

        self.keyboard_overlay.show()

    def close_keyboard_overlay(self):
        if self.keyboard_overlay_thread:
            self.keyboard_overlay_thread.stop()
            self.keyboard_overlay_thread.wait()
            self.keyboard_overlay_thread = None
        if self.keyboard_overlay:
            self.keyboard_overlay.close()
            self.keyboard_overlay = None

    def is_keyboard_overlay_visible(self):
        return bool(self.keyboard_overlay and self.keyboard_overlay.isVisible())

    # ==============================
    # 键盘覆盖层：映射与事件（移植自 MainWindow）
    # ==============================
    def setup_keyboard_mappings(self):
        # 左摇杆映射
        self.left_joystick_mappings = {
            'inner': {
                'D': 'D',
                'S': 'S', 
                'W': 'W',
                'E': 'E'
            },
            'outer_yellow': [
                'F', 'V', 'C', 'X', 'Z', 'A',
                'Q', '1!', '2@', '3#', '4$', 'R'
            ],
            'outer_green': [
                'G', 'B', 'alt', 'ctrl', 'shift', 'Capslock', 'tab','`~','Esc', 'Win', '5%','T', 'G'
            ]
        }
        # 右摇杆映射
        self.right_joystick_mappings = {
            'inner': {
                'D': 'L',
                'S': 'K',
                'W': 'I', 
                'E': 'O'
            },
            'outer_yellow': [
                ';:', '/?', '.>', ',<', 'M', 'J', 'U',
                '7&', '8*', '9(', '0)', 'P'
            ],
            'outer_green': [
                 "'\"", '\\|', 'Enter', 'Del','N','H','Y','6^','-_'
                 , '=+', '[{', ']}'
            ]
        }

    def on_keyboard_overlay_joystick_updated(self, joystick_id, x_axis, y_axis, lb_pressed, rb_pressed):
        # 读取按键一次性事件
        if hasattr(self, 'keyboard_overlay_thread') and self.keyboard_overlay_thread and hasattr(self.keyboard_overlay_thread, 'joysticks'):
            if joystick_id < len(self.keyboard_overlay_thread.joysticks):
                joystick = self.keyboard_overlay_thread.joysticks[joystick_id]
                mapping = self.keyboard_overlay_mapping
                lt_val = joystick.get_axis(4)
                rt_val = joystick.get_axis(5)
                a_pressed = True if lt_val > 0.1 else joystick.get_button(mapping.button_a)
                b_pressed = True if rt_val > 0.1 else joystick.get_button(mapping.button_b)
                y_pressed = joystick.get_button(mapping.button_y)
                x_pressed = joystick.get_button(mapping.button_x)
                start_pressed = joystick.get_button(mapping.start)
                back_pressed = joystick.get_button(mapping.back)
                ls_pressed = joystick.get_button(mapping.left_stick_in)
                rs_pressed = joystick.get_button(mapping.right_stick_in)
                guide_pressed = joystick.get_button(mapping.guide)

                # D-Pad（hat 或 按钮）
                vdvdv = 0.2
                if hasattr(mapping, 'has_hat') and mapping.has_hat and joystick.get_numhats() > 0:
                    hat = joystick.get_hat(0)
                    if hat == (0, 1):
                        pyautogui.press('up'); time.sleep(vdvdv)
                    elif hat == (0, -1):
                        pyautogui.press('down'); time.sleep(vdvdv)
                    elif hat == (-1, 0):
                        pyautogui.press('left'); time.sleep(vdvdv)
                    elif hat == (1, 0):
                        pyautogui.press('right'); time.sleep(vdvdv)
                else:
                    if joystick.get_button(mapping.dpad_up):
                        pyautogui.press('up'); time.sleep(vdvdv)
                    if joystick.get_button(mapping.dpad_down):
                        pyautogui.press('down'); time.sleep(vdvdv)
                    if joystick.get_button(mapping.dpad_left):
                        pyautogui.press('left'); time.sleep(vdvdv)
                    if joystick.get_button(mapping.dpad_right):
                        pyautogui.press('right'); time.sleep(vdvdv)

                # A/B/X/Y
                if a_pressed:
                    pyautogui.press('space'); time.sleep(vdvdv)
                if b_pressed:
                    pyautogui.press('backspace'); time.sleep(vdvdv)
                if x_pressed and not self._kb_last_x_pressed[joystick_id]:
                    self.keyboard_widget.toggle_sticky_mode()
                self._kb_last_x_pressed[joystick_id] = x_pressed
                if y_pressed and not self._kb_last_y_pressed[joystick_id]:
                    self.keyboard_widget.toggle_f_keys_mode()
                self._kb_last_y_pressed[joystick_id] = y_pressed

                # 退出键：Start 或 LS/RS/Guide
                if start_pressed and time.time() > self._kb_ignore_start_until:
                    self.close_keyboard_overlay(); return
                if any([ls_pressed, rs_pressed, guide_pressed]) and time.time() > self._kb_ignore_start_until:
                    self.close_keyboard_overlay(); return
                
                # Back键：切换窗口位置（位移/恢复原位置）
                # 只在joystick_id == 0时处理，避免重复触发
                if joystick_id == 0:
                    if back_pressed and not self._kb_last_back_pressed:
                        # 只在按键按下瞬间触发一次
                        if hasattr(self, '_kb_original_position') and self.keyboard_overlay:
                            if self._kb_window_shifted:
                                # 恢复原位置
                                self.keyboard_overlay.move(*self._kb_original_position)
                                self._kb_window_shifted = False
                            else:
                                # 位移
                                orig_x, orig_y = self._kb_original_position
                                offset_x = orig_x + self._kb_window_offset
                                self.keyboard_overlay.move(offset_x, orig_y)
                                self._kb_window_shifted = True
                    self._kb_last_back_pressed = back_pressed

        # 保存摇杆状态并驱动 UI 更新
        radius = math.sqrt(x_axis**2 + y_axis**2)
        if joystick_id == 0:
            self._kb_left_state = {'x': x_axis, 'y': y_axis, 'lb': lb_pressed, 'rb': rb_pressed, 'radius': radius}
        elif joystick_id == 1:
            self._kb_right_state = {'x': x_axis, 'y': y_axis, 'lb': lb_pressed, 'rb': rb_pressed, 'radius': radius}
        if self.keyboard_widget:
            self.keyboard_widget.set_joystick_state(
                {'x': self._kb_left_state['x'], 'y': self._kb_left_state['y']},
                {'x': self._kb_right_state['x'], 'y': self._kb_right_state['y']}
            )

        # F 区模式 or 普通模式
        if self.keyboard_widget and self.keyboard_widget.f_keys_enabled:
            self.handle_f_keys_selection_overlay(self._kb_left_state['rb'])
        else:
            left_r = self._kb_left_state['radius']
            right_r = self._kb_right_state['radius']
            if left_r >= right_r:
                s = self._kb_left_state
                self.update_keyboard_from_joystick_overlay(s['x'], s['y'], s['lb'], s['rb'], 'left')
            else:
                s = self._kb_right_state
                self.update_keyboard_from_joystick_overlay(s['x'], s['y'], s['lb'], s['rb'], 'right')

    def update_keyboard_from_joystick_overlay(self, x_axis, y_axis, lb_pressed, rb_pressed, side):
        radius = math.sqrt(x_axis**2 + y_axis**2)
        mapped_key = None
        now = time.time()
        zone = 'dead'
        if radius <= 0.2:
            zone = 'dead'
        elif radius < 0.75:
            zone = 'inner'
        else:
            zone = 'outer'
        mappings = self.left_joystick_mappings if side == 'left' else self.right_joystick_mappings
        angle = None
        if radius > 0.2:
            angle = math.degrees(math.atan2(y_axis, x_axis))
            if angle < 0:
                angle += 360
        # 外圈触发与内圈忽略
        if zone == 'outer' and self._kb_last_zone[side] != 'outer':
            self._kb_last_outer_time[side] = now
            self._kb_inner_ignore_until[side] = now + 0.25
        if zone == 'inner' and self._kb_last_zone[side] == 'dead':
            self._kb_inner_ignore_until[side] = 0
        # RB：执行选中按键/粘滞逻辑
        if rb_pressed:
            if not self._kb_rb_last_pressed:
                label_text = self.selected_key_label.text()
                if label_text.startswith('[') and label_text.endswith(']'):
                    selected_key = label_text[1:-1].strip()
                    if selected_key:
                        if len(selected_key) == 2:
                            selected_key = selected_key[0]
                        if self.keyboard_widget.sticky_enabled:
                            if selected_key in self.keyboard_widget.sticky_key_names:
                                if selected_key in self.keyboard_widget.sticky_keys:
                                    self.keyboard_widget.sticky_keys.remove(selected_key)
                                else:
                                    self.keyboard_widget.sticky_keys.add(selected_key)
                                self.keyboard_widget.update()
                            else:
                                if self.keyboard_widget.sticky_keys:
                                    sticky_modifiers = []
                                    if 'shift' in self.keyboard_widget.sticky_keys: sticky_modifiers.append('shift')
                                    if 'ctrl' in self.keyboard_widget.sticky_keys: sticky_modifiers.append('ctrl')
                                    if 'alt' in self.keyboard_widget.sticky_keys: sticky_modifiers.append('alt')
                                    if 'Win' in self.keyboard_widget.sticky_keys: sticky_modifiers.append('win')
                                    if sticky_modifiers:
                                        pyautogui.hotkey(*sticky_modifiers, selected_key.lower())
                                    else:
                                        pyautogui.press(selected_key.lower())
                                    self.keyboard_widget.sticky_keys.clear()
                                    self.keyboard_widget.update()
                                else:
                                    pyautogui.press(selected_key.lower())
                        else:
                            pyautogui.press(selected_key.lower())
            self._kb_rb_last_pressed = True
            self.keyboard_widget.update_active_key(None)
            self._kb_last_zone[side] = zone
            return
        else:
            self._kb_rb_last_pressed = False
        # 内圈延迟
        if zone == 'inner':
            if now < self._kb_inner_ignore_until[side]:
                self._kb_last_zone[side] = zone
                return
        # 正常映射
        if zone == 'inner' and angle is not None:
            if 0 <= angle < 90:
                direction = 'D'
            elif 90 <= angle < 180:
                direction = 'S'
            elif 180 <= angle < 270:
                direction = 'W'
            else:
                direction = 'E'
            mapped_key = mappings['inner'][direction]
        elif zone == 'outer' and angle is not None:
            sector = int(angle / 30) % 12
            if lb_pressed:
                mapped_key = mappings['outer_green'][sector]
            else:
                mapped_key = mappings['outer_yellow'][sector]
        if mapped_key:
            self.keyboard_widget.update_active_key(mapped_key)
        self._kb_last_zone[side] = zone

    def handle_f_keys_selection_overlay(self, rb_pressed):
        # 选择使用X轴较大的一侧
        left_x = self._kb_left_state['x']
        right_x = self._kb_right_state['x']
        x_axis = left_x if abs(left_x) >= abs(right_x) else right_x
        threshold = 0.2
        now = time.time()
        if abs(x_axis) > threshold:
            if now - self._kb_last_fkey_move_time > 0.15:
                if x_axis > 0:
                    self.keyboard_widget.move_f_keys_selection(1)
                else:
                    self.keyboard_widget.move_f_keys_selection(-1)
                self._kb_last_fkey_move_time = now
        if rb_pressed:
            if not self._kb_rb_last_pressed:
                current_f_key = self.keyboard_widget.get_current_f_key()
                if current_f_key:
                    pyautogui.press(current_f_key.lower())
                self._kb_rb_last_pressed = True
        else:
            self._kb_rb_last_pressed = False
        current_f_key = self.keyboard_widget.get_current_f_key()
        if current_f_key:
            self.selected_key_label.setText(f"[{current_f_key}]")

    def on_key_selected(self, key_name):
        if hasattr(self, 'selected_key_label') and self.selected_key_label:
            self.selected_key_label.setText(f"[{key_name}]")

    # ==============================
    # 鼠标映射主循环（非“键盘模拟”范围）
    # - 包含对系统快捷键的 pyautogui 触发，但不属于键盘模拟整理范畴
    # ==============================
    def mouse_simulation(self):
        """开启鼠标映射"""
        # 检查是否已经在运行
        if self.is_mouse_simulation_running:
            print("鼠标映射已在运行，忽略重复调用")
            return

        # 设置标志为 True，表示正在运行
        self.is_mouse_simulation_running = True

        if pygame.joystick.get_count() == 0:
            self.show_window()
            return
        joysticks = []
        for i in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            joysticks.append(joystick)
    
        if not joysticks:
            print("未检测到手柄")
        joystick_states = {joystick.get_instance_id(): {"scrolling_up": False, "scrolling_down": False} for joystick in joysticks}
        print("鼠标映射")

        # 鼠标移动灵敏度（高/低）
        SENS_HIGH = 100.0
        SENS_MEDIUM = 25.0
        SENS_LOW  = 10.0
        sensitivity = SENS_MEDIUM
        sensitivity1 = SENS_LOW
        DEADZONE = 0.1    # 摇杆死区阈值，防止轻微漂移
        clock = pygame.time.Clock()
        #mapping = ControllerMapping(joystick)
        # 初始化滚动状态变量
        scrolling_up = False
        scrolling_down = False
        window = type(self).MouseWindow()
        last_mouse_x, last_mouse_y = -1, -1  # 初始化上一次鼠标位置
        magnifier_open = False  # 初始化放大镜状态
        # 初始化鼠标按键状态变量
        left_button_down = False
        right_button_down = False
        screen_width, screen_height = pyautogui.size()
        pyautogui.moveTo(int(screen_width/2), int(screen_height/1.5))  # 移动鼠标到屏幕中心
        time.sleep(0.7) 
        #print(f'所有按键: {joystick.get_button(mapping.button_a)}, {joystick.get_button(mapping.button_b)}, {joystick.get_button(mapping.button_x)}, {joystick.get_button(mapping.button_y)}, {joystick.get_button(mapping.start)}, {joystick.get_button(mapping.back)}')
        #print(f"X轴: {x_axis:.2f}, Y轴: {y_axis:.2f}, 右扳机: {rt_val:.2f}, 左扳机: {lt_val:.2f}, 滚动: {scrolling_up}, {scrolling_down}")
        #print(f"{mapping.guide} {mapping.right_stick_in} {mapping.left_stick_in} {mapping.start} {mapping.back} {mapping.button_a} {mapping.button_b} {mapping.button_x} {mapping.button_y}")
        running = True  # 添加状态标志
        # 同时下压左右扳机计时切换标记窗口显示/隐藏
        both_triggers_start_time = None
        marker_hidden = False
        both_triggers_action_done = False  # 防抖：一次长按只触发一次
        try:
            while running:
                # 动态检测新手柄加入或移除
                for event in pygame.event.get():
                    if event.type == pygame.JOYDEVICEADDED:
                        joystick = pygame.joystick.Joystick(event.device_index)
                        joystick.init()
                        # 检查是否已在列表中
                        if joystick not in joysticks:
                            joysticks.append(joystick)
                            joystick_states[joystick.get_instance_id()] = {"scrolling_up": False, "scrolling_down": False}
                            print(f"手柄已连接: {joystick.get_name()}")
                    elif event.type == pygame.JOYDEVICEREMOVED:
                        # 移除断开手柄及其状态
                        for joystick in joysticks[:]:
                            if joystick.get_instance_id() == event.instance_id:
                                print(f"手柄已断开: {joystick.get_name()}")
                                joysticks.remove(joystick)
                                joystick_states.pop(event.instance_id, None)
                                break
                # 检查当前所有手柄，自动补充新插入的手柄
                for i in range(pygame.joystick.get_count()):
                    joystick = pygame.joystick.Joystick(i)
                    if joystick not in joysticks:
                        joystick.init()
                        joysticks.append(joystick)
                        joystick_states[joystick.get_instance_id()] = {"scrolling_up": False, "scrolling_down": False}
                        print(f"检测到新手柄: {joystick.get_name()}")
                pygame.event.pump()
                mouse_x, mouse_y = pyautogui.position()
                # 仅当鼠标位置发生变化时更新窗口位置
                if (mouse_x, mouse_y) != (last_mouse_x, last_mouse_y):
                    # 更新窗口位置
                    window.label.move(mouse_x, mouse_y)
                    last_mouse_x, last_mouse_y = mouse_x, mouse_y
                # 遍历所有手柄，处理输入
                joycount = pygame.joystick.get_count()
                for joystick in joysticks:
                    mapping = ControllerMapping(joystick) #切换对应的手柄映射
                    # GUIDE 按钮退出
                    if joystick.get_button(mapping.guide) or joystick.get_button(mapping.right_stick_in) or joystick.get_button(mapping.left_stick_in) or self.is_mouse_simulation_running == False:
                        running = False  # 设置状态标志为 False，退出循环
                        # 设置右下角坐标
                        print("退出鼠标映射")
                        if self.is_magnifier_open():
                            self.close_magnifier()
                            magnifier_open = False
                        right_bottom_x = screen_width - 1  # 最右边
                        right_bottom_y = screen_height - 1  # 最底部
                        # 移动鼠标到屏幕右下角
                        pyautogui.moveTo(right_bottom_x, right_bottom_y)
                        #time.sleep(0.5)  
                        break

                    # 检查左键状态
                    if joystick.get_button(mapping.button_a) or joystick.get_button(mapping.right_bumper):  # A键模拟左键按下
                        if not left_button_down:  # 状态变化时触发
                            pyautogui.mouseDown()
                            left_button_down = True
                    else:
                        if left_button_down:  # 状态变化时触发
                            pyautogui.mouseUp()
                            left_button_down = False

                    # 检查右键状态
                    if joystick.get_button(mapping.button_b) or joystick.get_button(mapping.left_bumper):  # B键模拟右键按下
                        if not right_button_down:  # 状态变化时触发
                            pyautogui.mouseDown(button='right')
                            right_button_down = True
                    else:
                        if right_button_down:  # 状态变化时触发
                            pyautogui.mouseUp(button='right')
                            right_button_down = False
                    # 读取左摇杆轴值（0: X 轴，1: Y 轴）
                    x_axis = joystick.get_axis(0)
                    y_axis = joystick.get_axis(1)
                    # 读取扳机轴值
                    rt_val = joystick.get_axis(5)
                    lt_val = joystick.get_axis(4)
                    # 检查是否使用 hat 输入
                    if mapping.has_hat:
                        hat_value = joystick.get_hat(0)  # 获取第一个 hat 的值
                        if magnifier_open:
                            if not self.is_magnifier_open():
                                magnifier_open = False
                            # 放大镜打开时，方向键模拟 Ctrl+Alt+方向键
                            if hat_value == (-1, 0):  # 左
                                pyautogui.hotkey('ctrl', 'alt', 'left')
                                time.sleep(0.2)
                            elif hat_value == (1, 0):  # 右
                                pyautogui.hotkey('ctrl', 'alt', 'right')
                                time.sleep(0.2)
                            elif hat_value == (0, -1):  # 下
                                pyautogui.hotkey('ctrl', 'alt', 'down')
                                time.sleep(0.2)
                            elif hat_value == (0, 1):  # 上
                                pyautogui.hotkey('ctrl', 'alt', 'up')
                                time.sleep(0.2)
                            # 滚动行为不变
                            if joystick.get_button(mapping.button_x) or hat_value == (0, -1):
                                scrolling_down = True
                            else:
                                scrolling_down = False
                            if joystick.get_button(mapping.button_y) or hat_value == (0, 1):
                                scrolling_up = True
                            else:
                                scrolling_up = False
                        else:
                            if hat_value == (-1, 0):  # 左
                                if lt_val > 0.5 or rt_val > 0.5:
                                    pyautogui.hotkey('left')
                                else:
                                    self.decrease_volume()
                                time.sleep(0.2)
                            elif hat_value == (1, 0):  # 右
                                if lt_val > 0.5 or rt_val > 0.5:
                                    pyautogui.hotkey('right')
                                else:
                                    self.increase_volume()
                                time.sleep(0.2)
                            elif joystick.get_button(mapping.button_x) or hat_value == (0, -1):  # 下
                                scrolling_down = True
                            elif joystick.get_button(mapping.button_y) or hat_value == (0, 1):  # 上
                                scrolling_up = True
                            else:
                                scrolling_down = False
                                scrolling_up = False
                    else:
                        if magnifier_open:
                            if not self.is_magnifier_open():
                                magnifier_open = False
                            # 放大镜打开时，方向键模拟 Ctrl+Alt+方向键
                            if joystick.get_button(mapping.dpad_left):
                                pyautogui.hotkey('ctrl', 'alt', 'left')
                                time.sleep(0.2)
                            elif joystick.get_button(mapping.dpad_right):
                                pyautogui.hotkey('ctrl', 'alt', 'right')
                                time.sleep(0.2)
                            elif joystick.get_button(mapping.dpad_down):
                                pyautogui.hotkey('ctrl', 'alt', 'down')
                                time.sleep(0.2)
                            elif joystick.get_button(mapping.dpad_up):
                                pyautogui.hotkey('ctrl', 'alt', 'up')
                                time.sleep(0.2)
                            # 滚动行为不变
                            if joystick.get_button(mapping.button_x) or joystick.get_button(mapping.dpad_down):
                                scrolling_down = True
                            else:
                                scrolling_down = False
                            if joystick.get_button(mapping.button_y) or joystick.get_button(mapping.dpad_up):
                                scrolling_up = True
                            else:
                                scrolling_up = False
                        else:
                            if joystick.get_button(mapping.dpad_left):
                                if lt_val > 0.5 or rt_val > 0.5:
                                    pyautogui.hotkey('left')
                                else:
                                    self.decrease_volume()
                                time.sleep(0.2)
                            elif joystick.get_button(mapping.dpad_right):
                                if lt_val > 0.5 or rt_val > 0.5:
                                    pyautogui.hotkey('right')
                                else:
                                    self.increase_volume()
                                time.sleep(0.2)
                            if joystick.get_button(mapping.button_x) or joystick.get_button(mapping.dpad_down):
                                scrolling_down = True
                            else:
                                scrolling_down = False
                            if joystick.get_button(mapping.button_y) or joystick.get_button(mapping.dpad_up):
                                scrolling_up = True
                            else:
                                scrolling_up = False

                    # 同时下压两个扳机时开始计时，满2秒后切换标志窗口显示/隐藏
                    if lt_val > 0.5 and rt_val > 0.5:
                        if both_triggers_start_time is None:
                            both_triggers_start_time = time.time()
                            both_triggers_action_done = False
                        elif not both_triggers_action_done and (time.time() - both_triggers_start_time) >= 1.0:
                            if marker_hidden:
                                # 重新显示并对齐当前位置
                                try:
                                    mx, my = pyautogui.position()
                                    window.label.move(mx, my)
                                except Exception:
                                    pass
                                window.show()
                                marker_hidden = False
                            else:
                                window.hide()
                                marker_hidden = True
                            both_triggers_action_done = True
                    else:
                        # 松手后重置，允许再次触发
                        both_triggers_start_time = None
                        both_triggers_action_done = False

                    # 读取右摇杆轴值（2: X 轴，3: Y 轴）
                    rx_axis = joystick.get_axis(2)  # 右摇杆 X 轴
                    ry_axis = joystick.get_axis(3)  # 右摇杆 Y 轴
                    def backandstart_pressed():
                        nonlocal magnifier_open
                        if joystick.get_button(mapping.back):
                            pyautogui.hotkey('win', 'a')
                            screen_width, screen_height = pyautogui.size()
                            pyautogui.moveTo(screen_width * 7 / 8, screen_height * 6 / 8)
                            time.sleep(0.5)
                        if joystick.get_button(mapping.start):
                            if not self.is_magnifier_open():
                                self.open_magnifier()
                                magnifier_open = True
                            else:
                                self.close_magnifier()
                                magnifier_open = False
                            time.sleep(0.5)
                    if lt_val > 0.5:
                        sensitivity = SENS_HIGH
                        backandstart_pressed()
                    elif rt_val > 0.5:
                        sensitivity = SENS_LOW
                        sensitivity1 = SENS_HIGH
                        backandstart_pressed()
                    else:
                        sensitivity = SENS_MEDIUM
                        sensitivity1 = SENS_LOW
                    
                    if joystick.get_button(mapping.start):
                        if magnifier_open:
                            if not self.is_magnifier_open():
                                magnifier_open = False
                            else:
                                self.close_magnifier()
                                magnifier_open = False
                                time.sleep(0.2)
                                break
                        print("切换到虚拟键盘覆盖层")
                        self.show_keyboard_overlay(mapping)
                        while self.is_keyboard_overlay_visible():
                            QApplication.processEvents()
                            time.sleep(0.05)
                        time.sleep(0.2)
                        break
                    if joystick.get_button(mapping.back):  # SELECT 键 → Win+Tab（非键盘模拟范围）
                        pyautogui.hotkey('win', 'tab')
                        pyautogui.moveTo(int(screen_width/2), int(screen_height/2))
                        time.sleep(0.5)  # 延迟0.2秒，避免重复触发

                    # 使用右摇杆控制鼠标移动（低灵敏度）
                    dx = dy = 0
                    if abs(rx_axis) > DEADZONE:
                        self.move_mouse_once()
                        dx = rx_axis * sensitivity1
                    if abs(ry_axis) > DEADZONE:
                        self.move_mouse_once()
                        dy = ry_axis * sensitivity1
                    # PyAutoGUI中 y 轴正值向下移动，与摇杆上推为负值刚好对应
                    pyautogui.moveRel(dx, dy)

                    # 根据摇杆值控制鼠标移动，加入死区处理
                    dx = dy = 0
                    if abs(x_axis) > DEADZONE:
                        self.move_mouse_once()
                        dx = x_axis * sensitivity
                    if abs(y_axis) > DEADZONE:
                        self.move_mouse_once()
                        dy = y_axis * sensitivity
                    # PyAutoGUI中 y 轴正值向下移动，与摇杆上推为负值刚好对应
                    pyautogui.moveRel(dx, dy)

                    # 在主循环中处理滚动
                    if scrolling_up:
                        pyautogui.scroll(50)  # 持续向上滚动
                    if scrolling_down:
                        pyautogui.scroll(-50)  # 持续向下滚动
                    #print(f'所有按键: {joystick.get_button(mapping.button_a)}, {joystick.get_button(mapping.button_b)}, {joystick.get_button(mapping.button_x)}, {joystick.get_button(mapping.button_y)}, {joystick.get_button(mapping.start)}, {joystick.get_button(mapping.back)}')
                    #print(f"X轴: {x_axis:.2f}, Y轴: {y_axis:.2f}, 右扳机: {rt_val:.2f}, 左扳机: {lt_val:.2f}, 滚动: {scrolling_up}, {scrolling_down}")
                    clock.tick(int(60*joycount))  # 稳定循环频率 (60 FPS)
        except KeyboardInterrupt:
            print("程序已退出。")
        finally:
            # 退出时重置标志
            window.close()
            #ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)  # SPI_SETCURSORS = 0x0057 还原鼠标光标
            self.is_mouse_simulation_running = False
            print("鼠标已退出")

    ########################
    def move_mouse_once(self):
        """模拟鼠标移动，避免光标不显示"""
        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [("dx", ctypes.c_long),
                        ("dy", ctypes.c_long),
                        ("mouseData", ctypes.c_ulong),
                        ("dwFlags", ctypes.c_ulong),
                        ("time", ctypes.c_ulong),
                        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

        class INPUT_UNION(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", ctypes.c_ulong),
                        ("u", INPUT_UNION)]

        def send(dx, dy):
            extra = ctypes.c_ulong(0)
            mi = MOUSEINPUT(dx, dy, 0, 0x0001, 0, ctypes.pointer(extra))  # 0x0001 = MOUSEEVENTF_MOVE
            inp = INPUT(0, INPUT_UNION(mi))  # 0 = INPUT_MOUSE
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

        send(1, 0)   # 向右移动1像素
        send(-1, 0)  # 向左移动1像素
    def is_magnifier_open(self):
        """检查放大镜是否已打开"""
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name'] and process.info['name'].lower() == 'magnify.exe':
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False

    def open_magnifier(self):
        """打开系统放大镜"""
        try:
            subprocess.Popen(['magnify.exe'], shell=True)
        except FileNotFoundError:
            print("无法找到放大镜程序")

    def close_magnifier(self):
        """关闭系统放大镜"""
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name'] and process.info['name'].lower() == 'magnify.exe':
                    process.terminate()
                    process.wait()
                    print("放大镜已关闭")
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    def toggle_mute(self):
        """静音或恢复声音"""
        try:
            # 调用 Windows 的音量静音快捷键
            ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)  # VK_VOLUME_MUTE
            ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)  # KEYEVENTF_KEYUP
            print("切换静音状态")
        except Exception as e:
            print(f"切换静音状态时出错: {e}")
    def increase_volume(self):
        """增加系统音量"""
        ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)  # VK_VOLUME_UP
        ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)  # KEYEVENTF_KEYUP
    
    def decrease_volume(self):
        """降低系统音量"""
        ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)  # VK_VOLUME_DOWN
        ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)  # KEYEVENTF_KEYUP
    #def lock_system(self):
    #    ctypes.windll.user32.LockWorkStation()

    def sleep_system(self):
        #os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        ctypes.windll.powrprof.SetSuspendState(0, 1, 0)

    def shutdown_system(self):
        if ADMIN:
            os.system("shutdown /s /t 0")
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "shutdown", "/s /t 0", None, 1)
            
    def handle_reload_signal(self):
        """处理信号时的逻辑"""
        QTimer.singleShot(100, self.reload_interface)

    def update_play_app_name(self, new_play_app_name):
        """更新主线程中的 play_app_name"""
        self.player = new_play_app_name
        print(f"更新后的 play_app_name: {self.play_app_name}")

    def create_game_button(self, game, index):
        """创建游戏按钮和容器"""
        # 创建容器
        button_container = QWidget()
        button_container.setFixedSize(int(220 * self.scale_factor2), int(300 * self.scale_factor2))  # 确保容器大小固定

        # 创建游戏按钮
        button = QPushButton()
        image_path = game["image-path"]
        # 自动判断图片路径是相对还是绝对
        if not os.path.isabs(image_path):
            image_path = f"{APP_INSTALL_PATH}\\config\\covers\\{image_path}"
        
        pixmap = QPixmap(image_path).scaled(int(200 * self.scale_factor2), int(267 * self.scale_factor2), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon = QIcon(pixmap)
        button.setIcon(icon)
        button.setIconSize(pixmap.size())
        button.setFixedSize(int(220 * self.scale_factor2), int(300 * self.scale_factor2))
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: #2e2e2e; 
                border-radius: {int(10 * self.scale_factor2)}px; 
                border: {int(2 * self.scale_factor2)}px solid #444444;
            }}
            QPushButton:hover {{
                border: {int(2 * self.scale_factor2)}px solid #888888;
            }}
        """)

        # 修改：点击时先判断光标位置
        def on_button_clicked(checked=False, idx=index):
            if self.current_index != idx or self.current_section != 0:
                self.current_section = 0
                self.current_index = idx
                self.update_highlight()
            else:
                self.launch_game(idx)
        button.clicked.connect(on_button_clicked)

        # 创建星标（如果已收藏）
        if game["name"] in settings["favorites"]:
            star_label = QLabel("✰", button)  # 将星标作为按钮的子控件
            star_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(10 * self.scale_factor2)}px;
                    padding: {int(5 * self.scale_factor2)}px;
                    background-color: rgba(46, 46, 46, 0.2);
                    border-radius: {int(10 * self.scale_factor2)}px;
                }}
            """)
            star_label.move(int(5 * self.scale_factor2), int(5 * self.scale_factor2)) 
        if game["name"] in self.player:
            star_label = QLabel("🌊运行中🌊\n点击恢复", button)  
            star_label.setAlignment(Qt.AlignCenter)
            star_label.setStyleSheet(f"""
                QLabel {{
                    color: yellow;
                    font-size: {int(20 * self.scale_factor2)}px;
                    padding: {int(5 * self.scale_factor2)}px;
                    background-color: rgba(46, 46, 46, 0.7);
                    border-radius: {int(5 * self.scale_factor2)}px;
                    border: {int(2 * self.scale_factor2)}px solid white;
                    text-align: center;
                }}
            """)
            star_label.move(int(45 * self.scale_factor2), int(190 * self.scale_factor2)) 
        
        return button

    def update_highlight(self):
        """高亮当前选中的游戏按钮，并更新游戏名称"""
        sorted_games = self.sort_games()
        
        # 检查是否有游戏
        if not sorted_games:
            self.game_name_label.setText("没有找到游戏")
            return
        
        # 确保 current_index 不超出范围
        if self.current_section == 0:  # 游戏选择区域
            if self.current_index >= len(sorted_games):
                self.current_index = len(sorted_games) - 1
        elif self.current_section == 1:  # 控制按钮区域
            if self.current_index >= len(self.control_buttons):
                self.current_index = len(self.control_buttons) - 1
        # 设置窗口透明度，当游戏运行时
        #if self.player:
        #    self.setWindowOpacity(0.95)
        #else:
        #    self.setWindowOpacity(1)
        # 更新游戏名称标签
        if self.current_section == 0:  # 游戏选择区域
            if self.more_section == 0 and self.current_index == self.buttonsindexset:  # 如果是"更多"按钮
                self.game_name_label.setText("所有软件")
            else:
                self.game_name_label.setText(sorted_games[self.current_index]["name"])

                # 检查当前游戏是否在运行
                current_game_name = sorted_games[self.current_index]["name"]
                is_running = current_game_name in self.player  # 假设 self.player 存储正在运行的游戏名称

                # 更新 favorite_button 的文本和样式
                if is_running:
                    self.favorite_button.setText("结束进程")
                    self.favorite_button.setStyleSheet(f"""
                        QPushButton {{
                            background-color: red; 
                            border-radius: {int(20 * self.scale_factor)}px; 
                            border: {int(2 * self.scale_factor)}px solid #888888;
                            color: white;
                            font-size: {int(16 * self.scale_factor)}px;
                        }}
                        QPushButton:hover {{
                            border: 0px solid transparent;
                        }}
                    """)
                else:
                    self.favorite_button.setText("收藏")
                    self.favorite_button.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent; 
                            border-radius: {int(20 * self.scale_factor)}px; 
                            border: {int(2 * self.scale_factor)}px solid #888888;
                            color: white;
                            font-size: {int(16 * self.scale_factor)}px;
                        }}
                        QPushButton:hover {{
                            border: {int(2 * self.scale_factor)}px solid #555555;
                        }}
                    """)

        if self.current_section == 0: 
            for index, button in enumerate(self.buttons):
                if index == self.current_index:
                    button.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #2e2e2e; 
                            border-radius: {int(10 * self.scale_factor2)}px; 
                            border: {int(3 * self.scale_factor2)}px solid #93ffff;
                        }}
                        QPushButton:hover {{
                            border: {int(3 * self.scale_factor2)}px solid #25ade7;
                        }}
                    """)
                    # 为高亮按钮添加发光阴影并做一次脉冲动画（保存引用防止被回收）
                    try:
                        effect = button.graphicsEffect()
                        if not isinstance(effect, QtWidgets.QGraphicsDropShadowEffect):
                            effect = None
                    except Exception:
                        effect = None
                    if effect is None:
                        try:
                            effect = QtWidgets.QGraphicsDropShadowEffect(button)
                            effect.setColor(QColor("#93ffff"))
                            effect.setBlurRadius(10)
                            effect.setOffset(0, 0)
                            button.setGraphicsEffect(effect)
                        except Exception:
                            effect = None
                    if effect is not None:
                        try:
                            anim = QPropertyAnimation(effect, b"blurRadius")
                            anim.setDuration(300)
                            anim.setStartValue(10)
                            anim.setKeyValueAt(0.5, 30)
                            anim.setEndValue(10)
                            try:
                                from PyQt5.QtCore import QEasingCurve
                                anim.setEasingCurve(QEasingCurve.InOutCubic)
                            except Exception:
                                pass
                            if not hasattr(self, '_highlight_anims'):
                                self._highlight_anims = {}
                            # 停止并替换已有动画
                            old = self._highlight_anims.get(button)
                            try:
                                if old and isinstance(old, QPropertyAnimation):
                                    old.stop()
                            except Exception:
                                pass
                            self._highlight_anims[button] = anim
                            def _on_highlight_finished():
                                try:
                                    # 保持最后状态，不立即删除效果
                                    pass
                                except Exception:
                                    pass
                            anim.finished.connect(_on_highlight_finished)
                            anim.start()
                        except Exception:
                            pass
                else:
                    button.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #2e2e2e; 
                            border-radius: {int(10 * self.scale_factor2)}px; 
                            border: {int(2 * self.scale_factor2)}px solid #444444;
                        }}
                        QPushButton:hover {{
                            border: {int(2 * self.scale_factor2)}px solid #888888;
                        }}
                    """)
                    # 移除之前可能存在的高亮动画
                    try:
                        if hasattr(self, '_highlight_anims') and button in self._highlight_anims:
                            old = self._highlight_anims.pop(button)
                            try:
                                old.stop()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    # 可选：移除效果以还原默认外观
                    try:
                        eff = button.graphicsEffect()
                        if isinstance(eff, QtWidgets.QGraphicsDropShadowEffect):
                            button.setGraphicsEffect(None)
                    except Exception:
                        pass
            for index, btn in enumerate(self.control_buttons):
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #3e3e3e;
                        border-radius: 62%;
                        font-size: {int(40 * self.scale_factor)}px; 
                        border: {int(5 * self.scale_factor)}px solid #282828;
                    }}
                    QPushButton:hover {{
                        border: {int(2 * self.scale_factor)}px solid #888888;
                    }}
                """)
            # 如果离开控制按钮区域，则隐藏任何残留的控制按钮标签
            self._hide_control_button_labels()
        elif self.current_section == 1:  # 控制按钮区域
            # 先隐藏旧标签一次，避免在循环中被多次删除/覆盖
            self._hide_control_button_labels()
            for index, btn in enumerate(self.control_buttons):
                if index == self.current_index:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #3e3e3e;
                            border-radius: 62%;
                            font-size: {int(40 * self.scale_factor)}px; 
                            border: {int(4 * self.scale_factor)}px solid #93ffff;
                        }}
                        QPushButton:hover {{
                            border: {int(4 * self.scale_factor)}px solid #25ade7;
                        }}
                    """)
                    # 只为选中按钮显示标签（前3个显示窗口名，其余显示固定中文名）
                    self._show_control_button_label(btn, index)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #3e3e3e;
                            border-radius: 62%;
                            font-size: {int(40 * self.scale_factor)}px; 
                            border: {int(5 * self.scale_factor)}px solid #282828;
                        }}
                        QPushButton:hover {{
                            border: {int(2 * self.scale_factor)}px solid #888888;
                        }}
                    """)
            for index, button in enumerate(self.buttons):
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #2e2e2e; 
                        border-radius: {int(10 * self.scale_factor2)}px; 
                        border: {int(2 * self.scale_factor2)}px solid #444444;
                    }}
                    QPushButton:hover {{
                        border: {int(2 * self.scale_factor2)}px solid #888888;
                    }}
                """)

        # 只在有按钮时进行滚动条调整
        #竖向滚动
        if self.buttons and self.current_section == 0 and self.more_section == 1:
            current_button = self.buttons[self.current_index]
            # 修正：获取按钮在scroll_widget中的准确位置
            button_pos = current_button.mapTo(self.scroll_widget, QPoint(0, 0))
            scroll_area_height = self.scroll_area.viewport().height()
            scroll_bar = self.scroll_area.verticalScrollBar()
            # 如果按钮顶部超出可视区域
            if button_pos.y() < scroll_bar.value():
                # 平滑滚动到目标位置
                self.animate_scroll('vertical', button_pos.y(), duration=150)
            # 如果按钮底部超出可视区域
            elif button_pos.y() + current_button.height() > scroll_bar.value() + scroll_area_height:
                self.animate_scroll('vertical', button_pos.y() + current_button.height() - scroll_area_height, duration=150)
        #固定2
        #if self.buttons:
        #    current_button = self.buttons[self.current_index]
        #    scroll_area_width = self.scroll_area.viewport().width()
        #    button_pos = current_button.mapTo(self.scroll_widget, QPoint(0, 0))
        #    button_width = current_button.width()
        #    
        #    if self.current_index == 0:
        #        # 第一个按钮，滚动到最左边
        #        self.scroll_area.horizontalScrollBar().setValue(0)
        #    elif self.current_index >= 1:
        #        # 从第二个按钮开始，将按钮对齐到第二个位置
        #        second_button_pos = self.buttons[1].mapTo(self.scroll_widget, QPoint(0, 0)).x()
        #        scroll_value = button_pos.x() - second_button_pos
        #        self.scroll_area.horizontalScrollBar().setValue(scroll_value)
        #横向排列
        if self.buttons and self.current_section == 0 and self.more_section == 0:
            current_button = self.buttons[self.current_index]
            scroll_area_width = self.scroll_area.viewport().width()
            button_pos = current_button.mapToGlobal(QPoint(0, 0))  # 获取按钮在屏幕中的绝对位置
            scroll_area_pos = self.scroll_area.mapToGlobal(QPoint(0, 0))  # 获取滚动区域在屏幕中的绝对位置
            button_width = current_button.width()
            offset = 100  # 偏移量，单位像素，可根据需要调整

            if self.current_index == 0:
                # 第一个按钮，平滑滚动到最左边
                self.animate_scroll('horizontal', 0, duration=150)
            elif self.current_index >= 1:
                button_pos = QPoint(current_button.mapToGlobal(QPoint(0, 0)))  # 获取当前按钮的精确位置
                scroll_value = self.scroll_area.horizontalScrollBar().value()  # 获取当前滚动值
                # 当靠近左边缘且左侧还有游戏时，稍微偏移一点让左侧游戏露出
                if button_pos.x() < scroll_area_pos.x() + offset and self.current_index > 0:
                    second_button_pos = self.buttons[0].mapToGlobal(QPoint(0, 0)).x()
                    scroll_value = button_pos.x() - second_button_pos - offset
                    self.animate_scroll('horizontal', scroll_value, duration=150)
                # 当靠近右边缘且移动距离大于3时调整滚动
                elif button_pos.x() + button_width > scroll_area_pos.x() + scroll_area_width:
                    second_button_pos = self.buttons[min(3, len(self.buttons) - 1)].mapToGlobal(QPoint(0, 0)).x()
                    scroll_value = button_pos.x() - second_button_pos
                    self.animate_scroll('horizontal', scroll_value, duration=150)
        #
        #self.game_name_label.move(button_pos.x(), button_pos.y() - self.game_name_label.height())
        #self.game_name_label.show()
        # 新增文本显示，复制game_name_label的内容
        if self.current_section == 0 and self.more_section == 0: 
            self.game_name_label.setStyleSheet(f"""QLabel {{color: #1e1e1e;}}""")
            button_pos = current_button.mapToGlobal(QPoint(0, 0))  # 重新加载按钮的最新位置
            if hasattr(self, 'additional_game_name_label') and isinstance(self.additional_game_name_label, QLabel):
                # 如果已有 label，则做淡出动画后删除
                try:
                    old_label = self.additional_game_name_label
                    try:
                        eff_old = old_label.graphicsEffect()
                        if not isinstance(eff_old, QtWidgets.QGraphicsOpacityEffect):
                            eff_old = None
                    except Exception:
                        eff_old = None
                    if eff_old is None:
                        try:
                            eff_old = QtWidgets.QGraphicsOpacityEffect(old_label)
                            old_label.setGraphicsEffect(eff_old)
                        except Exception:
                            eff_old = None
                    if eff_old is not None:
                        fade_out = QPropertyAnimation(eff_old, b"opacity")
                        fade_out.setDuration(180)
                        fade_out.setStartValue(1.0)
                        fade_out.setEndValue(0.0)
                        def _del_old():
                            try:
                                old_label.deleteLater()
                            except Exception:
                                pass
                        fade_out.finished.connect(_del_old)
                        # 保存引用
                        if not hasattr(self, '_label_fade_anims'):
                            self._label_fade_anims = []
                        self._label_fade_anims.append(fade_out)
                        fade_out.start()
                    else:
                        try:
                            old_label.deleteLater()
                        except Exception:
                            pass
                except RuntimeError:
                    pass  # 如果对象已被删除，忽略错误
            else:
                QTimer.singleShot(200, self.update_highlight)  # 延迟200毫秒后调用update_highlight
            self.additional_game_name_label = QLabel(self.game_name_label.text(), self)
            self.additional_game_name_label.setAlignment(Qt.AlignCenter)  # 设置文本居中
            self.additional_game_name_label.setStyleSheet(f"""
                QLabel {{
                    font-family: "Microsoft YaHei"; 
                    color: white;
                    font-size: {int(20 * self.scale_factor*1.5)}px;
                    background: transparent;
                }}
            """)
            # 添加不透明度效果并淡入
            try:
                eff = QtWidgets.QGraphicsOpacityEffect(self.additional_game_name_label)
                self.additional_game_name_label.setGraphicsEffect(eff)
                eff.setOpacity(0.0)
                fade_in_lbl = QPropertyAnimation(eff, b"opacity")
                fade_in_lbl.setDuration(180)
                fade_in_lbl.setStartValue(0.0)
                fade_in_lbl.setEndValue(1.0)
                if not hasattr(self, '_label_fade_anims'):
                    self._label_fade_anims = []
                self._label_fade_anims.append(fade_in_lbl)
                fade_in_lbl.start()
            except Exception:
                pass
        # background-color: #575757;    
        # border-radius: 10px;          
        # border: 2px solid #282828;
            self.additional_game_name_label.adjustSize()  # 调整标签大小以适应文本
            #print(self.game_name_label.text(), button_pos.x(), button_pos.x() + (button_width - self.additional_game_name_label.width()) // 2, button_pos.y() - self.game_name_label.height() - 20)
            self.additional_game_name_label.move(button_pos.x() + (button_width - self.additional_game_name_label.width()) // 2, button_pos.y() - self.game_name_label.height() - 20)  # 居中在按钮中央
            self.additional_game_name_label.show()
        elif self.current_section == 1:
            if hasattr(self, 'additional_game_name_label') and isinstance(self.additional_game_name_label, QLabel):
                try:
                    self.additional_game_name_label.deleteLater()  # 删除之前生成的 additional_game_name_label
                except RuntimeError:
                    pass
        else:
            if hasattr(self, 'additional_game_name_label') and isinstance(self.additional_game_name_label, QLabel):
                try:
                    self.additional_game_name_label.deleteLater()  # 删除之前生成的 additional_game_name_label
                    # 设置game_name_label的颜色
                    self.game_name_label.setStyleSheet(f"""
                        QLabel {{
                            font-family: "Microsoft YaHei";
                            color: white;
                            font-size: {int(20 * self.scale_factor*1.5)}px; 
                            background: transparent;
                        }}
                    """)
                except RuntimeError:
                    pass
        #    current_button = self.buttons[self.current_index]
        #    scroll_area_width = self.scroll_area.viewport().width()
        #    button_pos = current_button.mapTo(self.scroll_widget, QPoint(0, 0))
        #    button_width = current_button.width()
        #    if self.current_index == 0:
        #        # 第一个按钮，滚动到最左边
        #        self.scroll_area.horizontalScrollBar().setValue(0)
        #        self.last_scroll_index = 0
        #    elif self.current_index >= 1:
        #        # 使用QPoint实现精确定位并改进调整滚动的方式
        #        button_pos = QPoint(current_button.mapTo(self.scroll_widget, QPoint(0, 0)))  # 获取当前按钮的精确位置
        #        scroll_value = self.scroll_area.horizontalScrollBar().value()  # 获取当前滚动值
        #        
        #        # 计算移动距离
        #        move_distance = abs(self.current_index - (self.last_scroll_index or 0))
        #        print(button_pos.x(),button_width,scroll_area_width)
        #        # 当靠近左边缘且移动距离大于3时调整滚动 and move_distance < 3
        #        if button_pos.x() < 0:
        #            if self.current_index > self.last_scroll_index:
        #                return
        #            print('<',self.current_index, self.last_scroll_index, move_distance)
        #            scroll_value = max(0, button_pos.x())  # 确保滚动值不小于0
        #            self.scroll_area.horizontalScrollBar().setValue(scroll_value)
        #            self.last_scroll_index = self.current_index
        #        
        #        # 当靠近右边缘且移动距离大于3时调整滚动
        #        elif button_pos.x() + button_width > scroll_area_width:
        #            if self.current_index < self.last_scroll_index:
        #                return
        #            print(">",self.current_index, self.last_scroll_index, move_distance)
        #            scroll_value = button_pos.x() + button_width - scroll_area_width
        #            self.scroll_area.horizontalScrollBar().setValue(scroll_value)
        #            self.last_scroll_index = self.current_index
            #if button_pos.x() < 0:
            #    # 如果按钮超出左边界，调整滚动值
            #    self.scroll_area.horizontalScrollBar().setValue(scroll_value + button_pos.x())
            #elif button_pos.x() + button_width > scroll_area_width:
            #    # 如果按钮超出右边界，调整滚动值
            #    self.scroll_area.horizontalScrollBar().setValue(scroll_value + (button_pos.x() + button_width - scroll_area_width))
    # 暂时去除键盘导航功能
    def move_selection(self, offset):
        """移动选择的游戏"""
        total_buttons = len(self.buttons)
        new_index = self.current_index + offset

        # 上下键逻辑，循环跳转
        if offset == -self.row_count:  # 上移一行
            if new_index < 0:
                column = self.current_index % self.row_count
                new_index = (total_buttons - 1) - (total_buttons - 1) % self.row_count + column
                if new_index >= total_buttons:
                    new_index -= self.row_count
        elif offset == self.row_count:  # 下移一行
            if new_index >= total_buttons:
                column = self.current_index % self.row_count
                new_index = column

        # 左右键逻辑，循环跳转
        if offset == -1 and new_index < 0:
            new_index = total_buttons - 1
        elif offset == 1 and new_index >= total_buttons:
            new_index = 0

        # 更新索引并高亮
        self.current_index = new_index
        self.update_highlight()
    
    # ===== 控制按钮标签显示方法 =====
    def _capture_window_thumbnail(self, hwnd, width=160, height=120):
        """捕获窗口的缩略图（使用 PrintWindow + Pillow，返回 QPixmap）"""
        # 如果窗口最小化或不可见，跳过
        if ctypes.windll.user32.IsIconic(hwnd) or not ctypes.windll.user32.IsWindowVisible(hwnd):
            return None
    
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            return None

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bitmap)
        ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)

        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)

        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        # 从 BGRA 原始字节创建 Pillow 图像（不依赖 numpy）
        pil_img = Image.frombuffer("RGBA", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRA", 0, 1)

        # 将 Pillow 图像数据转为 QtImage
        data = pil_img.tobytes("raw", "RGBA")
        try:
            qimg = QtGui.QImage(data, pil_img.width, pil_img.height, QtGui.QImage.Format_RGBA8888)
        except AttributeError:
            # 兼容老版 PyQt5，尝试 ARGB32 并交换通道
            qimg = QtGui.QImage(data, pil_img.width, pil_img.height, QtGui.QImage.Format_ARGB32)
            qimg = qimg.rgbSwapped()

        pixmap = QPixmap.fromImage(qimg)
        pixmap = pixmap.scaledToWidth(width, Qt.SmoothTransformation)
        return pixmap

    def _show_control_button_label(self, btn, index):
        """在控制按钮上方显示窗口缩略图，下方显示文字标签"""
        # 支持两类标签：
        # - index < 3: 使用 btn.window_info['title']（若存在）
        # - index >=3: 使用固定中文名称映射
        labels_map = {
            3: '鼠标模拟',
            4: '显示地图',
            5: '系统休眠',
            6: '系统关机'
        }

        title = ''
        if index < 3 and hasattr(btn, 'window_info') and btn.window_info:
            title = btn.window_info.get('title', '')
        if not title:
            title = labels_map.get(index, '')
        if not title:
            return

        if len(title) > 15:
            title = title[:15] + '...'

        # 先隐藏旧标签（淡出）
        self._hide_control_button_labels()

        # 计算位置
        try:
            btn_pos = btn.mapToGlobal(QPoint(0, 0))
            btn_size = btn.size()
        except Exception:
            btn_pos = QPoint(0, 0)
            btn_size = btn.size() if hasattr(btn, 'size') else QSize(0, 0)

        # ===== 显示窗口缩略图（上方）=====
        if index < 3 and hasattr(btn, 'window_info') and btn.window_info:
            hwnd = btn.window_info.get('hwnd')
            if hwnd:
                thumbnail = self._capture_window_thumbnail(hwnd, width=160, height=120)
                if thumbnail:
                    thumbnail_label = QLabel(self)
                    thumbnail_label.setPixmap(thumbnail)
                    thumbnail_label.setStyleSheet(f"""
                        QLabel {{
                            background-color: rgba(30, 30, 30, 0.9);
                            border: 2px solid #555555;
                            border-radius: {int(8 * self.scale_factor)}px;
                            padding: {int(4 * self.scale_factor)}px;
                        }}
                    """)
                    thumbnail_label.adjustSize()
                    
                    # 计算缩略图位置（按钮上方居中）
                    thumb_x = btn_pos.x() + (btn_size.width() - thumbnail.width()) // 2
                    thumb_y = btn_pos.y() - thumbnail.height() - int(20 * self.scale_factor)
                    thumbnail_label.move(thumb_x, thumb_y)
                    
                    # 淡入动画
                    try:
                        eff = QtWidgets.QGraphicsOpacityEffect(thumbnail_label)
                        thumbnail_label.setGraphicsEffect(eff)
                        eff.setOpacity(0.0)
                        fade_in = QPropertyAnimation(eff, b"opacity")
                        fade_in.setDuration(180)
                        fade_in.setStartValue(0.0)
                        fade_in.setEndValue(1.0)
                        if not hasattr(self, '_label_fade_anims'):
                            self._label_fade_anims = []
                        self._label_fade_anims.append(fade_in)
                        fade_in.start()
                    except Exception:
                        pass
                    
                    thumbnail_label.show()
                    self._current_control_button_thumbnail = thumbnail_label

        # ===== 显示文字标签（下方）=====
        # 创建并样式化标签
        label = QLabel(title, self)
        label.setAlignment(Qt.AlignCenter)
        # 使用与 game_name_label 相同的样式：白色、大号字体
        label.setStyleSheet(f"""
            QLabel {{
                font-family: "Microsoft YaHei";
                color: white;
                font-size: {int(16 * self.scale_factor * 1.5)}px;
                background: transparent;
            }}
        """)

        label.adjustSize()
        label_x = btn_pos.x() + (btn_size.width() - label.width()) // 2
        label_y = btn_pos.y() + btn_size.height() + int(10 * self.scale_factor)
        label.move(label_x, label_y)

        # 淡入动画
        try:
            eff = QtWidgets.QGraphicsOpacityEffect(label)
            label.setGraphicsEffect(eff)
            eff.setOpacity(0.0)
            fade_in = QPropertyAnimation(eff, b"opacity")
            fade_in.setDuration(180)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            if not hasattr(self, '_label_fade_anims'):
                self._label_fade_anims = []
            self._label_fade_anims.append(fade_in)
            fade_in.start()
        except Exception:
            pass

        label.show()
        self._current_control_button_label = label
    
    def _hide_control_button_labels(self):
        """隐藏所有控制按钮标签和缩略图"""
        # 隐藏缩略图
        if hasattr(self, '_current_control_button_thumbnail') and self._current_control_button_thumbnail:
            try:
                old_thumb = self._current_control_button_thumbnail
                try:
                    eff_old_thumb = old_thumb.graphicsEffect()
                    if not isinstance(eff_old_thumb, QtWidgets.QGraphicsOpacityEffect):
                        eff_old_thumb = None
                except Exception:
                    eff_old_thumb = None
                if eff_old_thumb is None:
                    try:
                        eff_old_thumb = QtWidgets.QGraphicsOpacityEffect(old_thumb)
                        old_thumb.setGraphicsEffect(eff_old_thumb)
                    except Exception:
                        eff_old_thumb = None
                if eff_old_thumb is not None:
                    fade_out_thumb = QPropertyAnimation(eff_old_thumb, b"opacity")
                    fade_out_thumb.setDuration(180)
                    fade_out_thumb.setStartValue(1.0)
                    fade_out_thumb.setEndValue(0.0)
                    def _del_old_thumb():
                        try:
                            old_thumb.deleteLater()
                        except Exception:
                            pass
                    fade_out_thumb.finished.connect(_del_old_thumb)
                    if not hasattr(self, '_label_fade_anims'):
                        self._label_fade_anims = []
                    self._label_fade_anims.append(fade_out_thumb)
                    fade_out_thumb.start()
                else:
                    try:
                        old_thumb.deleteLater()
                    except Exception:
                        pass
            except RuntimeError:
                pass
            self._current_control_button_thumbnail = None
        
        # 隐藏标签
        if hasattr(self, '_current_control_button_label') and self._current_control_button_label:
            try:
                old_label = self._current_control_button_label
                try:
                    eff_old = old_label.graphicsEffect()
                    if not isinstance(eff_old, QtWidgets.QGraphicsOpacityEffect):
                        eff_old = None
                except Exception:
                    eff_old = None
                if eff_old is None:
                    try:
                        eff_old = QtWidgets.QGraphicsOpacityEffect(old_label)
                        old_label.setGraphicsEffect(eff_old)
                    except Exception:
                        eff_old = None
                if eff_old is not None:
                    fade_out = QPropertyAnimation(eff_old, b"opacity")
                    fade_out.setDuration(180)
                    fade_out.setStartValue(1.0)
                    fade_out.setEndValue(0.0)
                    def _del_old():
                        try:
                            old_label.deleteLater()
                        except Exception:
                            pass
                    fade_out.finished.connect(_del_old)
                    if not hasattr(self, '_label_fade_anims'):
                        self._label_fade_anims = []
                    self._label_fade_anims.append(fade_out)
                    fade_out.start()
                else:
                    try:
                        old_label.deleteLater()
                    except Exception:
                        pass
            except RuntimeError:
                pass
            self._current_control_button_label = None
    
    # ===== 后台任务切换相关方法 =====
    def get_running_windows(self):
        """获取所有正在运行的窗口列表，排除系统窗口"""
        windows = []
        def enum_window_callback(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                # 过滤掉标题为空或系统窗口
                if title and title.strip():
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        process = psutil.Process(pid)
                        exe_path = process.exe()
                        exe_name = os.path.basename(exe_path)
                        # 过滤掉系统进程
                        if exe_name.lower() not in ['explorer.exe', 'svchost.exe', 'csrss.exe', 'dwm.exe']:
                            windows.append({
                                'hwnd': hwnd,
                                'title': title,
                                'pid': pid,
                                'exe_path': exe_path,
                                'exe_name': exe_name
                            })
                    except Exception:
                        pass
            return True
        
        win32gui.EnumWindows(enum_window_callback, None)
        return windows
    
    def get_window_icon(self, exe_path, size=40):
        """从可执行文件获取图标"""
        icon = QIcon()
        try:
            from icoextract import IconExtractor
            extractor = IconExtractor(exe_path)
            bio = extractor.get_icon(num=0)
            data = bio.getvalue()
            pix = QPixmap()
            if pix.loadFromData(data):
                pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon = QIcon(pix)
                return icon
        except Exception:
            pass
        
        # 尝试使用系统默认方式获取图标
        try:
            # 尝试从应用本身获取图标（通过文件管理器API）
            from PIL import Image
            import io
            
            # 使用 Windows 图标缓存
            result = ctypes.windll.shell32.ExtractIconW(None, exe_path, 0)
            if result:
                # 将句柄转换为 QPixmap（这比较复杂，通常不推荐）
                return QIcon()
        except Exception:
            pass
        
        return icon
    
    def update_background_windows(self):
        """更新后台窗口列表"""
        self.background_windows = self.get_running_windows()
    
    def update_background_buttons(self):
        """更新前3个按钮的显示，显示后台应用程序图标"""
        self.update_background_windows()
        
        # 显示前3个后台应用图标
        for i in range(3):
            btn = self.control_buttons[i]
            if i < len(self.background_windows):
                window_info = self.background_windows[i]
                # 不设置文本，仅保存窗口信息
                btn.setText('')  # 清空文本
                
                # 尝试设置图标
                icon = self.get_window_icon(window_info['exe_path'], size=int(50 * self.scale_factor))
                if icon:
                    btn.setIcon(icon)
                    btn.setIconSize(QSize(int(50 * self.scale_factor), int(50 * self.scale_factor)))
                
                # 保存窗口信息到按钮（用于点击时调用）
                btn.window_info = window_info
                btn.setVisible(True)
            else:
                btn.setText('')
                btn.setIcon(QIcon())
                btn.window_info = None
                btn.setVisible(True)
        
        # 如果有超过3个后台应用，添加额外按钮容器
        if len(self.background_windows) > 3:
            self.create_extra_background_buttons()
    
    def on_background_button_clicked(self, button_index):
        """处理后台任务按钮点击事件"""
        btn = self.control_buttons[button_index]
        if hasattr(btn, 'window_info') and btn.window_info:
            window_info = btn.window_info
            hwnd = window_info['hwnd']
            # 恢复窗口
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            self.hide_window()
    
    def create_extra_background_buttons(self):
        """为超过3个的后台应用在 left_label 后面创建按钮"""
        # 确保texta_layout和left_label已经初始化
        if not hasattr(self, 'texta_layout') or not self.texta_layout or not hasattr(self, 'left_label') or not self.left_label:
            return
        
        # 如果少于等于3个应用，不需要额外按钮
        if len(self.background_windows) <= 3:
            # 移除所有额外按钮
            # 首先检查当前布局中是否已经有额外按钮
            current_extra_buttons = []
            for i in range(self.texta_layout.count()):
                widget = self.texta_layout.itemAt(i).widget()
                if widget and widget != self.left_label and widget != self.right_label:
                    current_extra_buttons.append(widget)
            
            # 移除所有当前的额外按钮
            for widget in current_extra_buttons:
                try:
                    self.texta_layout.removeWidget(widget)
                    widget.deleteLater()
                except Exception as e:
                    print(f"Error removing extra buttons: {e}")
            
            # 更新布局
            self.texta_layout.update()
            if self.texta_layout.parentWidget():
                self.texta_layout.parentWidget().update()
            return
        
        # 移除旧的额外按钮
        current_extra_buttons = []
        for i in range(self.texta_layout.count()):
            widget = self.texta_layout.itemAt(i).widget()
            if widget and widget != self.left_label and widget != self.right_label:
                current_extra_buttons.append(widget)
        
        # 移除所有当前的额外按钮
        for widget in current_extra_buttons:
            try:
                self.texta_layout.removeWidget(widget)
                widget.deleteLater()
            except Exception as e:
                print(f"Error removing old extra buttons: {e}")
        
        # 为超过3个的应用添加一个大按钮
        if len(self.background_windows) > 3:
            # 获取所有额外应用的图标（放大一倍）
            extra_icons = []
            for i in range(3, len(self.background_windows)):
                window_info = self.background_windows[i]
                icon = self.get_window_icon(window_info['exe_path'], size=int(36 * self.scale_factor))  # 放大一倍图标
                if icon:
                    extra_icons.append(icon.pixmap(QSize(int(36 * self.scale_factor), int(36 * self.scale_factor))))
            
            btn = QPushButton()
            # 计算长条形按钮尺寸（放大一倍）
            icon_size = int(16 * self.scale_factor) 
            spacing = int(6 * self.scale_factor)    # 增加间距
            btn_width = len(extra_icons) * icon_size *2 + (len(extra_icons) - 1) * spacing + int(24 * self.scale_factor)
            btn_height = int(50 * self.scale_factor)  
            btn.setFixedSize(btn_width, btn_height)

            
            # 设置样式
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1e1e1e;
                    border-radius: {int(8 * self.scale_factor)}px;
                    border: 0px solid transparent;
                    margin-left: 0px;
                    margin-right: {int(10 * self.scale_factor)}px;
                    text-align: left;
                    padding-left: {int(12 * self.scale_factor)}px;
                    padding-right: {int(12 * self.scale_factor)}px;
                }}
                QPushButton:hover {{
                    background-color: #2e2e2e;
                    border: {int(2 * self.scale_factor)}px solid #555555;
                }}
            """)
            
            # 创建合成图标
            if extra_icons:
                # 计算合成图标大小（放大一倍）
                max_cols = len(extra_icons)  # 只显示一排
                num_icons = len(extra_icons)
                
                icon_size = int(36 * self.scale_factor)
                spacing = int(6 * self.scale_factor)
                composite_size = QSize(
                    num_icons * icon_size + (num_icons - 1) * spacing,
                    icon_size
                )
                
                # 创建合成图像
                composite_pixmap = QPixmap(composite_size)
                composite_pixmap.fill(Qt.transparent)  # 设置背景透明
                
                painter = QPainter(composite_pixmap)
                
                # 绘制所有图标（只显示一排，放大一倍）
                for i, pixmap in enumerate(extra_icons):
                    x = i * (icon_size + spacing)
                    y = 0
                    painter.drawPixmap(x, y, pixmap)
                
                painter.end()
                
                # 设置合成图标到按钮
                btn.setIcon(QIcon(composite_pixmap))
                btn.setIconSize(composite_size)
            else:
                # 如果没有图标，显示额外应用的数量
                extra_apps_count = len(self.background_windows) - 3
                # 调整按钮宽度以适应文本（放大一倍）
                btn_width = int(80 * self.scale_factor) + len(str(extra_apps_count)) * int(24 * self.scale_factor)
                btn_height = int(60 * self.scale_factor)
                btn.setFixedSize(btn_width, btn_height)
                btn.setText(f"+{extra_apps_count}")
                btn.setStyleSheet(btn.styleSheet() + f"font-size: {int(36 * self.scale_factor)}px;")
            # 点击额外按钮时，切换所有按钮到后台任务模式
            btn.clicked.connect(self.switch_all_buttons_to_background_mode)
            
            # 直接添加到texta_layout中，位于left_label之后，设置靠左对齐并设置固定宽度
            left_label_index = self.texta_layout.indexOf(self.left_label)
            if left_label_index >= 0:
                # 先移除右侧标签
                right_label_index = self.texta_layout.indexOf(self.right_label)
                if right_label_index >= 0:
                    self.texta_layout.takeAt(right_label_index)
                
                # 添加按钮
                self.texta_layout.insertWidget(left_label_index + 1, btn, alignment=Qt.AlignLeft)
                
                # 添加一个伸缩空间
                self.texta_layout.addStretch()
                
                # 重新添加右侧标签
                self.texta_layout.addWidget(self.right_label, alignment=Qt.AlignRight)
        
        # 更新布局
        self.texta_layout.update()
        if self.texta_layout.parentWidget():
            self.texta_layout.parentWidget().update()
    
    def switch_all_buttons_to_background_mode(self):
        """将所有按钮切换为后台任务模式"""
        # 重新获取后台窗口列表
        self.update_background_windows()
        
        # 清除所有点击事件并重新配置
        # 使用后台任务数来确定需要切换的按钮数量
        for i in range(min(len(self.background_windows), len(self.control_buttons))):
            btn = self.control_buttons[i]
            # 断开旧信号
            try:
                btn.clicked.disconnect()
            except TypeError:
                pass
            
            if i < len(self.background_windows):
                window_info = self.background_windows[i]
                title = window_info['title']
                if len(title) > 10:
                    title = title[:10] + '...'
                btn.setText(title)
                
                icon = self.get_window_icon(window_info['exe_path'], size=int(50 * self.scale_factor))
                if icon:
                    btn.setIcon(icon)
                    btn.setIconSize(QSize(int(50 * self.scale_factor), int(50 * self.scale_factor)))
                
                btn.window_info = window_info
                btn.clicked.connect(lambda checked=False, info=window_info: self.restore_background_window(info))
                btn.setVisible(True)
            else:
                btn.setText('')
                btn.setIcon(QIcon())
                btn.window_info = None
                btn.setVisible(True)
        
        # 隐藏多余的按钮
        for i in range(len(self.background_windows), len(self.control_buttons)):
            if i < len(self.control_buttons):
                btn = self.control_buttons[i]
                btn.setText('')
                btn.setIcon(QIcon())
                btn.window_info = None
                btn.setVisible(True)
    
    def restore_background_window(self, window_info):
        """恢复后台窗口"""
        hwnd = window_info['hwnd']
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        self.hide_window()

    # 焦点检测
    def gsfocus(self):
        # 获取当前活动窗口句柄
        hwnd = win32gui.GetForegroundWindow()
        if hwnd == GSHWND or globals().get("FSPREVIEWHWND", None) is not None and hwnd == globals().get("FSPREVIEWHWND"):
            return True
        else:
            return False
    
    def restore_window(self, game_path):
        self.hide_window()
        for process in psutil.process_iter(['pid', 'exe']):
                    try:
                        if process.info['exe'] and process.info['exe'].lower() == game_path.lower():
                            pid = process.info['pid']

                            # 查找进程对应的窗口
                            def enum_window_callback(hwnd, lParam):
                                _, current_pid = win32process.GetWindowThreadProcessId(hwnd)
                                if current_pid == pid:
                                    # 获取窗口的可见性
                                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                                    # 如果窗口的样式包含 WS_VISIBLE，则表示该窗口是可见的
                                    if style & win32con.WS_VISIBLE:
                                        # 恢复窗口并将其置前
                                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                                        win32gui.SetForegroundWindow(hwnd)
                                        print(f"已将进程 {pid} 的窗口带到前台")
                                        self.switch_to_main_interface()

                            # 枚举所有窗口
                            win32gui.EnumWindows(enum_window_callback, None)
                            return
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
    def launch_game(self, index):
        """启动选中的游戏"""
        sorted_games = self.sort_games()
        game = sorted_games[index]
        game_cmd = game["cmd"]
        game_name = game["name"]
        image_path = game.get("image-path", "")
        if not os.path.isabs(image_path):
            image_path = f"{APP_INSTALL_PATH}\\config\\covers\\{image_path}"
        self.ignore_input_until = pygame.time.get_ticks() + 600

        # 点击反馈：对被点击的按钮触发更大幅度的脉冲动画（保持引用以防被回收）
        try:
            if 0 <= index < len(self.buttons):
                clicked_btn = self.buttons[index]
                try:
                    eff = clicked_btn.graphicsEffect()
                    if not isinstance(eff, QtWidgets.QGraphicsDropShadowEffect):
                        eff = None
                except Exception:
                    eff = None
                if eff is None:
                    try:
                        eff = QtWidgets.QGraphicsDropShadowEffect(clicked_btn)
                        eff.setColor(QColor("#93ffff"))
                        eff.setBlurRadius(10)
                        eff.setOffset(0, 0)
                        clicked_btn.setGraphicsEffect(eff)
                    except Exception:
                        eff = None
                if eff is not None:
                    try:
                        pulse = QPropertyAnimation(eff, b"blurRadius")
                        pulse.setDuration(200)
                        pulse.setStartValue(10)
                        pulse.setKeyValueAt(0.2, 120)
                        pulse.setEndValue(10)
                        try:
                            from PyQt5.QtCore import QEasingCurve
                            pulse.setEasingCurve(QEasingCurve.OutCubic)
                        except Exception:
                            pass
                        if not hasattr(self, '_click_pulse_anims'):
                            self._click_pulse_anims = []
                        self._click_pulse_anims.append(pulse)
                        pulse.start()
                        # 阻塞当前函数直到动画结束，但保持 UI 响应（使用本地事件循环）
                        try:
                            from PyQt5.QtCore import QEventLoop
                            loop = QEventLoop()
                            pulse.finished.connect(loop.quit)
                            try:
                                loop.exec_()
                            except AttributeError:
                                loop.exec()
                        except Exception:
                            pass
                    except Exception:
                        pass
        except Exception:
            pass

        if self.more_section == 0 and self.current_index == self.buttonsindexset: # 如果点击的是"更多"按钮
            self.switch_to_all_software()
            return
        #冻结相关
        if os.path.exists("./_internal/pssuspend64.exe") and self.freeze:
            for app in valid_apps:
                if app["name"] == game_name:
                    game_path = app["path"]
                    break
            else:
                game_path = None
            if game_path:
                for process in psutil.process_iter(['pid', 'exe', 'status']):
                    try:
                        if process.info['exe'] and process.info['exe'].lower() == game_path.lower():
                            # 检查进程状态是否为挂起（Windows下为 'stopped'）
                            if process.status() == psutil.STATUS_STOPPED:
                                # 恢复挂起
                                subprocess.Popen(
                                    ['./_internal/pssuspend64.exe', '-r', os.path.basename(game_path)],
                                    creationflags=subprocess.CREATE_NO_WINDOW
                                )
                                time.sleep(0.5)  # 等待恢复
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
        # 恢复窗口
        if game["name"] in self.player:
            for app in valid_apps:
                if app["name"] == game["name"]:
                    game_path = app["path"]
                    break
            self.restore_window(game_path)
            return
        if self.player:
            # 创建确认弹窗
            self.confirm_dialog = ConfirmDialog("已经打开了一个游戏，还要再打开一个吗？", scale_factor=self.scale_factor)
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  # 设置屏蔽时间为800毫秒
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            else:
                pass
        self.launch_overlay.show_launch_window(game_name, image_path)
        self.switch_to_main_interface()
        self.current_index = 0  # 从第一个按钮开始
        # 更新最近游玩列表
        if game["name"] in settings["last_played"]:
            settings["last_played"].remove(game["name"])
        settings["last_played"].insert(0, game["name"])
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

        self.reload_interface()
        self.ignore_input_until = pygame.time.get_ticks() + 1000
        # 新增：如果该游戏在 on_mapping_clicked 里，自动开启鼠标映射
        if "on_mapping_clicked" in settings and game_name in settings["on_mapping_clicked"]:
            self.mouse_simulation()
        # 启动关联工具（避免重复启动）
        for item in settings.get("custom_tools", []):
            if item["name"] == game_name:
                for tool in item.get("tools", []):
                    tool_path = tool.get("path")
                    if tool_path and os.path.exists(tool_path):
                        # 检查是否已运行
                        already_running = False
                        for proc in psutil.process_iter(['exe']):
                            try:
                                if proc.info['exe'] and os.path.abspath(proc.info['exe']) == os.path.abspath(tool_path):
                                    already_running = True
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                continue
                        if not already_running:
                            subprocess.Popen(tool_path, shell=True)
        if game_cmd:
            #self.showMinimized()
            # subprocess.Popen(game_cmd, shell=True)
            os.startfile(game_cmd)  # 使用os.startfile启动游戏
            #self.showFullScreen()
            return
        # 新增：处理detached字段，优先启动detached中的.url
        detached_list = game.get("detached", [])
        if detached_list:
            url_path = detached_list[0].strip('"')  # 去掉前后引号
            if url_path.lower().endswith('.url'):
                os.startfile(url_path)
            # 检查 game["name"] 是否能在 valid_apps["name"] 里找到
            if not any(app["name"] == game["name"] for app in valid_apps):
                print(f"未在 valid_apps 中找到 {game['name']}")
                # 创建确认弹窗
                self.confirm_dialog = ConfirmDialog("该游戏未绑定进程\n点击确定后将打开自定义进程页面", scale_factor=self.scale_factor)
                result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
                self.ignore_input_until = pygame.time.get_ticks() + 350  # 设置屏蔽时间为800毫秒
                if result == QDialog.Accepted:  # 如果按钮被点击
                    self.custom_valid_show(game["name"])
                    return
    def custom_valid_show(self, gamename):
        settings_window = SettingsWindow(self)
        settings_window.show_custom_valid_apps_dialog()
        def fill_name_and_show():
            # 找到刚刚弹出的dialog中的name_edit并填充
            # 由于show_custom_valid_apps_dialog内部定义了name_edit变量，需通过遍历子控件查找
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, QDialog) and widget.windowTitle() == "添加自定义游戏进程":
                    for child in widget.findChildren(QLineEdit):
                        if child.placeholderText().startswith("点击选择游戏名称"):
                            child.setText(gamename)
                            break
                    break
        QTimer.singleShot(100, fill_name_and_show)
    # 判断当前窗口是否全屏(当设置中开启时)
    def is_current_window_fullscreen(self):
        try:
            # 获取当前活动窗口句柄
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                print("未找到活动窗口")
                return False  # 未找到活动窗口
    
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(pid)
                exe_path = process.exe()
                exe_name = os.path.basename(exe_path)
            except e:
                print(f"获取进程信息失败: {e}")
            if exe_name == "explorer.exe":
                print("当前窗口为桌面")
                return False  # 忽略桌面
            # 获取屏幕分辨率
            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    
            # 获取窗口位置和大小
            rect = win32gui.GetWindowRect(hwnd)
            window_width = rect[2] - rect[0]
            window_height = rect[3] - rect[1]
    
            # 判断窗口是否全屏
            if window_width == screen_width and window_height == screen_height:
                print(f"当前窗口已全屏{exe_name}")
                ShowWindow = ctypes.windll.user32.ShowWindow
                SW_MINIMIZE = 6
                # 最小化窗口
                ShowWindow(hwnd, SW_MINIMIZE)
                #冻结相关
                if self.freeze:
                    if os.path.exists("./_internal/pssuspend64.exe"):
                        pass_exe=['DesktopGame.exe', 'ZFGameBrowser.exe', 'amdow.exe', 'audiodg.exe', 'cmd.exe', 'cncmd.exe', 'copyq.exe', 'frpc.exe', 'gamingservicesnet.exe', 'memreduct.exe', 'mmcrashpad_handler64.exe','GameBarPresenceWriter.exe', 'HipsTray.exe', 'HsFreezer.exe', 'HsFreezerMagiaMove.exe', 'PhoneExperienceHost.exe','PixPin.exe', 'PresentMon-x64.exe','msedgewebview2.exe', 'plugin_host-3.3.exe', 'plugin_host-3.8.exe','explorer.exe','System Idle Process', 'System', 'svchost.exe', 'Registry', 'smss.exe', 'csrss.exe', 'wininit.exe', 'winlogon.exe', 'services.exe', 'lsass.exe', 'atiesrxx.exe', 'amdfendrsr.exe', 'atieclxx.exe', 'MemCompression', 'ZhuDongFangYu.exe', 'wsctrlsvc.exe', 'AggregatorHost.exe', 'wlanext.exe', 'conhost.exe', 'spoolsv.exe', 'reWASDService.exe', 'AppleMobileDeviceService.exe', 'ABService.exe', 'mDNSResponder.exe', 'Everything.exe', 'SunloginClient.exe', 'RtkAudUService64.exe', 'gamingservices.exe', 'SearchIndexer.exe', 'MoUsoCoreWorker.exe', 'SecurityHealthService.exe', 'HsFreezerEx.exe', 'GameInputSvc.exe', 'TrafficProt.exe', 'HipsDaemon.exe','python.exe', 'pythonw.exe', 'qmbrowser.exe', 'reWASDEngine.exe', 'sihost.exe', 'sublime_text.exe', 'taskhostw.exe', 'SearchProtocolHost.exe','crash_handler.exe', 'crashpad_handler.exe', 'ctfmon.exe', 'dasHost.exe', 'dllhost.exe', 'dwm.exe', 'fontdrvhost.exe','RuntimeBroker.exe','taskhostw.exe''WeChatAppEx.exe', 'WeChatOCR.exe', 'WeChatPlayer.exe', 'WeChatUtility.exe', 'WidgetService.exe', 'Widgets.exe', 'WmiPrvSE.exe', 'Xmp.exe','QQScreenshot.exe', 'RadeonSoftware.exe', 'SakuraFrpService.exe', 'SakuraLauncher.exe', 'SearchHost.exe', 'SecurityHealthSystray.exe', 'ShellExperienceHost.exe', 'StartMenuExperienceHost.exe', 'SystemSettings.exe', 'SystemSettingsBroker.exe', 'TextInputHost.exe', 'TrafficMonitor.exe', 'UserOOBEBroker.exe','WeChatAppEx.exe','360zipUpdate.exe', 'AMDRSServ.exe', 'AMDRSSrcExt.exe', 'APlayer.exe', 'ApplicationFrameHost.exe', 'CPUMetricsServer.exe', 'ChsIME.exe', 'DownloadSDKServer.exe','QMWeiyun.exe']
                        if exe_name in pass_exe:
                            print(f"当前窗口 {exe_name} 在冻结列表中，跳过冻结")
                            return True
                        # 仅当目标进程未挂起时才执行挂起
                        is_stopped = False
                        for proc in psutil.process_iter(['name', 'status']):
                            try:
                                if proc.info['name'] and proc.info['name'].lower() == exe_name.lower():
                                    if proc.status() == psutil.STATUS_STOPPED:
                                        is_stopped = True
                                        break
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                continue
                        # 判断exe_path是否在valid_apps的path中
                        found_in_valid_apps = False
                        for app in valid_apps:
                            if exe_path and exe_path.lower() == app["path"].lower():
                                found_in_valid_apps = True
                                break
                        if not found_in_valid_apps:
                            is_stopped = True

                        if not is_stopped:
                            subprocess.Popen(
                                ['./_internal/pssuspend64.exe', exe_name],
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                    else:
                        QMessageBox.warning(self, "提示", "未找到冻结工具，请检查路径")
                return True
            else:
                print(f"当前窗口非全屏 {exe_name} 窗口大小：{window_width} x {window_height} 屏幕分辨率：{screen_width} x {screen_height}")
                return False
        except Exception as e:
            # 捕获异常，返回假
            print(f"错误: {e}")
            return False
    def handle_gamepad_input(self, action):
        """处理手柄输入"""
        global STARTUP  # 声明 STARTUP 为全局变量
        if action:
            # 处理方向键FIRST事件
            if action.startswith('FIRST-'):
                firstinput = True
                action = action.split('-', 1)[1]  # 提取方向值
            else:
                firstinput = False
        # 标记是否为方向输入（允许绕过全局防抖/屏蔽）
        is_direction = action in ('UP', 'DOWN', 'LEFT', 'RIGHT') if action else False
        # 跟踪焦点状态
        current_time = pygame.time.get_ticks()
        # 如果在屏蔽输入的时间段内，则不处理（方向键除外）
        if current_time < self.ignore_input_until and not is_direction:
            return

        # 如果按键间隔太短，则不处理（方向键除外）
        if current_time - self.last_input_time < self.input_delay and not is_direction:
            return
        if self.is_mouse_simulation_running == True:
            return # 防止鼠标模拟运行时处理手柄输入
        # 检查 LS 和 RS 键是否同时按下
        if action in ('LS', 'RS'):
            # 获取当前手柄对象和映射
            for controller_data in self.controller_thread.controllers.values():
                controller = controller_data['controller']
                mapping = controller_data['mapping']
                ls_pressed = controller.get_button(mapping.left_stick_in)
                rs_pressed = controller.get_button(mapping.right_stick_in)
                if ls_pressed and rs_pressed:
                    self.ignore_input_until = pygame.time.get_ticks() + 3000 
                    print("LS和RS同时按下！正在截图...")
                    screenshot = pyautogui.screenshot()
                
                    # 智能识别当前游戏名称
                    def get_current_game_name():
                        try:
                            hwnd = win32gui.GetForegroundWindow()
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            exe_path = psutil.Process(pid).exe()
                            exe_path = exe_path.lower()
                            # 在 valid_apps 里查找匹配的游戏名
                            for app in valid_apps:
                                if app["path"].lower() == exe_path:
                                    return app["name"]
                        except Exception as e:
                            print(f"识别游戏名失败: {e}")
                        return "other"
                
                    game_name = get_current_game_name()
                    # 生成保存路径
                    now_str = time.strftime("%Y%m%d_%H%M%S")
                    screenshot_dir = os.path.join(program_directory, "screenshot", game_name)
                    os.makedirs(screenshot_dir, exist_ok=True)
                    screenshot_path = os.path.join(screenshot_dir, f"{now_str}.png")
                    screenshot.save(screenshot_path)
                    print(f"截图已保存到 {screenshot_path}")
                
                    # 新增：截图悬浮窗
                    class ScreenshotDialog(QDialog):
                        def __init__(self, image_path, parent=None):
                            super().__init__(parent)
                            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
                            self.setAttribute(Qt.WA_TranslucentBackground)
                            self.setModal(False)
                            self.setFixedSize(480, 160)
                    
                            # 用QWidget做内容容器，设置背景和圆角
                            content_widget = QWidget(self)
                            content_widget.setObjectName("content_widget")
                            content_widget.setGeometry(0, 0, 480, 160)
                            content_widget.setStyleSheet("""
                                QWidget#content_widget {
                                    background-color: rgba(30, 30, 30, 230);
                                    border-radius: 12px;
                                }
                            """)
                    
                            main_layout = QHBoxLayout(content_widget)
                            main_layout.setContentsMargins(16, 16, 16, 16)  # 适当内边距
                    
                            # 左侧图片
                            pixmap = QPixmap(image_path).scaled(180, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            img_label = QLabel()
                            img_label.setPixmap(pixmap)
                            img_label.setFixedSize(180, 120)
                            img_label.setStyleSheet("background: transparent; margin: 0px; padding: 0px;")
                            main_layout.addWidget(img_label)
                    
                            # 右侧文字
                            text_layout = QVBoxLayout()
                            text_layout.setContentsMargins(0, 0, 0, 0)
                            tip_label = QLabel(f"  截图已保存\n  {game_name}\n  {now_str}.png")
                            tip_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent; margin: 0px; padding: 0px;")
                            tip_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                            text_layout.addWidget(tip_label)
                            main_layout.addLayout(text_layout)
                    
                            self.move(20, 20)
                            self.show()
                    
                            QTimer.singleShot(2000, self.close)
                
                    ScreenshotDialog(screenshot_path, self)
        # 检查 Back 和 Start 键是否同时按下
        if action in ('BACK', 'START'):
            # 获取当前手柄对象和映射
            for controller_data in self.controller_thread.controllers.values():
                controller = controller_data['controller']
                mapping = controller_data['mapping']
                back_pressed = controller.get_button(mapping.back)
                start_pressed = controller.get_button(mapping.start)
                if back_pressed and start_pressed:
                    print("Back和Start同时按下！")
                    # 弹出进度条悬浮窗
                    class ProgressDialog(QDialog):
                        def __init__(self, parent=None):
                            super().__init__(parent)
                            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
                            self.setAttribute(Qt.WA_TranslucentBackground)
                            self.setWindowOpacity(0.85)
                            self.setModal(True)
                    
                            # 内容容器，设置背景和圆角
                            content_widget = QWidget(self)
                            content_widget.setObjectName("content_widget")
                            content_widget.setGeometry(0, 0, 420, 120)
                            content_widget.setStyleSheet("""
                                QWidget#content_widget {
                                    background-color: rgba(30, 30, 30, 230);
                                    border-radius: 10px;
                                }
                            """)
                    
                            # 主布局放在内容容器上
                            main_layout = QVBoxLayout(content_widget)
                            main_layout.setContentsMargins(10, 10, 10, 10)
                    
                            # 创建提示标签
                            self.prompt_label = QLabel("持续按住触发鼠标模拟...")
                            self.prompt_label.setStyleSheet("color: white; font-size: 14px; background: transparent;")
                            self.prompt_label.setAlignment(Qt.AlignCenter)
                            main_layout.addWidget(self.prompt_label)
                    
                            # 创建进度条容器
                            progress_container = QFrame()
                            progress_container.setStyleSheet("""
                                QFrame {
                                    background-color: rgba(0, 0, 0, 125);
                                    border: 1px solid black;
                                    border-radius: 5px;
                                }
                            """)
                            progress_layout = QVBoxLayout(progress_container)
                            progress_layout.setContentsMargins(10, 5, 10, 5)
                    
                            # 创建进度条标签
                            self.label = QLabel("0%")
                            self.label.setStyleSheet("""
                                QLabel {
                                    background-color: green;
                                    color: white;
                                    font-size: 16px;
                                    border-radius: 3px;
                                }
                            """)
                            self.label.setAlignment(Qt.AlignCenter)
                            self.label.setFixedHeight(30)
                            progress_layout.addWidget(self.label)
                    
                            main_layout.addWidget(progress_container)
                    
                            # 设置窗口大小
                            self.setFixedSize(440, 120)
                    
                            # 居中显示窗口
                            screen = QApplication.primaryScreen().geometry()
                            x = (screen.width() - self.width()) // 2
                            y = (screen.height() - self.height()) // 2
                            self.move(x, y)
                    
                            self.show()
                            
                        def update_progress(self, percent):
                            # 更新进度条宽度
                            width = int(400 * percent / 100)
                            self.label.setFixedWidth(width)
                            self.label.setText(f"{percent}%")
                            QApplication.processEvents()
                            
                    # 只弹出一次
                    if not hasattr(self, '_back_start_progress') or self._back_start_progress is None:
                        self._back_start_progress = ProgressDialog(self)
                        QApplication.processEvents()
                        pressed = True
                        for i in range(0, 101, 3):
                            # 实时检测按键是否松开
                            back_pressed = controller.get_button(mapping.back)
                            start_pressed = controller.get_button(mapping.start)
                            if not (back_pressed and start_pressed):
                                pressed = False
                                break
                            self._back_start_progress.update_progress(i)
                            time.sleep(0.01)
                        self._back_start_progress.close()
                        self._back_start_progress = None
                        if pressed:
                            print("Back和Start已持续按下2秒！")
                            # 执行鼠标模拟
                            self.mouse_simulation()
                        else:
                            # 按键提前松开，执行后续代码
                            self.back_start_pressed_time = None
                            break
                    break
                else:
                    self.back_start_pressed_time = None
                    break
        print(f"处理手柄输入: {action}")
        if hasattr(self, 'confirm_dialog') and self.confirm_dialog and self.confirm_dialog.isVisible():  # 如果确认弹窗显示中
            print("确认弹窗显示中")
            self.ignore_input_until = current_time + 500
            self.confirm_dialog.handle_gamepad_input(action)
            return
        # 优先检查所有可能的 confirm_dialog，无论窗口是否可见
        # 检查 screenshot_window 的 confirm_dialog
        if hasattr(self, 'screenshot_window') and hasattr(self.screenshot_window, 'confirm_dialog') and self.screenshot_window.confirm_dialog and self.screenshot_window.confirm_dialog.isVisible():
            self.screenshot_window.handle_gamepad_input(action)
            self.ignore_input_until = pygame.time.get_ticks() + 300 
            return
        # 检查 floating_window 的 confirm_dialog
        if getattr(self, 'floating_window', None) and hasattr(self.floating_window, 'confirm_dialog') and self.floating_window.confirm_dialog and self.floating_window.confirm_dialog.isVisible():
            self.floating_window.handle_gamepad_input(action)
            self.ignore_input_until = pygame.time.get_ticks() + 300 
            return
        
        if not self.gsfocus():  # 检测当前窗口是否为游戏选择界面
            if action == 'GUIDE':
                try:
                    # 将所有界面标记归零（没必要似乎
                    #self.current_index = 0
                    #self.current_section = 0
                    #self.more_section = 0
                    #if current_time < ((self.ignore_input_until)+2000):
                    #    return
                    #self.ignore_input_until = pygame.time.get_ticks() + 500 
                    #if STARTUP:subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])#STARTUP = False
                    if self.killexplorer == True:
                        self.wintaskbarshow()
                    #if STARTUP:
                    #    self.exitdef(False)
                    #    # 无参数重启
                    #    subprocess.Popen([sys.executable])
                    #self.showFullScreen()
                    ## 记录当前窗口的 Z 顺序
                    #z_order = []
                    #def enum_windows_callback(hwnd, lParam):
                    #    z_order.append(hwnd)
                    #    return True
                    #win32gui.EnumWindows(enum_windows_callback, None)
                    self.is_current_window_fullscreen()
                    hwnd = int(self.winId())
                    ctypes.windll.user32.ShowWindow(hwnd, 9) # 9=SW_RESTORE            
                    result = ctypes.windll.user32.SetForegroundWindow(hwnd)
                    screen_width, screen_height = pyautogui.size()
                    # 设置右下角坐标
                    right_bottom_x = screen_width - 1  # 最右边
                    right_bottom_y = screen_height - 1  # 最底部
                    pyautogui.moveTo(right_bottom_x, right_bottom_y)
                    if result:
                        print("窗口已成功带到前台")
                    else:
                        print("未能将窗口带到前台，正在尝试设置为最上层")
                        SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                        if self.killexplorer == False:
                            hide_taskbar()
                        time.sleep(0.2)
                    # 移动鼠标到屏幕右下角并进行右键点击
                        pyautogui.rightClick(right_bottom_x, right_bottom_y)
                        if self.killexplorer == False:
                            show_taskbar()
                        # 恢复原来的 Z 顺序
                        #for hwnd in reversed(z_order):
                        SetWindowPos(hwnd, -2, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                except Exception as e:
                    print(f"Error: {e}")
            self.ignore_input_until = current_time + 500
            return
        
            # 若启动悬浮窗存在，关闭启动悬浮窗
        if hasattr(self, 'launch_overlay'):
            if self.launch_overlay and self.launch_overlay.isVisible():
                self.launch_overlay.hide()
                self.launch_overlay._stop_launch_animations()
        # 正常窗口处理逻辑
        if hasattr(self, 'screenshot_window') and self.screenshot_window.isVisible():
            print("截图悬浮窗显示中")
            self.ignore_input_until = current_time + 200
            self.screenshot_window.handle_gamepad_input(action)
            return
        
        if getattr(self, 'floating_window', None) and self.floating_window.isVisible():
            # 添加防抖检查（方向键可绕过浮窗防抖以获得更灵敏的导航）
            if not is_direction and not self.floating_window.can_process_input():
                return
            
            if action == 'UP':
                self.floating_window.current_index = max(0, self.floating_window.current_index - 1)
                self.floating_window.update_highlight()
            elif action == 'DOWN':
                self.floating_window.current_index = min(
                    len(self.floating_window.buttons) - 1,
                    self.floating_window.current_index + 1
                )
                self.floating_window.update_highlight()
            elif action == 'A':
                self.execute_more_item()
            elif action in ('B', 'X'):  # B键或X键都可以关闭悬浮窗
                self.floating_window.hide()
            elif action == 'Y':
                self.floating_window.toggle_favorite()
            self.last_input_time = current_time
            return

        # 新增焦点切换逻辑
        if action == 'DOWN' and self.current_section == 0 and self.more_section == 0:
            self.current_section = 1  # 切换到控制按钮区域
            #if self.current_index < 3:
            #    self.current_index = int(self.current_index * 2)
            #else:
            #    self.current_index = 6
            self.current_index = 3
            self.update_highlight()
            print("当前区域：控制按钮区域")
        elif action == 'UP' and self.current_section == 1 and self.more_section == 0:
            self.current_section = 0  # 返回游戏选择区域
            self.current_index = int(self.current_index/2)
            self.update_highlight()
            print("当前区域：游戏选择区域")
        elif action == 'B' and self.more_section == 1:
            self.switch_to_main_interface()
        else:
            if self.current_section == 1:  # 控制按钮区域
                if action.lower() == "right":
                    self.current_index = min(self.current_index + 1, len(self.control_buttons)-1)
                elif action.lower() == "left":
                    self.current_index = max(self.current_index - 1, 0)
                #elif action.lower() == "down":
                #    self.current_section = 0  # 返回游戏选择区域
                elif action == 'A':
                    self.control_buttons[self.current_index].click()
                elif action == 'X':  # X键开悬浮窗
                    self.show_more_window()  # 打开悬浮窗
                elif action == 'B':
                    #self.exitdef()  # 退出程序
                    self.hide_window()
                elif action == 'GUIDE':  # 回桌面
                    if current_time < ((self.ignore_input_until)+500):
                        return
                    self.ignore_input_until = pygame.time.get_ticks() + 500 
                    #self.exitdef()  # 退出程序
                    self.hide_window()
                    pyautogui.hotkey('win', 'd')
                        
                self.update_highlight()
            else:
                if action == 'UP' and self.more_section == 1:
                    self.move_selection(-self.row_count)  # 向上移动
                elif action == 'DOWN' and self.more_section == 1:
                    self.move_selection(self.row_count)  # 向下移动
                elif action == 'LEFT':
                    if self.current_index == 0:  # 如果当前是第一项
                        if firstinput:
                            self.move_selection(-1)  # 向左移动
                        return
                    self.move_selection(-1)  # 向左移动
                elif action == 'RIGHT':
                    if self.current_index < len(self.buttons) - 1:  # 检查是否已经是最后一个按钮
                        self.move_selection(1)  # 向右移动
                    else:
                        if firstinput:
                            self.move_selection(1)  # 向右移动
                elif action == 'A':
                    self.launch_game(self.current_index)  # 启动游戏
                elif action == 'B':
                    #self.exitdef()  # 退出程序
                    self.hide_window()
                elif action == 'Y':
                    self.toggle_favorite()  # 收藏/取消收藏游戏
                    self.ignore_input_until = pygame.time.get_ticks() + 300 
                elif action == 'X':  # X键开悬浮窗
                    self.show_more_window()  # 打开悬浮窗
                elif action == 'START':  # START键打开游戏详情
                    self.open_selected_game_screenshot()
                elif action == 'BACK':  # SELECT键打开设置
                    if current_time < ((self.ignore_input_until)+500):
                        return
                    self.ignore_input_until = pygame.time.get_ticks() + 500 
                    self.show_settings_window()
                    self.mouse_simulation()
                    QTimer.singleShot(10, lambda: pyautogui.moveTo(int(self.settings_button.mapToGlobal(self.settings_button.rect().center()).x()+100), int(self.settings_button.mapToGlobal(self.settings_button.rect().center()).y())+270))
                elif action == 'GUIDE':  # 回桌面
                    if current_time < ((self.ignore_input_until)+500):
                        return
                    self.ignore_input_until = pygame.time.get_ticks() + 500 
                    #self.exitdef()  # 退出程序
                    self.hide_window()
                    pyautogui.hotkey('win', 'd')

        # 更新最后一次按键时间
        self.last_input_time = current_time
    def sort_games(self):
        """根据收藏和最近游玩对游戏进行排序"""
        sorted_games = []

        # 如果有正在运行的应用，优先加入
        for game_name in self.player:
            for game in games:
                if game["name"] == game_name:
                    sorted_games.append(game)
                    break
        
        # 首先添加收藏的游戏
        for game_name in settings["favorites"]:
            for game in games:
                if game["name"] == game_name and game["name"] not in self.player:
                    sorted_games.append(game)
                    break
        
        # 然后添加最近游玩的游戏
        for game_name in settings["last_played"]:
            for game in games:
                if game["name"] == game_name and game["name"] not in settings["favorites"] and game["name"] not in self.player:
                    sorted_games.append(game)
                    break
        
        # 最后添加其他游戏
        for game in games:
            if game["name"] not in settings["favorites"] and game["name"] not in settings["last_played"] and game["name"] not in self.player:
                sorted_games.append(game)
        
        return sorted_games
    def exitdef(self):
        """退出程序"""
        # 停止所有线程
        if self.killexplorer == True and hasattr(self, 'winTaskbar'):
            self.winTaskbar.on_back_to_desktop()
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        if hasattr(self, 'controller_thread'):
            self.controller_thread.stop()
            self.controller_thread.wait()
        
            
        #self.close()
        QApplication.quit()
        #def exitdef(self,rerun=True):
        #if rerun:
        #    subprocess.Popen([sys.executable, "startup"])

    def toggle_favorite(self):
        """切换当前游戏的收藏状态"""
        current_game = self.sort_games()[self.current_index]
        game_name = current_game["name"]
        print(game_name)
        #删除逻辑
        if game_name in self.player:
            # 创建确认弹窗
            self.confirm_dialog = ConfirmDialog(f"是否关闭下列程序？\n{game_name}", scale_factor=self.scale_factor)
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks()
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            for app in valid_apps:
                if app["name"] == game_name:
                    game_path = app["path"]
                    break
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    # 检查进程的执行文件路径是否与指定路径匹配
                    if proc.info['exe'] and os.path.abspath(proc.info['exe']) == os.path.abspath(game_path):
                        print(f"找到进程: {proc.info['name']} (PID: {proc.info['pid']})")
                        # 显示加载窗口
                        loading = LoadingDialog("正在关闭程序......", scale_factor=self.scale_factor, parent=self)
                        loading.show()
                        QApplication.processEvents()
                        try:
                            proc.terminate()  # 请求结束进程
                        except Exception:
                            pass
                        # 等待进程退出，同时让 UI 响应
                        start_time = time.time()
                        try:
                            while proc.is_running():
                                QApplication.processEvents()
                                time.sleep(0.05)
                                if time.time() - start_time > 5:
                                    try:
                                        proc.kill()
                                    except Exception:
                                        pass
                                    break
                        except Exception:
                            pass
                        loading.close()
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # 处理权限问题和进程已消失的异常
                    continue
            return

        if game_name in settings["favorites"]:
            settings["favorites"].remove(game_name)
        else:
            settings["favorites"].append(game_name)
        
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        
        # 重新加载界面
        self.reload_interface()
    
    def on_scale_factor_updated(self, new_scale_factor):
        """缩放因子更新时调用，更新界面控件尺寸与布局"""
        # 更新缩放因子
        self.scale_factor = new_scale_factor
        self.scale_factor2 = self.scale_factor * 2
        
        # 更新顶部按钮
        if hasattr(self, 'more_button'):
            self.more_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
            self.more_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    border-radius: {int(20 * self.scale_factor)}px; 
                    border: {int(2 * self.scale_factor)}px solid #888888;
                    color: white;
                    font-size: {int(16 * self.scale_factor)}px;
                }}
                QPushButton:hover {{
                    border: {int(2 * self.scale_factor)}px solid #555555;
                }}
            """)
        
        if hasattr(self, 'favorite_button'):
            self.favorite_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
            self.favorite_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    border-radius: {int(20 * self.scale_factor)}px; 
                    border: {int(2 * self.scale_factor)}px solid #888888;
                    color: white;
                    font-size: {int(16 * self.scale_factor)}px;
                }}
                QPushButton:hover {{
                    border: {int(2 * self.scale_factor)}px solid #555555;
                }}
            """)
        
        if hasattr(self, 'quit_button'):
            self.quit_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
            self.quit_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    border-radius: {int(20 * self.scale_factor)}px; 
                    border: {int(2 * self.scale_factor)}px solid #888888;
                    color: white;
                    font-size: {int(16 * self.scale_factor)}px;
                }}
                QPushButton:hover {{
                    border: {int(2 * self.scale_factor)}px solid #555555;
                }}
            """)
        
        if hasattr(self, 'settings_button'):
            self.settings_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
            self.settings_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    border-radius: {int(20 * self.scale_factor)}px; 
                    border: {int(2 * self.scale_factor)}px solid #888888;
                    color: white;
                    font-size: {int(16 * self.scale_factor)}px;
                }}
                QPushButton:hover {{
                    border: {int(2 * self.scale_factor)}px solid #555555;
                }}
            """)
        
        if hasattr(self, 'screenshot_button'):
            self.screenshot_button.setFixedSize(int(120 * self.scale_factor), int(40 * self.scale_factor))
            self.screenshot_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; 
                    border-radius: {int(20 * self.scale_factor)}px; 
                    border: {int(2 * self.scale_factor)}px solid #888888;
                    color: white;
                    font-size: {int(16 * self.scale_factor)}px;
                }}
                QPushButton:hover {{
                    border: {int(2 * self.scale_factor)}px solid #555555;
                }}
            """)
        
        # 更新游戏名标签和时间标签
        if hasattr(self, 'game_name_label'):
            self.game_name_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(20 * self.scale_factor)}px;
                    font-weight: bold;
                    padding: 0 {int(20 * self.scale_factor)}px;
                }}
            """)
        
        if hasattr(self, 'time_label'):
            self.time_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(25 * self.scale_factor)}px;
                    padding-top: {int(10 * self.scale_factor)}px;
                    padding-bottom: {int(10 * self.scale_factor)}px;
                    padding-right: {int(20 * self.scale_factor)}px;
                }}
            """)

        # 更新底部右侧文字（帮助/提示）
        if hasattr(self, 'right_label'):
            try:
                self.right_label.setStyleSheet(f"""
                    QLabel {{
                        font-family: "Microsoft YaHei"; 
                        color: white;
                        font-size: {int(25 * self.scale_factor)}px;
                        padding-bottom: {int(10 * self.scale_factor)}px;
                        padding-right: {int(50 * self.scale_factor)}px;
                    }}
                """)
            except Exception:
                pass
        
        # 更新网格布局间距
        if hasattr(self, 'grid_layout'):
            self.grid_layout.setSpacing(int(20 * self.scale_factor))
        
        # 更新顶部布局边距
        if hasattr(self, 'top_layout'):
            self.top_layout.setContentsMargins(int(20 * self.scale_factor), 0, int(20 * self.scale_factor), 0)

        # 更新控制按钮区域（圆形按钮）
        if hasattr(self, 'control_layout'):
            try:
                self.control_layout.setSpacing(int(50 * self.scale_factor))
            except Exception:
                pass
        if hasattr(self, 'control_buttons'):
            for btn in self.control_buttons:
                try:
                    size = int(125 * self.scale_factor)
                    border_px = max(1, int(5 * self.scale_factor))
                    font_px = max(8, int(40 * self.scale_factor))
                    btn.setFixedSize(size, size)
                    # 圆形半径为宽度的一半，使用像素值避免百分比差异
                    radius_px = int(size / 2)
                    checked_border = max(1, int(6 * self.scale_factor))
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #575757;
                            border-radius: {radius_px}px;
                            font-size: {font_px}px; 
                            border: {border_px}px solid #282828;
                        }}
                        QPushButton:checked {{
                            background-color: #45a049;
                            border: {checked_border}px solid #ffff00;
                        }}
                    """)
                except Exception:
                    pass
        
        # 更新游戏按钮
        if hasattr(self, 'buttons'):
            for button in self.buttons:
                # 跳过"更多"按钮
                if button.text() == "🟦🟦\n🟦🟦":
                    button.setFixedSize(int(140 * self.scale_factor2), int(140 * self.scale_factor2))
                elif button.text() in ["返回", "返回主页面"]:
                    # 处理返回按钮
                    button.setFixedSize(int(140 * self.scale_factor2), int(140 * self.scale_factor2))
                else:
                    # 更新游戏按钮
                    button.setFixedSize(int(220 * self.scale_factor2), int(300 * self.scale_factor2))
                    # 更新按钮样式
                    button.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            border-radius: {int(10 * self.scale_factor2)}px;
                            border: {int(2 * self.scale_factor2)}px solid #444444;
                            color: white;
                            text-align: center;
                            padding: 0;
                        }}
                        QPushButton:hover {{
                            border: {int(2 * self.scale_factor2)}px solid #888888;
                        }}
                    """)
                    
                    # 更新按钮内的标签
                    for child in button.findChildren(QLabel):
                        if child.objectName() == "star_label":
                            # 更新收藏标签
                            child.setStyleSheet(f"""
                                QLabel {{
                                    background-color: rgba(0, 0, 0, 0.7);
                                    color: gold;
                                    font-size: {int(10 * self.scale_factor2)}px;
                                    padding: {int(5 * self.scale_factor2)}px;
                                    border-radius: {int(10 * self.scale_factor2)}px;
                                }}
                            """)
                            child.move(int(5 * self.scale_factor2), int(5 * self.scale_factor2))
        
        # 更新滚动区域高度和宽度
        if hasattr(self, 'scroll_area'):
            self.scroll_area.setFixedHeight(int(320 * self.scale_factor * 2.4))
            self.scroll_area.setFixedWidth(int(self.width()))
        
        # 更新滚动区域中的图像
        if hasattr(self, 'buttons') and hasattr(self, 'sort_games'):
            sorted_games = self.sort_games()
            for idx, button in enumerate(self.buttons):
                # 跳过"更多"按钮和"返回"按钮
                if button.text() == "🟦🟦\n🟦🟦" or button.text() in ["返回", "返回主页面"]:
                    continue
                
                # 确保索引有效
                if idx < len(sorted_games):
                    game = sorted_games[idx]
                    image_path = game["image-path"]
                    # 自动判断图片路径是相对还是绝对
                    if not os.path.isabs(image_path):
                        image_path = f"{APP_INSTALL_PATH}\\config\\covers\\{image_path}"
                    
                    # 重新加载并缩放图像
                    pixmap = QPixmap(image_path).scaled(int(200 * self.scale_factor2), int(267 * self.scale_factor2), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    icon = QIcon(pixmap)
                    button.setIcon(icon)
                    button.setIconSize(pixmap.size())
        
        # 更新加载提示标签
        if hasattr(self, 'loading_label'):
            self.loading_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(30 * self.scale_factor)}px;
                }}
            """)
        
        # 更新没有游戏时的提示按钮
        if hasattr(self, 'no_games_button'):
            self.no_games_button.setFixedSize(int(700 * self.scale_factor), int(200 * self.scale_factor))
            self.no_games_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border-radius: {int(10 * self.scale_factor)}px;
                    border: {int(2 * self.scale_factor)}px solid #444444;
                    color: white;
                    font-size: {int(30 * self.scale_factor)}px;
                }}
                QPushButton:hover {{
                    border: {int(2 * self.scale_factor)}px solid #888888;
                }}
            """)
        
        # 更新分隔线
        if hasattr(self, 'divider'):
            self.divider.setFixedHeight(int(4 * self.scale_factor))
        
        # 更新左右标签
        if hasattr(self, 'left_label'):
            self.left_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(25 * self.scale_factor)}px;
                    padding-bottom: {int(10 * self.scale_factor)}px;
                    padding-left: {int(50 * self.scale_factor)}px;
                }}
            """)
        
        if hasattr(self, 'right_label'):
            self.right_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {int(25 * self.scale_factor)}px;
                    padding-bottom: {int(10 * self.scale_factor)}px;
                    padding-right: {int(50 * self.scale_factor)}px;
                }}
            """)

    def reload_interface(self):
        """重新加载界面"""
        # 优化：清除现有按钮的方式，使用更高效的布局处理
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        self.buttons.clear()
        if self.more_section == 1:
            #修改按钮文字为"返回"
            self.quit_button.setText("返回主页面")
        else:
            self.quit_button.setText("最小化")
        # 重新添加按钮
        sorted_games = self.sort_games()
        if sorted_games:  # 只在有游戏时添加按钮
            if self.more_section == 0:
                for index, game in enumerate(sorted_games[:self.buttonsindexset]):
                    button = self.create_game_button(game, index)
                    #self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)
                    self.grid_layout.addWidget(button, 0, index)
                    self.buttons.append(button)

                # 添加"更多"按钮
                more_button = QPushButton("🟦🟦\n🟦🟦")
                more_button.setFont(QFont("Microsoft YaHei", 40))
                more_button.setFixedSize(int(140 * self.scale_factor2), int(140 * self.scale_factor2))
                more_button.clicked.connect(self.switch_to_all_software)  # 绑定"更多"按钮的功能
                self.grid_layout.addWidget(more_button, 0, len(sorted_games[:self.buttonsindexset]))  # 添加到最后一列
                self.buttons.append(more_button)
            else:
                # 优化：使用批量加载方式
                self.load_all_games_optimized(sorted_games)

        # 使用 QTimer 延迟执行高亮更新
        QTimer.singleShot(25, self.update_highlight)
        #self.butto=False
    
    def load_all_games_optimized(self, sorted_games):
        """优化加载所有游戏的方法"""
        for index, game in enumerate(sorted_games):
            button = self.create_game_button(game, index)
            self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)
            self.buttons.append(button)
            
            # 每创建10个按钮，让UI线程有机会处理其他事件
            if (index + 1) % 10 == 0:
                QApplication.processEvents()  # 处理待处理的事件，优化 `c:\Users\86150\Desktop\dist2\DesktopGame.py`

    def show_more_window(self):
        """显示更多选项窗口"""
        if not self.floating_window:
            self.floating_window = FloatingWindow(self)
            
        # 计算悬浮窗位置
        button_pos = self.more_button.mapToGlobal(self.more_button.rect().bottomLeft())
        self.floating_window.move(button_pos.x(), button_pos.y() + 10)
        
        self.floating_window.show()
        # 重新加载按钮
        for button in self.floating_window.buttons:
            button.setParent(None)
        self.floating_window.buttons.clear()
        self.floating_window.create_buttons()
        self.floating_window.update_highlight()

    def execute_more_item(self, file=None, enable_mouse_sim=True):
        """执行更多选项中的项目"""
        if not self.floating_window:
            return
    
        sorted_files = self.floating_window.sort_files()
        if file:
            current_file = file
        else:
            current_file = sorted_files[self.floating_window.current_index]
    
        current_file["path"] = os.path.abspath(os.path.join("./morefloder/", current_file["path"]))
        if current_file["name"] in self.floating_window.current_running_apps:
            self.restore_window(get_target_path(current_file["path"]))
        else:
            # 更新最近使用列表
            if "more_last_used" not in settings:
                settings["more_last_used"] = []
    
            if current_file["name"] in settings["more_last_used"]:
                settings["more_last_used"].remove(current_file["name"])
            settings["more_last_used"].insert(0, current_file["name"])
    
            # 保存设置
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
    
            # 执行文件
            print(f"执行文件: {current_file['path']}")
            self.hide_window()
            subprocess.Popen(current_file["path"], shell=True)
        self.floating_window.current_index = 0
        self.floating_window.update_highlight()
        self.floating_window.hide()
        if enable_mouse_sim:
            self.mouse_simulation()

    def show_settings_window(self):
        """显示设置窗口"""
        if not hasattr(self, 'settings_window') or self.settings_window is None:
            self.settings_window = SettingsWindow(self)
        
        # 计算悬浮窗位置
        button_pos = self.settings_button.mapToGlobal(self.settings_button.rect().bottomLeft())
        self.settings_window.move(button_pos.x(), button_pos.y() + 10)
        
        self.settings_window.show()

    def is_admin(self):
        """检查当前进程是否具有管理员权限"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def run_as_admin(self):
        """以管理员权限重新运行程序"""
        try:
            # 传递启动参数 'refresh'，以便在新程序中执行刷新逻辑
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv) + " refresh", None, 1
            )
            sys.exit()  # 关闭原程序
        except Exception as e:
            print(f"无法以管理员权限重新运行程序: {e}")

    def restart_program(self):
        """重启程序"""
        QApplication.quit()
        # 只传递可执行文件的路径，不传递其他参数
        subprocess.Popen([sys.executable])

    def refresh_games(self, args=None):
        """刷新游戏列表，处理 extra_paths 中的快捷方式（线程安全）"""
        self.qsaa_thread = QuickStreamAppAddThread(args=args)
        self.qsaa_thread.finished_signal.connect(self.deep_reload_games)
        self.qsaa_thread.start()
        return

    def update_controller_status(self, controller_name):
        """更新左侧标签显示的手柄名称"""
        if hasattr(self, 'left_label') and isinstance(self.left_label, QLabel):
            self.left_label.setText(f"🎮️ {controller_name}")
        else:
            print("left_label 未正确初始化")
    class KeyboardWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.setFixedSize(700, 320)
            self.setStyleSheet("background-color: lightgray;")
            self.keys = {"Esc": [66,36,104,40,"green"],"Win": [172,36,104,40,"green"],"Del": [378,268,104,40,"green"],"Enter": [484,268,104,40,"green"],"1!": [68,80,50,40,"yellow"],"2@": [120,80,50,40,"yellow"],"3#": [172,80,50,40,"yellow"],"4$": [224,80,50,40,"yellow"],"5%": [276,80,50,40,"green"],"6^": [328,80,50,40,"green"],"7&": [380,80,50,40,"yellow"],"8*": [432,80,50,40,"yellow"],"9(": [484,80,50,40,"yellow"],"0)": [536,80,50,40,"yellow"],"`~": [16,80,50,40,"green"],"Q": [68,128,50,40,"yellow"],"W": [120,128,50,40,"white"],"E": [172,128,50,40,"white"],"R": [224,128,50,40,"yellow"],"T": [276,128,50,40,"green"],"Y": [328,128,50,40,"green"],"U": [380,128,50,40,"yellow"],"I": [432,128,50,40,"white"],"O": [484,128,50,40,"white"],"P": [536,128,50,40,"yellow"],"-_": [378,36,104,40,"green"],"tab": [16,128,50,40,"green"],"A": [68,176,50,40,"yellow"],"S": [120,176,50,40,"white"],"D": [172,176,50,40,"white"],"F": [224,176,50,40,"yellow"],"G": [276,176,50,40,"green"],"H": [328,176,50,40,"green"],"J": [380,176,50,40,"yellow"],"K": [432,176,50,40,"white"],"L": [484,176,50,40,"white"],";:": [536,176,50,40,"yellow"],"\\|": [588,224,50,40,"green"],"Capslock": [16,176,50,40,"green"],"Z": [68,224,50,40,"yellow"],"X": [120,224,50,40,"yellow"],"C": [172,224,50,40,"yellow"],"V": [224,224,50,40,"yellow"],"B": [276,224,50,40,"green"],"N": [328,224,50,40,"green"],"M": [380,224,50,40,"yellow"],",<": [432,224,50,40,"yellow"],".>": [484,224,50,40,"yellow"],"/?": [536,224,50,40,"yellow"],"shift": [16,224,50,40,"green"],"ctrl": [66,268,104,40,"green"],"alt": [172,268,104,40,"green"],"=+": [484,36,104,40,"green"],"[{": [588,80,50,40,"green"],"]}": [588,128,50,40,"green"],"'\"": [588,176,50,40,"green"]}
            self.active_key = None
            self.key_selected_callback = None
            self.sticky_enabled = False
            self.sticky_keys = set()
            self.sticky_key_names = {'shift', 'ctrl', 'alt', 'Win'}
            self.f_keys_enabled = False
            self.f_keys_active = 0
            self.f_keys = {}
            self.setup_f_keys()
            self.left_joystick_state = {'x': 0.0, 'y': 0.0}
            self.right_joystick_state = {'x': 0.0, 'y': 0.0}
        def set_joystick_state(self, left_state, right_state):
            self.left_joystick_state = left_state
            self.right_joystick_state = right_state
            self.update()
        def setup_f_keys(self):
            for i in range(12):
                x = (i * 52) + 16
                self.f_keys[f'F{i+1}'] = [x, 0, 50, 32, "blue"]
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            # -- 底层添加带圆角的灰色遮罩 --
            rounded_rect = self.rect().adjusted(10, 30, -55, -5)  # 留出些内边距
            radius = 60
            mask_color = QColor(120, 120, 120, 90)  # 灰色且半透明
            painter.setBrush(QBrush(mask_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rounded_rect, radius, radius)

            if self.f_keys_enabled:
                painter.setBrush(QBrush(QColor(100, 150, 255, 180)))
                painter.setPen(QPen(Qt.black, 1))
                painter.drawRect(16, 0, 620, 32)
                for i, (key_name, (x, y, w, h, color)) in enumerate(self.f_keys.items()):
                    brush_color = QColor(255, 0, 0) if i == self.f_keys_active else QColor(100, 150, 255)
                    painter.setBrush(QBrush(brush_color))
                    painter.setPen(QPen(Qt.black))
                    painter.drawRect(x, y, w, h)
                    painter.setPen(QPen(Qt.white))
                    font = QFont("Arial", 12, QFont.Bold)
                    painter.setFont(font)
                    painter.drawText(x, y, w, h, Qt.AlignCenter, key_name)
            if self.sticky_enabled:
                painter.setBrush(QBrush(QColor(255, 255, 0, 180)))
                painter.setPen(QPen(Qt.black, 2))
                painter.drawRect(10, 280, 200, 30)
                painter.setPen(QPen(Qt.black))
                font = QFont("Arial", 10, QFont.Bold)
                painter.setFont(font)
                painter.drawText(15, 300, "粘滞键: 开启")
                if self.sticky_keys:
                    sticky_text = "激活: " + ", ".join(self.sticky_keys)
                    painter.setPen(QPen(Qt.red))
                    painter.drawText(15, 315, sticky_text)
            for key_name, (x, y, w, h, color) in self.keys.items():
                # 精简：合并颜色生成逻辑，减少代码行数，全部字体改为白色
                base_color = QColor(200, 200, 200) if color == 'white' else (
                    QColor(180, 180, 180) if color == 'yellow' else (
                        QColor(140, 140, 140) if color == 'green' else QColor(100, 100, 100)))
                if key_name == self.active_key:
                    overlay = QColor(255, 30, 30, 120)
                    brush_color = QColor(
                        min(base_color.red() + overlay.red()//3, 255),
                        min(base_color.green() + overlay.green()//3, 255),
                        min(base_color.blue() + overlay.blue()//3, 255),
                        210
                    )
                    pen_color = QColor(255, 90, 90)
                elif key_name in self.sticky_keys and self.sticky_enabled:
                    overlay = QColor(255, 220, 64, 100)
                    brush_color = QColor(
                        min(base_color.red() + overlay.red()//5, 255),
                        min(base_color.green() + overlay.green()//5, 255),
                        min(base_color.blue() + overlay.blue()//5, 255),
                        180
                    )
                    pen_color = QColor(255, 220, 80)
                else:
                    # 半透明黑作为普通按键叠加
                    alpha = 125
                    brush_color = QColor(
                        max(base_color.red() - alpha//4, 0),
                        max(base_color.green() - alpha//4, 0),
                        max(base_color.blue() - alpha//4, 0),
                        210
                    )
                    pen_color = QColor(60, 60, 60)
                painter.setBrush(QBrush(brush_color))
                painter.setPen(QPen(pen_color, 2))
                painter.drawRect(x, y, w, h)
                painter.setFont(QFont("Arial", 12))
                painter.setPen(QPen(QColor(255, 255, 255)))  # 白色字体
                display_name = "Caps" if key_name == "Capslock" else key_name
                painter.drawText(x, y, w, h, Qt.AlignCenter, display_name)
            def circle_to_square_progress(x: float, y: float):
                r = math.hypot(x, y)
                if r == 0.0:
                    return 0.0, 0.0
                m = max(abs(x), abs(y))
                if m == 0.0:
                    return 0.0, 0.0
                def nonlinear_radius_mapping(r: float) -> float:
                    if r <= 0.75:
                        return (r / 0.75) * 0.5
                    else:
                        return 0.5 + ((r - 0.75) / 0.25) * 0.5
                r_nl = nonlinear_radius_mapping(r)
                k = r_nl / m
                u = max(-1.0, min(1.0, x * k))
                v = max(-1.0, min(1.0, y * k))
                return u, v
            max_x = 100
            max_y = 90
            center_left = QPoint(170, 168)
            lx = self.left_joystick_state.get('x', 0.0)
            ly = self.left_joystick_state.get('y', 0.0)
            ux, uy = circle_to_square_progress(lx, ly)
            end_left = QPoint(int(center_left.x() + ux * max_x), int(center_left.y() + uy * max_y))
            painter.setPen(QPen(QColor(120, 120, 120), 4))
            painter.drawLine(center_left, end_left)
            painter.setBrush(QBrush(QColor(120, 120, 120)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(end_left, 6, 6)
            center_right = QPoint(482, 172)
            rx = self.right_joystick_state.get('x', 0.0)
            ry = self.right_joystick_state.get('y', 0.0)
            ux, uy = circle_to_square_progress(rx, ry)
            end_right = QPoint(int(center_right.x() + ux * max_x), int(center_right.y() + uy * max_y))
            painter.setPen(QPen(QColor(120, 120, 120), 4))
            painter.drawLine(center_right, end_right)
            painter.setBrush(QBrush(QColor(120, 120, 120)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(end_right, 6, 6)
        def update_active_key(self, key):
            if self.active_key == key:
                return
            self.active_key = key
            self.update()
            if self.key_selected_callback:
                self.key_selected_callback(key)
        def toggle_sticky_mode(self):
            self.sticky_enabled = not self.sticky_enabled
            if not self.sticky_enabled:
                self.sticky_keys.clear()
            self.update()
        def toggle_f_keys_mode(self):
            self.f_keys_enabled = not self.f_keys_enabled
            if not self.f_keys_enabled:
                self.f_keys_active = 0
            self.update()
        def move_f_keys_selection(self, direction):
            if self.f_keys_enabled:
                self.f_keys_active = (self.f_keys_active + direction) % 12
                self.update()
        def get_current_f_key(self):
            if self.f_keys_enabled:
                f_key_names = list(self.f_keys.keys())
                return f_key_names[self.f_keys_active]
            return None
        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                pos = event.pos()
                from PyQt5.QtCore import QRect
                for key_name, (x, y, w, h, color) in self.keys.items():
                    rect = QRect(x, y, w, h)
                    if rect.contains(pos):
                        self.update_active_key(key_name)
                        break

    # 迁移：覆盖层用手柄线程作为内部类
    class JoystickThread(QThread):
        joystick_updated = pyqtSignal(int, float, float, bool, bool)
        def __init__(self, mapping=None):
            super().__init__()
            self.mapping = mapping
            self.running = True
            self.joysticks = []
        def run(self):
            for i in range(pygame.joystick.get_count()):
                joy = pygame.joystick.Joystick(i)
                joy.init()
                self.joysticks.append(joy)
                print(f"手柄 {i} 已连接: {joy.get_name()}")
            while self.running:
                pygame.event.pump()
                for i, joystick in enumerate(self.joysticks):
                    left_x = joystick.get_axis(0)
                    left_y = joystick.get_axis(1)
                    right_x = joystick.get_axis(2)
                    right_y = joystick.get_axis(3)
                    lb_pressed = joystick.get_button(self.mapping.left_bumper) if joystick.get_numbuttons() > self.mapping.left_bumper else False
                    rb_pressed = joystick.get_button(self.mapping.right_bumper) if joystick.get_numbuttons() > self.mapping.right_bumper else False
                    self.joystick_updated.emit(0, left_x, left_y, lb_pressed, rb_pressed)
                    self.joystick_updated.emit(1, right_x, right_y, lb_pressed, rb_pressed)
                self.msleep(16)
        def stop(self):
            self.running = False
            print("键盘操作已停止")

    # 迁移：鼠标提示窗口作为内部类
    class MouseWindow(QDialog):
        def __init__(self):
            super().__init__()
            self.initUI()
        def initUI(self):
            self.label = QLabel("↖(🎮️映射中)", self)
            self.label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 15px; color: white; border: 1px solid black; border-radius: 0px; background-color: rgba(0, 0, 0, 125);")
            self.label.adjustSize()
            screen_geometry = QApplication.primaryScreen().geometry()
            label_width = self.label.width()
            label_height = self.label.height()
            self.label.move(screen_geometry.width() - label_width - 30, screen_geometry.height() - label_height - 30)
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setWindowOpacity(0.7)
            self.setGeometry(screen_geometry)
            self.show()

class ProgressWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(10 * parent.scale_factor)}px;
                border: {int(2 * parent.scale_factor)}px solid #444444;
            }}
        """)
        self.setFixedSize(int(300 * parent.scale_factor), int(100 * parent.scale_factor))

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(int(10 * parent.scale_factor))

        self.label = QLabel("正在刷新游戏列表...")
        self.label.setStyleSheet(f"color: white; font-size: {int(16 * parent.scale_factor)}px;")
        self.layout.addWidget(self.label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: {int(2 * parent.scale_factor)}px solid #444444;
                border-radius: {int(5 * parent.scale_factor)}px;
                background: #2e2e2e;
            }}
            QProgressBar::chunk {{
                background-color: #00ff00;
                width: {int(20 * parent.scale_factor)}px;
            }}
        """)
        self.layout.addWidget(self.progress_bar)

    def update_progress(self, current, total):
        """更新进度条"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

class GameControllerThread(QThread):
    """子线程用来监听手柄输入"""
    gamepad_signal = pyqtSignal(str)
    controller_connected_signal = pyqtSignal(str)  # 新增信号，用于通知主线程手柄连接

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        pygame.init()
        self.controllers = {}
        self._running = True  # 添加运行标志
        self.last_move_time = 0
        self.move_delay = 0.1
        self.axis_threshold = 0.5
        self.last_hat_time = 0
        self.hat_delay = 0.05
        self.last_hat_value = (0, 0)

    def stop(self):
        """停止线程"""
        self._running = False
        
    # ---- DAS / ARR repeat helpers ----
    def _init_repeat_state_for_controller(self, instance_id):
        # state for directional DAS/ARR handling per controller
        self.controllers[instance_id].setdefault('repeat', {
            'dirs': {
                'UP':    {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
                'DOWN':  {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
                'LEFT':  {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
                'RIGHT': {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False},
            }
        })

    def _handle_direction_state(self, instance_id, up, down, left, right):
        """Centralized handling of directional inputs with DAS/ARR.
        Emits 'FIRST-<DIR>' on initial press, then waits DAS seconds,
        then emits repeated '<DIR>' every ARR seconds. If ARR==0 emits '<DIR>_EDGE' once.
        """
        now = time.time()
        das = getattr(self, 'das', 0.3)  # seconds before auto-repeat starts
        arr = getattr(self, 'arr', 0.07)  # repeat interval in seconds; 0 => edge jump

        repeat = self.controllers[instance_id].setdefault('repeat', {})
        dirs = repeat.setdefault('dirs', {})

        booleans = {'UP': up, 'DOWN': down, 'LEFT': left, 'RIGHT': right}

        for dname, is_pressed in booleans.items():
            state = dirs.setdefault(dname, {'pressed': False, 'next_time': 0, 'first_sent': False, 'edge_sent': False})

            if is_pressed:
                if not state['pressed']:
                    # initial press
                    state['pressed'] = True
                    state['first_sent'] = True
                    state['edge_sent'] = False
                    state['next_time'] = now + das
                    # emit FIRST event
                    self.gamepad_signal.emit(f'FIRST-{dname}')
                else:
                    # already pressed, check for repeat
                    if now >= state['next_time']:
                        if arr == 0:
                            # edge behavior: emit once
                            if not state.get('edge_sent', False):
                                state['edge_sent'] = True
                                self.gamepad_signal.emit(f'{dname}_EDGE')
                        else:
                            # emit normal repeat and schedule next
                            self.gamepad_signal.emit(dname)
                            state['next_time'] = now + arr
            else:
                # released
                if state['pressed']:
                    state['pressed'] = False
                    state['first_sent'] = False
                    state['edge_sent'] = False
                    state['next_time'] = 0
    def run(self):
        """监听手柄输入"""
        while self._running:  # 使用运行标志控制循环
            try:
                pygame.event.pump()  # 确保事件队列被更新

                # 处理事件
                for event in pygame.event.get():
                    # 处理手柄连接事件
                    if event.type == pygame.JOYDEVICEADDED:
                        try:
                            controller = pygame.joystick.Joystick(event.device_index)
                            controller.init()
                            mapping = ControllerMapping(controller)
                            self.controllers[controller.get_instance_id()] = {
                                'controller': controller,
                                'mapping': mapping
                            }
                            # 初始化 DAS/ARR 状态
                            try:
                                self._init_repeat_state_for_controller(controller.get_instance_id())
                            except Exception:
                                pass
                            print(f"Controller {controller.get_instance_id()} connected: {controller.get_name()}")
                            self.controller_connected_signal.emit(controller.get_name())
                        except pygame.error as e:
                            print(f"Failed to initialize controller {event.device_index}: {e}")
                
                    elif event.type == pygame.JOYDEVICEREMOVED:
                        if event.instance_id in self.controllers:
                            print(f"Controller {event.instance_id} disconnected")
                            del self.controllers[event.instance_id]
                        # 清理方向状态
                        try:
                            if event.instance_id in self.direction_states:
                                del self.direction_states[event.instance_id]
                        except Exception:
                            pass

                # 处理所有已连接手柄的输入
                for controller_data in self.controllers.values():
                    controller = controller_data['controller']
                    mapping = controller_data['mapping']
                    
                    # 汇总方向输入（hat, 摇杆, D-pad 按钮），统一交给 DAS/ARR 处理
                    try:
                        cid = controller.get_instance_id()
                    except Exception:
                        cid = None

                    # 初始化方向标记
                    up_pressed = down_pressed = left_pressed = right_pressed = False

                    # hat (D-pad) 处理：任何 hat 非零都会设置对应方向
                    try:
                        for i in range(controller.get_numhats()):
                            hat = controller.get_hat(i)
                            if hat != (0, 0):
                                up_pressed = up_pressed or (hat[1] == 1)
                                down_pressed = down_pressed or (hat[1] == -1)
                                left_pressed = left_pressed or (hat[0] == -1)
                                right_pressed = right_pressed or (hat[0] == 1)
                    except Exception:
                        pass

                    # 摇杆轴：合并左右两个摇杆的输入
                    try:
                        left_x = controller.get_axis(mapping.left_stick_x)
                        left_y = controller.get_axis(mapping.left_stick_y)
                        right_x = controller.get_axis(mapping.right_stick_x)
                        right_y = controller.get_axis(mapping.right_stick_y)
                    except:
                        left_x = left_y = right_x = right_y = 0

                    if left_y < -self.axis_threshold or right_y < -self.axis_threshold:
                        up_pressed = True
                    if left_y > self.axis_threshold or right_y > self.axis_threshold:
                        down_pressed = True
                    if left_x < -self.axis_threshold or right_x < -self.axis_threshold:
                        left_pressed = True
                    if left_x > self.axis_threshold or right_x > self.axis_threshold:
                        right_pressed = True

                    # D-pad 按钮（PS4 / 其他）
                    try:
                        buttons = [controller.get_button(i) for i in range(controller.get_numbuttons())]
                    except Exception:
                        buttons = []

                    try:
                        if mapping.controller_type == 'ps4' or mapping.controller_type != 'xbox360':
                            # 对于 ps4 和其他手柄，都支持 mapping 中的 dpad 按钮索引
                            if buttons and mapping.dpad_up is not None and buttons[mapping.dpad_up]:
                                up_pressed = True
                            if buttons and mapping.dpad_down is not None and buttons[mapping.dpad_down]:
                                down_pressed = True
                            if buttons and mapping.dpad_left is not None and buttons[mapping.dpad_left]:
                                left_pressed = True
                            if buttons and mapping.dpad_right is not None and buttons[mapping.dpad_right]:
                                right_pressed = True
                    except Exception:
                        pass

                    # 最后：统一处理方向状态（如果有 controller id）
                    if cid is not None:
                        # 初始化 repeat 状态（如果尚未初始化）
                        if cid not in self.controllers or 'repeat' not in self.controllers.get(cid, {}):
                            try:
                                if cid in self.controllers:
                                    self._init_repeat_state_for_controller(cid)
                            except Exception:
                                pass
                        try:
                            self._handle_direction_state(cid, up_pressed, down_pressed, left_pressed, right_pressed)
                        except Exception:
                            pass

                    # 检查动作按钮
                    if buttons[mapping.button_a]:  # A/Cross/○
                        self.gamepad_signal.emit('A')
                    if buttons[mapping.button_b]:  # B/Circle/×
                        self.gamepad_signal.emit('B')
                    if buttons[mapping.button_x]:  # X/Square/□
                        self.gamepad_signal.emit('X')
                    if buttons[mapping.button_y]:  # Y/Triangle/△
                        self.gamepad_signal.emit('Y')
                    if buttons[mapping.guide]:
                        self.gamepad_signal.emit('GUIDE')
                    if buttons[mapping.back]:  # Back
                        self.gamepad_signal.emit('BACK')
                    if buttons[mapping.start]:  # Start
                        self.gamepad_signal.emit('START')
                    if buttons[mapping.left_bumper]:  # LB
                        self.gamepad_signal.emit('LB')
                    if buttons[mapping.right_bumper]:  # RB
                        self.gamepad_signal.emit('RB')
                    #if buttons[mapping.left_trigger]:  # LT
                    #    self.gamepad_signal.emit('LT')
                    #if buttons[mapping.right_trigger]:  # RT
                    #    self.gamepad_signal.emit('RT')
                    if buttons[mapping.left_stick_in]:  # LS
                        self.gamepad_signal.emit('LS')
                    if buttons[mapping.right_stick_in]:  # RS
                        self.gamepad_signal.emit('RS')

                time.sleep(0.01)
            except Exception as e:
                print(f"Error in event loop: {e}")
                self.restart_thread()

    def restart_thread(self):
        """重启线程"""
        try:
            # 关闭所有现有的控制器
            for controller_data in self.controllers.values():
                controller_data['controller'].quit()
            self.controllers.clear()
            
            # 重新初始化 pygame
            pygame.quit()
            pygame.init()
            
            # 重置计时器和状态
            self.last_move_time = 0
            self.last_hat_time = 0
            self.last_hat_value = (0, 0)
            
            print("手柄监听线程已重启")
        except Exception as e:
            print(f"重启线程时发生错误: {e}")
class FileDialogThread(QThread):
    file_selected = pyqtSignal(str)  # 信号，用于传递选中的文件路径

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        """运行文件选择对话框"""
        file_dialog = QFileDialog()
        file_dialog.setWindowTitle("选择要启动的文件")
        file_dialog.setNameFilter("Executable and Shortcut Files (*.exe *.lnk)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        if file_dialog.exec_():
            selected_file = file_dialog.selectedFiles()[0]
            self.file_selected.emit(selected_file)  # 发射信号传递选中的文件路径
class FloatingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        bat_dir = './morefloder'
        self.current_running_apps = set()
        if not os.path.exists(bat_dir):
            os.makedirs(bat_dir)  # 创建目录
        self.select_add_btn = None  # 在初始化方法中定义
        self.select_del_btn = None  # 同样定义删除按钮
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(10 * parent.scale_factor)}px;
                border: {int(2 * parent.scale_factor)}px solid #444444;
            }}
        """)
        
        self.current_index = 0
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(int(5 * parent.scale_factor))
        self.buttons = []
        
        # 添加防抖相关属性
        self.last_input_time = 0
        self.input_delay = 200  # 设置200毫秒的防抖延迟
        
        # 读取目录中的文件
        self.files = self.get_files()
        self.create_buttons(False)
    
    def handle_gamepad_input(self, action):
        """处理手柄输入，转发到 confirm_dialog"""
        if hasattr(self, 'confirm_dialog') and self.confirm_dialog and self.confirm_dialog.isVisible():
            self.confirm_dialog.handle_gamepad_input(action)
            
    def can_process_input(self):
        """检查是否可以处理输入"""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_input_time < self.input_delay:
            return False
        self.last_input_time = current_time
        return True
    
    def get_files(self):
        """获取目录中的文件"""
        files = []
        # 获取当前目录的文件
            # 获取目录中的所有文件和文件夹
        all_files = os.listdir('./morefloder/')

        # 过滤掉文件夹，保留文件
        filess = [f for f in all_files if os.path.isfile(os.path.join('./morefloder/', f))]
        for file in filess:
            #if file.endswith(('.bat', '.url')) and not file.endswith('.lnk'):
            files.append({
                "name": os.path.splitext(file)[0],
                "path": file
            })

        return files
    #create_buttons()可刷新按钮
    def create_buttons(self, settitype=True): 
        """创建按钮"""
        self.files = self.get_files()
        if settitype:
            if self.select_add_btn:  # 确保按钮已经定义
                self.layout.removeWidget(self.select_add_btn)
            if self.select_del_btn:  # 确保按钮已经定义
                self.layout.removeWidget(self.select_del_btn)
        
        # 获取当前运行的所有进程
        self.current_running_apps.clear()
        for process in psutil.process_iter(['pid', 'exe']):
            try:
                exe_path = process.info['exe']
                if exe_path:
                    for app in more_apps:
                        if exe_path.lower() == app['path'].lower():
                            self.current_running_apps.add(app['name'])
                            break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        sorted_files = self.sort_files()
        for file in sorted_files:
            # 尝试为文件项加载图标：优先解析 .lnk 目标或 exe 并用 icoextract 提取，失败回退为图片加载
            def _get_icon_for_file(relpath, size=24):
                try:
                    abs_path = os.path.abspath(os.path.join('./morefloder/', relpath))
                    # 如果是快捷方式，解析目标
                    if abs_path.lower().endswith('.lnk'):
                        try:
                            shell = win32com.client.Dispatch('WScript.Shell')
                            shortcut = shell.CreateShortCut(abs_path)
                            target = shortcut.Targetpath
                            if target and os.path.exists(target):
                                abs_path = target
                        except Exception:
                            pass
                    # 如果目标存在且可能为可执行文件，尝试用 icoextract 提取
                    if os.path.exists(abs_path):
                        try:
                            from icoextract import IconExtractor
                            extractor = IconExtractor(abs_path)
                            bio = extractor.get_icon(num=0)
                            data = bio.getvalue()
                            pix = QPixmap()
                            if pix.loadFromData(data):
                                pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                return QIcon(pix)
                        except Exception:
                            pass
                        # 回退：尝试作为图片加载（例如 .ico/.png/.jpg）
                        try:
                            pix = QPixmap(abs_path)
                            if not pix.isNull():
                                pix = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                return QIcon(pix)
                        except Exception:
                            pass
                except Exception:
                    pass
                return QIcon()

            icon = _get_icon_for_file(file.get("path", ""), size=int(24 * self.parent().scale_factor))
            btn = QPushButton(file["name"])
            if not icon.isNull():
                btn.setIcon(icon)
                try:
                    btn.setIconSize(QSize(int(24 * self.parent().scale_factor), int(24 * self.parent().scale_factor)))
                except Exception:
                    pass
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: white;
                    text-align: left;
                    padding: {int(10 * self.parent().scale_factor)}px;
                    border: none;
                    font-size: {int(16 * self.parent().scale_factor)}px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                }}
            """)
            if file["name"] in settings.get("more_favorites", []):
                btn.setText(f"⭐ {file['name']}")
            if file["name"] in self.current_running_apps:
                btn.setText(f"🟢 {file['name']}")
            if file["name"] in settings.get("more_favorites", []) and file["name"] in self.current_running_apps:
                btn.setText(f"⭐🟢 {file['name']}")
            self.buttons.append(btn)
            self.layout.addWidget(btn)
            btn.clicked.connect(lambda checked, f=file: self.parent().execute_more_item(f, enable_mouse_sim=False))

        if settitype:
            # 重新添加按钮到布局
            if self.select_add_btn:
                self.layout.addWidget(self.select_add_btn)
            if self.select_del_btn:
                self.layout.addWidget(self.select_del_btn)
            return

        # 这里将按钮作为实例属性定义
        self.select_add_btn = QPushButton("➕ 添加项目")
        self.select_add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #888888;
                text-align: left;
                padding: {int(10 * self.parent().scale_factor)}px;
                border: none;
                font-size: {int(16 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }}
        """)
        self.select_add_btn.clicked.connect(self.select_add)
        self.layout.addWidget(self.select_add_btn)

        self.select_del_btn = QPushButton("❌ 删除项目")
        self.select_del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #888888;
                text-align: left;
                padding: {int(10 * self.parent().scale_factor)}px;
                border: none;
                font-size: {int(16 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }}
        """)
        self.select_del_btn.clicked.connect(self.select_del)
        self.layout.addWidget(self.select_del_btn)

    def select_add(self):
        self.show_add_item_window()
    def select_del(self):
        self.show_del_item_window()

    def show_add_item_window(self):
        """显示添加项目的悬浮窗"""
        # 创建悬浮窗口
        self.add_item_window = QWidget(self, Qt.Popup)
        self.add_item_window.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.add_item_window.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(15 * self.parent().scale_factor)}px;
                border: {int(2 * self.parent().scale_factor)}px solid #444444;
            }}
        """)

        layout = QVBoxLayout(self.add_item_window)
        layout.setSpacing(int(15 * self.parent().scale_factor))
        layout.setContentsMargins(int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor))

        # 第一行：编辑名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入名称")
        self.name_edit.setFixedHeight(int(50 * self.parent().scale_factor))  # 设置固定高度为 30 像素
        self.name_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: {int(1 * self.parent().scale_factor)}px solid #444444;
                border-radius: {int(10 * self.parent().scale_factor)}px;
                padding: {int(10 * self.parent().scale_factor)}px;
                font-size: {int(20 * self.parent().scale_factor)}px;
            }}
        """)
        layout.addWidget(self.name_edit)

        # 第二行：显示选择的项目
        self.selected_item_label = QLabel("")
        self.selected_item_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {int(16 * self.parent().scale_factor)}px;
                font-weight: 400;
            }}
        """)
        layout.addWidget(self.selected_item_label)

        # 第三行：选择bat、创建自定义bat按钮
        button_layout = QHBoxLayout()

        self.select_bat_button = QPushButton("选择文件")
        self.select_bat_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #5f5f5f;
                color: white;
                border: none;
                border-radius: {int(8 * self.parent().scale_factor)}px;
                padding: {int(8 * self.parent().scale_factor)}px {int(16 * self.parent().scale_factor)}px;
                font-size: {int(14 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #808080;
            }}
            QPushButton:pressed {{
                background-color: #333333;
            }}
        """)
        self.select_bat_button.clicked.connect(self.select_bat_file)
        button_layout.addWidget(self.select_bat_button)

        #self.create_custom_bat_button = QPushButton("创建自定义bat")
        #self.create_custom_bat_button.setStyleSheet(f"""
        #    QPushButton {{
        #        background-color: #404040;
        #        color: #999999;
        #        border: none;
        #        border-radius: {int(8 * self.parent().scale_factor)}px;
        #        padding: {int(8 * self.parent().scale_factor)}px {int(16 * self.parent().scale_factor)}px;
        #        font-size: {int(14 * self.parent().scale_factor)}px;
        #    }}
        #    QPushButton:hover {{
        #        background-color: #606060;
        #    }}
        #    QPushButton:pressed {{
        #        background-color: #505050;
        #    }}
        #""")
        #self.create_custom_bat_button.clicked.connect(self.show_custom_bat_editor)
        #button_layout.addWidget(self.create_custom_bat_button)

        layout.addLayout(button_layout)

        # 第四行：保存按钮
        self.save_button = QPushButton("保存")
        self.save_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #008CBA;
                color: white;
                border: none;
                border-radius: {int(8 * self.parent().scale_factor)}px;
                padding: {int(10 * self.parent().scale_factor)}px {int(20 * self.parent().scale_factor)}px;
                font-size: {int(16 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #007B9E;
            }}
            QPushButton:pressed {{
                background-color: #006F8A;
            }}
        """)
        self.save_button.clicked.connect(self.save_item)
        layout.addWidget(self.save_button)

        self.add_item_window.setLayout(layout)
        self.add_item_window.show()
    def show_del_item_window(self): 
        """显示删除项目的悬浮窗"""
        # 创建悬浮窗口
        self.del_item_window = QWidget(self, Qt.Popup)
        self.del_item_window.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.del_item_window.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(15 * self.parent().scale_factor)}px;
                border: {int(2 * self.parent().scale_factor)}px solid #444444;
            }}
        """)
        self.del_item_window.move(30, 100)

        # 使用QVBoxLayout来管理布局
        layout = QVBoxLayout(self.del_item_window)
        layout.setSpacing(int(15 * self.parent().scale_factor))
        layout.setContentsMargins(int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor))

        # 获取文件列表并创建按钮
        files = self.get_files()  # 获取文件列表
        for file in files:
            file_button = QPushButton(file["name"])
            file_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: #444444;
                    color: white;
                    text-align: center;
                    padding: {int(10 * self.parent().scale_factor)}px;
                    border: none;
                    font-size: {int(16 * self.parent().scale_factor)}px;
                }}
                QPushButton:hover {{
                    background-color: #555555;
                }}
            """)
            # 连接每个按钮点击事件到处理函数
            file_button.clicked.connect(lambda checked, f=file, btn=file_button: self.handle_del_file_button_click(f, btn))
            layout.addWidget(file_button)

        # 设置布局
        self.del_item_window.setLayout(layout)
        self.del_item_window.show()

    def handle_del_file_button_click(self, file, button):
        """处理删除文件按钮点击事件"""
        if button.property("clicked_once"):
            # 第二次点击，删除文件
            self.remove_file(file)
            # 重新加载按钮
            for button in self.buttons:
                button.setParent(None)
            self.buttons.clear()
            self.create_buttons()
            self.update_highlight()
            self.adjustSize()  # 调整窗口大小以适应内容

        else:
            # 第一次点击，变红色并更改文本
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: red;
                    color: white;
                    text-align: center;
                    padding: {int(10 * self.parent().scale_factor)}px;
                    border: none;
                    font-size: {int(16 * self.parent().scale_factor)}px;
                }}
            """)
            button.setText("删除？(再次点击确认)")
            button.setProperty("clicked_once", True)

    def remove_file(self, file):
        """删除文件并更新设置"""
        file_path = os.path.join('./morefloder/', file["path"])  # 获取文件的完整路径
        if os.path.exists(file_path):
            os.remove(file_path)  # 删除文件

            # 重新加载删除项窗口，确保界面更新
            self.del_item_window.close()  # 关闭删除项目窗口
            self.show_del_item_window()  # 重新加载删除项目窗口
        else:
            print(f"文件 {file['name']} 不存在！")
    def select_bat_file(self):
        """选择bat文件（非阻塞）"""
        # 先隐藏所有相关弹窗
        if hasattr(self, 'add_item_window') and self.add_item_window.isVisible():
            self.add_item_window.hide()
        if hasattr(self, 'del_item_window') and self.del_item_window.isVisible():
            self.del_item_window.hide()
        self.hide()
        # 启动文件选择线程
        self.file_dialog_thread = FileDialogThread(self)
        self.file_dialog_thread.file_selected.connect(self.handle_file_selected)  # 连接信号到槽
        self.file_dialog_thread.start()  # 启动线程 
    def handle_file_selected(self, selected_file):
        """处理选中的文件"""
        self.show()
        self.add_item_window.show()
        self.selected_item_label.setText(selected_file)
        self.name_edit.setText(os.path.splitext(os.path.basename(selected_file))[0])  # 只填入文件名部分
        # 保持悬浮窗可见
        self.add_item_window.show()

    #def show_custom_bat_editor(self):
    #    """显示自定义bat编辑器"""
    #    # 创建自定义 BAT 编辑器窗口
    #    self.custom_bat_editor = QWidget(self, Qt.Popup)
    #    self.custom_bat_editor.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
    #    self.custom_bat_editor.setStyleSheet(f"""
    #        QWidget {{
    #            background-color: rgba(46, 46, 46, 0.95);
    #            border-radius: {int(15 * self.parent().scale_factor)}px;
    #            border: {int(2 * self.parent().scale_factor)}px solid #444444;
    #        }}
    #    """)
#
    #    layout = QVBoxLayout(self.custom_bat_editor)
    #    layout.setSpacing(int(15 * self.parent().scale_factor))
    #    layout.setContentsMargins(int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor), int(20 * self.parent().scale_factor))
#
    #    # 文本框：显示和编辑 bat 脚本
    #    self.bat_text_edit = QTextEdit()
    #    self.bat_text_edit.setPlaceholderText("请输入脚本内容...")
    #    self.bat_text_edit.setStyleSheet(f"""
    #        QTextEdit {{
    #            background-color: rgba(255, 255, 255, 0.1);
    #            color: white;
    #            border: {int(1 * self.parent().scale_factor)}px solid #444444;
    #            border-radius: {int(10 * self.parent().scale_factor)}px;
    #            padding: {int(12 * self.parent().scale_factor)}px;
    #            font-size: {int(14 * self.parent().scale_factor)}px;           
    #        }}
    #    """)
    #    layout.addWidget(self.bat_text_edit)
#
    #    # 添加程序按钮
    #    self.add_program_button = QPushButton("添加程序")
    #    self.add_program_button.setStyleSheet(f"""
    #        QPushButton {{
    #            background-color: #5f5f5f;
    #            color: white;
    #            border: none;
    #            border-radius: {int(8 * self.parent().scale_factor)}px;
    #            padding: {int(10 * self.parent().scale_factor)}px {int(20 * self.parent().scale_factor)}px;
    #            font-size: {int(14 * self.parent().scale_factor)}px;
    #        }}
    #        QPushButton:hover {{
    #            background-color: #808080;
    #        }}
    #        QPushButton:pressed {{
    #            background-color: #333333;
    #        }}
    #    """)
    #    self.add_program_button.clicked.connect(self.add_program_to_bat)
    #    layout.addWidget(self.add_program_button)
#
    #    # 保存bat按钮
    #    self.save_bat_button = QPushButton("保存bat")
    #    self.save_bat_button.setStyleSheet(f"""
    #        QPushButton {{
    #            background-color: #4CAF50;
    #            color: white;
    #            border: none;
    #            border-radius: {int(8 * self.parent().scale_factor)}px;
    #            padding: {int(10 * self.parent().scale_factor)}px {int(20 * self.parent().scale_factor)}px;
    #            font-size: {int(16 * self.parent().scale_factor)}px;
    #        }}
    #        QPushButton:hover {{
    #            background-color: #45a049;
    #        }}
    #        QPushButton:pressed {{
    #            background-color: #388e3c;
    #        }}
    #    """)
    #    self.save_bat_button.clicked.connect(self.save_custom_bat)
    #    layout.addWidget(self.save_bat_button)
    #    self.custom_bat_editor.move(0, 100)
    #    self.custom_bat_editor.setLayout(layout)
    #    self.custom_bat_editor.show()


    #def add_program_to_bat(self):
    #    """添加程序到bat"""
    #    file_dialog = QFileDialog(self, "选择一个可执行文件", "", "Executable Files (*.exe)")
    #    file_dialog.setFileMode(QFileDialog.ExistingFile)
    #    if file_dialog.exec_():
    #        selected_file = file_dialog.selectedFiles()[0]
    #        program_dir = os.path.dirname(selected_file)
    #        self.bat_text_edit.append(f'cd /d "{program_dir}"\nstart "" "{selected_file}"\n')
    #        self.add_item_window.show()
    #        self.custom_bat_editor.show()
#
    #def save_custom_bat(self):
    #    """保存自定义bat"""
    #    bat_dir = './bat/Customize'
    #    if not os.path.exists(bat_dir):
    #        os.makedirs(bat_dir)  # 创建目录
    #    bat_content = self.bat_text_edit.toPlainText()
    #    bat_path = os.path.join(program_directory, "./bat/Customize/Customize.bat")
    #    counter = 1
    #    while os.path.exists(bat_path):
    #        bat_path = os.path.join(program_directory, f"./bat/Customize/Customize_{counter}.bat")
    #        counter += 1
    #    bat_path = os.path.abspath(bat_path)
    #    with open(bat_path, "w", encoding="utf-8") as f:
    #        f.write(bat_content)
    #    self.selected_item_label.setText(bat_path)
    #    self.custom_bat_editor.hide()
    #    self.add_item_window.show()

    def save_item(self):
        """保存项目"""
        name = self.name_edit.text()
        path = self.selected_item_label.text()  
        bat_dir = './morefloder'
        if not os.path.exists(bat_dir):
            os.makedirs(bat_dir)

        shortcut_name = name + ".lnk"
        shortcut_path = os.path.join(bat_dir, shortcut_name)
        # 如果是lnk文件，直接复制
        if path.endswith('.lnk'):
            shutil.copy(path, shortcut_path)
        else:
            # 创建新的快捷方式
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = path
            shortcut.WorkingDirectory = os.path.dirname(path)
            shortcut.save()
        
        print(f"快捷方式已创建: {shortcut_path}")
        self.add_item_window.hide()
        load_morefloder_shortcuts()
        # 重新加载按钮
        for button in self.buttons:
            button.setParent(None)
        self.buttons.clear()
        self.create_buttons()
        self.update_highlight()
        self.show()
    def sort_files(self):
        """排序文件"""
        sorted_files = []
        
        # 获取收藏和最近使用的列表
        favorites = settings.get("more_favorites", [])
        last_used = settings.get("more_last_used", [])
        
        # 添加收藏的文件
        for name in favorites:
            for file in self.files:
                if file["name"] == name:
                    sorted_files.append(file)
                    break
        
        # 添加最近使用的文件
        for name in last_used:
            for file in self.files:
                if file["name"] == name and file["name"] not in favorites:
                    sorted_files.append(file)
                    break
        
        # 添加其他文件
        for file in self.files:
            if file["name"] not in favorites and file["name"] not in last_used:
                sorted_files.append(file)
        
        return sorted_files
    
    def update_highlight(self):
        """更新高亮状态"""
        for i, button in enumerate(self.buttons):
            if i == self.current_index:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: white;
                        text-align: left;
                        padding: {int(10 * self.parent().scale_factor)}px;
                        border: {int(2 * self.parent().scale_factor)}px solid #93ffff;
                        font-size: {int(16 * self.parent().scale_factor)}px;
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: white;
                        text-align: left;
                        padding: {int(10 * self.parent().scale_factor)}px;
                        border: none;
                        font-size: {int(16 * self.parent().scale_factor)}px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.1);
                    }}
                """)
    
    def toggle_favorite(self):
        """切换收藏状态"""
        sorted_files = self.sort_files()
        current_file = sorted_files[self.current_index]
        if current_file["name"] in self.current_running_apps:
            # 创建确认弹窗
            if not self.parent().is_mouse_simulation_running == True:
                self.confirm_dialog = ConfirmDialog(f"是否关闭下列程序？\n{current_file['name']}", scale_factor=self.scale_factor)
                result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
                self.ignore_input_until = pygame.time.get_ticks() + 350  # 设置屏蔽时间为800毫秒
            else:
                result = False
            # 关闭窗口
            self.current_index = 0
            self.update_highlight()
            self.hide()
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            # 修正：用 more_apps 查找真实路径
            exe_path = None
            for app in more_apps:
                if app["name"] == current_file["name"]:
                    exe_path = app["path"]
                    break
            if exe_path:
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        if proc.info['exe'] and os.path.abspath(proc.info['exe']) == os.path.abspath(exe_path):
                            print(f"找到进程: {proc.info['name']} (PID: {proc.info['pid']})")
                            proc.terminate()  # 结束进程
                            proc.wait()  # 等待进程完全终止
                            return
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
            return
        else:
            if "more_favorites" not in settings:
                settings["more_favorites"] = []

            if current_file["name"] in settings["more_favorites"]:
                settings["more_favorites"].remove(current_file["name"])
            else:
                settings["more_favorites"].append(current_file["name"])

            # 保存设置
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            
        # 重新加载按钮
        for button in self.buttons:
            button.setParent(None)
        self.buttons.clear()
        self.create_buttons()
        self.update_highlight()

    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key_Up:
            self.current_index = (self.current_index - 1) % len(self.buttons)
            self.update_highlight()
        elif event.key() == Qt.Key_Down:
            self.current_index = (self.current_index + 1) % len(self.buttons)
            self.update_highlight()

class ControllerMapping:
    """手柄按键映射类"""
    #https://www.pygame.org/docs/ref/joystick.html
    def __init__(self, controller):
        self.controller = controller
        self.controller_name = controller.get_name()
        self.setup_mapping()
        
    def setup_mapping(self):
        """根据手柄类型设置按键映射"""
        # 默认映射（用于未识别的手柄）
        self.button_a = 0
        self.button_b = 1
        self.button_x = 2
        self.button_y = 3
        self.dpad_up = 11
        self.dpad_down = 12
        self.dpad_left = 13
        self.dpad_right = 14
        self.guide = 5
        self.left_stick_x = 0
        self.left_stick_y = 1
        self.right_stick_x = 3
        self.right_stick_y = 4
        self.has_hat = False
        self.controller_type = "unknown"  # 添加控制器类型标识
        
        # Xbox 360 Controller
        if "Xbox 360 Controller" in self.controller_name:
            self.controller_type = "xbox360"
            # 按钮映射
            self.button_a = 0
            self.button_b = 1
            self.button_x = 2
            self.button_y = 3
            
            # 摇杆映射
            self.left_stick_x = 0   # 左摇杆左右
            self.left_stick_y = 1   # 左摇杆上下
            self.right_stick_x = 2  # 右摇杆左右
            self.right_stick_y = 3  # 右摇杆上下
            
            # 扳机键映射（如果需要）
            self.left_trigger = 2   # 左扳机
            self.right_trigger = 5  # 右扳机
            
            # 其他按钮映射（如果需要）
            self.left_bumper = 4    # 左肩键
            self.right_bumper = 5   # 右肩键
            self.back = 6           # Back 键
            self.start = 7          # Start 键
            self.left_stick_in = 8  # 左摇杆按下
            self.right_stick_in = 9 # 右摇杆按下
            self.guide = 10         # Guide 键
            
            # D-pad 使用 hat
            self.has_hat = True
        
        # PS4 Controller
        elif "PS4 Controller" in self.controller_name:
            self.controller_type = "ps4"
            self.button_a = 0  # Cross
            self.button_b = 1  # Circle
            self.button_x = 2  # Square
            self.button_y = 3  # Triangle
            self.left_bumper = 9    # 左肩键
            self.right_bumper = 10   # 右肩键
            self.dpad_up = 11
            self.dpad_down = 12
            self.dpad_left = 13
            self.dpad_right = 14
            self.left_stick_x = 0
            self.left_stick_y = 1
            self.right_stick_x = 2
            self.right_stick_y = 3
            self.guide = 5         # PS 键
            self.back = 4
            self.start = 6
            self.left_stick_in = 7  # 左摇杆按下
            self.right_stick_in = 8 # 右摇杆按下

            
        # PS5 Controller
        elif "Sony Interactive Entertainment Wireless Controller" in self.controller_name:
            self.button_a = 0  # Cross
            self.button_b = 1  # Circle
            self.button_x = 2  # Square
            self.button_y = 3  # Triangle
            self.has_hat = True
            self.left_stick_x = 0
            self.left_stick_y = 1
            self.right_stick_x = 3
            self.right_stick_y = 4
            self.guide = 10         # PS 键
            
        # Nintendo Switch Joy-Con (Left)
        elif "Wireless Gamepad" in self.controller_name and self.controller.get_numbuttons() == 11:
            self.dpad_up = 0
            self.dpad_down = 1
            self.dpad_left = 2
            self.dpad_right = 3
            self.left_stick_x = 0
            self.left_stick_y = 1
            
        # Nintendo Switch Joy-Con (Right)
        elif "Wireless Gamepad" in self.controller_name:
            self.button_a = 0
            self.button_b = 1
            self.button_x = 2
            self.button_y = 3
            self.right_stick_x = 0
            self.right_stick_y = 1
            self.guide = 12
            
        #print(f"Detected controller: {self.controller_name}")

class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(10 * parent.scale_factor)}px;
                border: {int(2 * parent.scale_factor)}px solid #444444;
            }}
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(int(5 * parent.scale_factor))
        # 添加调整主页游戏数量的选项
        self.buttonsindexset_label = QLabel(f"主页游戏数量: {parent.buttonsindexset}")
        self.buttonsindexset_label.setStyleSheet(f"color: white; font-size: {int(16 * parent.scale_factor)}px;")
        self.buttonsindexset_label.setFixedHeight(int(30 * parent.scale_factor))  # 固定高度为30像素
        self.layout.addWidget(self.buttonsindexset_label)

        self.buttonsindexset_slider = QSlider(Qt.Horizontal)
        self.buttonsindexset_slider.setMinimum(4)
        self.buttonsindexset_slider.setMaximum(12)
        self.buttonsindexset_slider.setValue(parent.buttonsindexset)
        self.buttonsindexset_slider.valueChanged.connect(self.update_buttonsindexset)
        self.layout.addWidget(self.buttonsindexset_slider)

        # 添加调整 row_count 的选项
        self.row_count_label = QLabel(f"每行游戏数量(所有处): {parent.row_count}")
        self.row_count_label.setStyleSheet(f"color: white; font-size: {int(16 * parent.scale_factor)}px;")
        self.row_count_label.setFixedHeight(int(30 * parent.scale_factor))  # 固定高度为30像素
        self.layout.addWidget(self.row_count_label)

        self.row_count_slider = QSlider(Qt.Horizontal)
        self.row_count_slider.setMinimum(4)
        self.row_count_slider.setMaximum(10)
        self.row_count_slider.setValue(parent.row_count)
        self.row_count_slider.valueChanged.connect(self.update_row_count)
        self.layout.addWidget(self.row_count_slider)



        # 添加查看游戏时间排名按钮
        self.play_time_rank_button = QPushButton("查看游玩时长汇总")
        self.play_time_rank_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        self.play_time_rank_button.clicked.connect(self.show_play_time_rank_window)
        self.layout.addWidget(self.play_time_rank_button)

        # 添加重启程序按钮
        restart_button = QPushButton("重启程序")
        restart_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        restart_button.clicked.connect(self.restart_program)
        self.layout.addWidget(restart_button)

        # 添加刷新游戏按钮
        self.refresh_button = QPushButton("---管理---")
        self.refresh_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(15 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        self.refresh_button.clicked.connect(parent.refresh_games)
        self.layout.addWidget(self.refresh_button)

        # 添加快速添加运行中游戏按钮
        self.quick_add_running_btn = QPushButton("-快速添加运行中游戏-")
        self.quick_add_running_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        self.quick_add_running_btn.clicked.connect(self.quick_add_running_game)
        self.layout.addWidget(self.quick_add_running_btn)

        # 添加切换 killexplorer 状态的按钮
        self.killexplorer_button = QPushButton(f"沉浸模式 {'√' if settings.get('killexplorer', False) else '×'}")
        self.killexplorer_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        self.killexplorer_button.clicked.connect(self.toggle_killexplorer)
        self.layout.addWidget(self.killexplorer_button)
        #self.custom_valid_apps_button = QPushButton("-自定义游戏进程列表-")
        #self.custom_valid_apps_button.setStyleSheet(f"""
        #    QPushButton {{
        #        background-color: #444444;
        #        color: white;
        #        text-align: center;
        #        padding: {int(10 * parent.scale_factor)}px;
        #        border: none;
        #        font-size: {int(16 * parent.scale_factor)}px;
        #    }}
        #    QPushButton:hover {{
        #        background-color: #555555;
        #    }}
        #""")
        #self.custom_valid_apps_button.clicked.connect(self.show_del_custom_valid_apps_dialog)
        #self.layout.addWidget(self.custom_valid_apps_button)
        # 添加回到主页时尝试冻结运行中的游戏按钮
        self.freeze_button = QPushButton(f"回主页时尝试冻结游戏 {'√' if settings.get('freeze', False) else '×'}")
        self.freeze_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        self.freeze_button.clicked.connect(self.toggle_freeze)
        self.layout.addWidget(self.freeze_button)

        self.open_folder_button = QPushButton("开启/关闭-开机自启")
        self.open_folder_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """)
        self.open_folder_button.clicked.connect(self.is_startup_enabled)
        self.layout.addWidget(self.open_folder_button)

        # 在其他按钮之后添加关闭程序按钮
        self.close_program_button = QPushButton("关闭程序")
        self.close_program_button.setStyleSheet(f"""
            QPushButton {{
                background-color: BLACK; 
                color: white;
                text-align: center;
                padding: {int(10 * parent.scale_factor)}px;
                border: none;
                font-size: {int(16 * parent.scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #ff6666;
            }}
        """)
        self.close_program_button.clicked.connect(self.close_program)
        self.layout.addWidget(self.close_program_button)
        
        self.asdasgg_label = QLabel(
            '<span style="color: white;">'
            '<a href="#" style="color: white; text-decoration: none;">（提示＆关于）</a>'
            '</span>'
        )
        self.asdasgg_label.setTextFormat(Qt.RichText)
        self.asdasgg_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.asdasgg_label.setOpenExternalLinks(False)
        self.asdasgg_label.setFixedHeight(int(30 * parent.scale_factor))
        self.asdasgg_label.setAlignment(Qt.AlignCenter)
        self.asdasgg_label.linkActivated.connect(lambda _: self.show_about_dialog())
        self.layout.addWidget(self.asdasgg_label)

    def show_about_dialog(self):
        """显示关于窗口"""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("关于 DeskGamix")
        about_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        about_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(46, 46, 46, 0.98);
                border-radius: {int(15 * self.parent().scale_factor)}px;
                border: {int(2 * self.parent().scale_factor)}px solid #444444;
            }}
        """)
        about_dialog.setFixedWidth(int(1200 * self.parent().scale_factor))
        layout = QVBoxLayout(about_dialog)
        layout.setSpacing(int(18 * self.parent().scale_factor))
        layout.setContentsMargins(
            int(30 * self.parent().scale_factor),
            int(30 * self.parent().scale_factor),
            int(30 * self.parent().scale_factor),
            int(30 * self.parent().scale_factor)
        )
    
        # 顶部图标和标题
        icon_title_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_pix = QPixmap("./_internal/fav.ico").scaled(int(36 * self.parent().scale_factor), int(36 * self.parent().scale_factor), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(icon_pix)
        icon_label.setFixedSize(int(36 * self.parent().scale_factor), int(36 * self.parent().scale_factor))
        icon_title_layout.addWidget(icon_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        title_label = QLabel("DeskGamix")
        title_label.setStyleSheet(f"color: white; font-size: {int(26 * self.parent().scale_factor)}px; font-weight: bold;")
        icon_title_layout.addWidget(title_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        icon_title_layout.addStretch()
        layout.addLayout(icon_title_layout)
    
        # 软件简介
        intro = QLabel("桌面游戏启动器\n"
                       "支持手柄一键启动、收藏、截图等功能，"
                       "支持自定义快捷方式、进程管理、游戏冻结等多种实用功能。\n"
                       "专为Windows手柄操作优化。\n长按start+back打开鼠标映射。"
                       "在手柄鼠标映射启用时点击系统托盘图标可停止映射\n\n"
                       "手柄鼠标映射键位操作示意图：")
        intro.setStyleSheet(f"color: white; font-size: {int(18 * self.parent().scale_factor)}px;")
        intro.setWordWrap(True)
        layout.addWidget(intro)
    
        # 手柄映射示意图
        #'<a href="https://wwse.lanzn.com/b00uz4bjmd" style="color:#93ffff;">蓝奏（密码:85jl）</a>　|　'
        title_label = QLabel(
            '<a href="https://github.com/gmaox/DeskGamix" style="color:#93ffff;">GitHub</a>　|　'
            '<a href="https://space.bilibili.com/258889407" style="color:#93ffff;">B站主页</a>'
        )
        title_label.setStyleSheet(f"color: white; font-size: {int(26 * self.parent().scale_factor)}px; ")
        title_label.setOpenExternalLinks(True)
        icon_title_layout.addWidget(title_label, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        img_label = QLabel()
        try:
            pixmap = QPixmap("./_internal/1.png").scaled(
                int(1150 * self.parent().scale_factor),
                int(660 * self.parent().scale_factor),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            img_label.setPixmap(pixmap)
        except Exception:
            img_label.setText("未找到1.png")
        img_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(img_label)
    
        # 链接
        #link_label = QLabel(
        #    '<a href="https://github.com/DeskGamix/DeskGamix" style="color:#93ffff;">GitHub主页</a>　|　'
        #    '<a href="https://space.bilibili.com/349308" style="color:#93ffff;">B站主页</a>'
        #)
        #link_label.setStyleSheet(f"color: #93ffff; font-size: {int(18 * self.parent().scale_factor)}px;")
        #link_label.setAlignment(Qt.AlignCenter)
        #link_label.setOpenExternalLinks(True)
        #layout.addWidget(link_label)
    
        ## 关闭按钮
        #close_btn = QPushButton("关闭")
        #close_btn.setStyleSheet(f"""
        #    QPushButton {{
        #        background-color: #444444;
        #        color: white;
        #        border-radius: {int(8 * self.parent().scale_factor)}px;
        #        font-size: {int(16 * self.parent().scale_factor)}px;
        #        padding: {int(10 * self.parent().scale_factor)}px {int(30 * self.parent().scale_factor)}px;
        #    }}
        #    QPushButton:hover {{
        #        background-color: #555555;
        #    }}
        #""")
        #close_btn.clicked.connect(about_dialog.accept)
        #layout.addWidget(close_btn, alignment=Qt.AlignCenter)
    
        about_dialog.setLayout(layout)
        # 居中显示
        parent_geom = self.parent().geometry()
        x = parent_geom.x() + (parent_geom.width() - about_dialog.width()) // 2
        y = 100 * self.parent().scale_factor
        about_dialog.move(x, y)
        about_dialog.exec_()

    def quick_add_running_game(self):
        """快速添加运行中游戏"""
        # 弹出进程选择窗口
        proc_dialog = QDialog(self)
        proc_dialog.setWindowTitle("选择运行中游戏进程")
        proc_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        proc_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(46, 46, 46, 0.98);
                border-radius: {int(10 * self.parent().scale_factor)}px;
                border: {int(2 * self.parent().scale_factor)}px solid #444444;
            }}
        """)
        vbox = QVBoxLayout(proc_dialog)
        vbox.setSpacing(int(10 * self.parent().scale_factor))
        vbox.setContentsMargins(
            int(20 * self.parent().scale_factor),
            int(20 * self.parent().scale_factor),
            int(20 * self.parent().scale_factor),
            int(20 * self.parent().scale_factor)
        )
        label = QLabel("选择一个运行中游戏进程，加入到游戏列表。（steam/EPIC等启动器需求游戏推荐steam等软件中创建快捷方式用QSAA导入）")
        label.setStyleSheet("color: white; font-size: 16px;")
        vbox.addWidget(label)
        # 枚举所有有前台窗口且不是隐藏的进程
        hwnd_pid_map = {}
        def enum_window_callback(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                hwnd_pid_map[pid] = hwnd
            return True
        win32gui.EnumWindows(enum_window_callback, None)

        # 收集进程信息
        proc_list = []
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if (
                    proc.info['pid'] in hwnd_pid_map
                    and proc.info['exe']
                    and proc.info['name'].lower() != "explorer.exe"
                    and proc.info['name'].lower() != "desktopgame.exe"   # 屏蔽自身
                    and proc.info['name'].lower() != "textinputhost.exe"       
                ):
                    proc_list.append(proc)
            except Exception:
                continue

        if not proc_list:
            label = QLabel("没有检测到可用进程")
            label.setStyleSheet("color: white; font-size: 16px;")
            vbox.addWidget(label)
        else:
            for proc in proc_list:
                proc_name = proc.info.get('name', '未知')
                proc_exe = proc.info.get('exe', '')
                # 创建横向布局
                hbox = QHBoxLayout()
                hbox.setSpacing(8)
                # 进程按钮
                btn = QPushButton(f"{proc_name} ({proc_exe})")
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #444444;
                        color: white;
                        border-radius: {int(8 * self.parent().scale_factor)}px;
                        font-size: {int(14 * self.parent().scale_factor)}px;
                        padding: {int(8 * self.parent().scale_factor)}px;
                        text-align: left;
                    }}
                    QPushButton:hover {{
                        background-color: #555555;
                    }}
                """)
                btn.clicked.connect(lambda checked, exe=proc.info['exe']: self.run_quick_add_and_restart(exe, proc_dialog))
                hbox.addWidget(btn)
                # 文件夹小按钮
                folder_btn = QPushButton("📁")
                folder_btn.setFixedSize(32, 32)
                folder_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #666666;
                        color: white;
                        border-radius: 6px;
                        font-size: 18px;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: #888888;
                    }}
                """)
                def open_file_dialog(proc_exe=proc_exe):
                    # 打开文件选择器，初始目录为exe所在目录
                    start_dir = os.path.dirname(proc_exe) if proc_exe and os.path.exists(proc_exe) else ""
                    file_dialog = QFileDialog(proc_dialog)
                    file_dialog.setWindowTitle("手动选择要添加的游戏文件")
                    file_dialog.setNameFilter("可执行文件 (*.exe *.lnk)")
                    file_dialog.setFileMode(QFileDialog.ExistingFile)
                    if start_dir:
                        file_dialog.setDirectory(start_dir)
                    if file_dialog.exec_():
                        selected_file = file_dialog.selectedFiles()[0]
                        self.run_quick_add_and_restart(selected_file, proc_dialog)
                folder_btn.clicked.connect(lambda checked, proc_exe=proc_exe: open_file_dialog(proc_exe))
                hbox.addWidget(folder_btn)
                vbox.addLayout(hbox)

        proc_dialog.setLayout(vbox)
        x = 350 * self.parent().scale_factor
        y = 100 * self.parent().scale_factor
        proc_dialog.move(x, y)
        proc_dialog.show()

    def run_quick_add_and_restart(self, exe_path, dialog):
        """调用QuickStreamAppAdd.exe并重启"""
        dialog.accept()
        # 启动QuickStreamAppAdd.exe并传递exe路径参数
        self.qsaa_thread = QuickStreamAppAddThread(args=["-addlnk", str(exe_path)])
        if self.parent() and hasattr(self.parent(), "deep_reload_games"):
            self.qsaa_thread.finished_signal.connect(self.parent().deep_reload_games)
        self.qsaa_thread.start()

    def show_play_time_rank_window(self):
        """显示游戏时长排名悬浮窗"""
        # 创建悬浮窗口
        self.add_item_window = QWidget(self, Qt.Popup)
        self.add_item_window.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.add_item_window.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(46, 46, 46, 0.98);
                border-radius: {int(15 * self.parent().scale_factor)}px;
                border: {int(2 * self.parent().scale_factor)}px solid #444444;
            }}
        """)
        self.add_item_window.setMinimumWidth(int(500 * self.parent().scale_factor))
        layout = QVBoxLayout(self.add_item_window)
        layout.setSpacing(int(15 * self.parent().scale_factor))
        layout.setContentsMargins(
            int(20 * self.parent().scale_factor),
            int(20 * self.parent().scale_factor),
            int(20 * self.parent().scale_factor),
            int(20 * self.parent().scale_factor)
        )

        # 获取并排序游戏时长
        play_time_dict = settings.get("play_time", {})
        sorted_games = sorted(play_time_dict.items(), key=lambda x: x[1], reverse=True)
        # 计算总游戏时长
        total_minutes = sum(play_time for _, play_time in sorted_games)
        if total_minutes < 60:
            total_time_str = f"总游戏时长：{total_minutes} 分钟"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            total_time_str = f"总游戏时长：{hours} 小时 {minutes} 分钟"
        total_label = QLabel(total_time_str)
        total_label.setStyleSheet(f"color: #FFD700; font-size: {int(15 * self.parent().scale_factor)}px; font-weight: bold; border: none; ")
        layout.addWidget(total_label)
        if not sorted_games:
            label = QLabel("暂无游戏时长数据")
            label.setStyleSheet("color: white; font-size: 18px; border: none;")
            layout.addWidget(label)
        else:
            max_time = sorted_games[0][1] if sorted_games[0][1] > 0 else 1
            for idx, (game, play_time) in enumerate(sorted_games):
                # 游戏名
                name_label = QLabel(game)
                name_label.setStyleSheet(f"color: white; font-size: {int(18 * self.parent().scale_factor)}px; font-weight: bold; border: none;")
                layout.addWidget(name_label)
                
                # 时长文本
                if play_time < 60:
                    play_time_str = f"游玩时间：{play_time} 分钟"
                else:
                    hours = play_time // 60
                    minutes = play_time % 60
                    play_time_str = f"游玩时间：{hours} 小时 {minutes} 分钟"
                time_label = QLabel(play_time_str)
                time_label.setStyleSheet(f"color: white; font-size: {int(16 * self.parent().scale_factor)}px; border: none;")
                layout.addWidget(time_label)

                # 进度条
                progress = int(play_time / max_time * 100)
                progress_bar = QProgressBar()
                progress_bar.setMaximum(100)
                progress_bar.setValue(progress)
                progress_bar.setTextVisible(False)
                # 选择进度条颜色
                if progress >= 90:
                    bar_color = "#FE8601"
                elif progress >= 80:
                    bar_color = "#A62ECD"
                elif progress >= 40:
                    bar_color = "#3F84DF"
                else:
                    bar_color = "#9DC464"
                progress_bar.setStyleSheet(f"""
                    QProgressBar {{
                        border: {int(1 * self.parent().scale_factor)}px solid #444444;
                        border-radius: {int(5 * self.parent().scale_factor)}px;
                        background: #2e2e2e;
                        height: {int(4 * self.parent().scale_factor)}px;
                        min-height: {int(4 * self.parent().scale_factor)}px;
                        max-height: {int(4 * self.parent().scale_factor)}px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {bar_color};
                        width: {int(20 * self.parent().scale_factor)}px;
                    }}
                """)
                layout.addWidget(progress_bar)

                # 分割线（最后一项不加）
                if idx < len(sorted_games) - 1:
                    line = QFrame()
                    line.setFrameShape(QFrame.HLine)
                    line.setFrameShadow(QFrame.Sunken)
                    line.setStyleSheet("background-color: #444; border: none; min-height: 2px; max-height: 2px;")
                    layout.addWidget(line)

        self.add_item_window.setLayout(layout)
        # 居中显示
        parent_geom = self.parent().geometry()
        win_geom = self.add_item_window.frameGeometry()
        #x = parent_geom.x() + (parent_geom.width() - win_geom.width()) // 2
        #y = parent_geom.y() + (parent_geom.height() - win_geom.height()) // 2
        x = 350 * self.parent().scale_factor
        y = 100 * self.parent().scale_factor
        self.add_item_window.move(x, y)
        self.add_item_window.show()

    #def show_del_custom_valid_apps_dialog(self):
    #    """显示删除自定义valid_apps条目的窗口"""
    #    self.del_dialog = QDialog(self)
    #    self.del_dialog.setWindowTitle("删除自定义游戏进程")
    #    self.del_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
    #    self.del_dialog.setStyleSheet(f"""
    #        QDialog {{
    #            background-color: rgba(46, 46, 46, 0.95);
    #            border-radius: {int(15 * self.parent().scale_factor)}px;
    #            border: {int(2 * self.parent().scale_factor)}px solid #444444;
    #        }}
    #    """)
    #    layout = QVBoxLayout(self.del_dialog)
    #    layout.setSpacing(int(15 * self.parent().scale_factor))
    #    layout.setContentsMargins(
    #        int(20 * self.parent().scale_factor),
    #        int(20 * self.parent().scale_factor),
    #        int(20 * self.parent().scale_factor),
    #        int(20 * self.parent().scale_factor)
    #    )
    #
    #    # 添加"+添加自定义进程"按钮
    #    add_btn = QPushButton("+添加自定义进程")
    #    add_btn.setStyleSheet(f"""
    #        QPushButton {{
    #            background-color: #008CBA;
    #            color: white;
    #            border-radius: {int(8 * self.parent().scale_factor)}px;
    #            font-size: {int(16 * self.parent().scale_factor)}px;
    #            padding: {int(10 * self.parent().scale_factor)}px;
    #        }}
    #        QPushButton:hover {{
    #            background-color: #007B9E;
    #        }}
    #    """)
    #    add_btn.clicked.connect(lambda: [self.del_dialog.accept(), self.show_custom_valid_apps_dialog()])
    #    layout.addWidget(add_btn)
    #
    #    # 获取自定义条目列表
    #    custom_list = settings.get("custom_valid_apps", [])
    #    if not custom_list:
    #        label = QLabel("暂无自定义条目")
    #        label.setStyleSheet("color: white; font-size: 16px;")
    #        layout.addWidget(label)
    #    else:
    #        for idx, item in enumerate(custom_list):
    #            btn = QPushButton(f"{item['name']} ({item['path']})")
    #            btn.setStyleSheet(f"""
    #                QPushButton {{
    #                    background-color: #444444;
    #                    color: white;
    #                    text-align: left;
    #                    padding: {int(10 * self.parent().scale_factor)}px;
    #                    border: none;
    #                    font-size: {int(16 * self.parent().scale_factor)}px;
    #                }}
    #                QPushButton:hover {{
    #                    background-color: #3f3f3f;
    #                    color: white;
    #                }}
    #            """)
    #            def handle_del(i=idx, b=btn, current_item=item):
    #                # 第一次点击变红
    #                if not hasattr(b, "_clicked_once"):
    #                    b.setStyleSheet(f"""
    #                        QPushButton {{
    #                            background-color: #ff4444;
    #                            color: yellow;
    #                            text-align: left;
    #                            padding: {int(10 * self.parent().scale_factor)}px;
    #                            border: none;
    #                            font-size: {int(16 * self.parent().scale_factor)}px;
    #                        }}
    #                    """)
    #                    b.setText("确认删除？(再次点击)")
    #                    b._clicked_once = True
    #                else:
    #                    # 第二次点击删除
    #                    del settings["custom_valid_apps"][i]
    #                    # 从 valid_apps 中删除对应项（用 name 和 path 匹配）
    #                    valid_apps[:] = [app for app in valid_apps if not (app["name"] == current_item["name"] and app["path"] == current_item["path"])]
    #                    with open(settings_path, "w", encoding="utf-8") as f:
    #                        json.dump(settings, f, indent=4)
    #                    self.del_dialog.accept()
    #            btn.clicked.connect(handle_del)
    #            layout.addWidget(btn)
    #    self.del_dialog.setLayout(layout)
    #    x = 350 * self.parent().scale_factor
    #    y = 100 * self.parent().scale_factor
    #    self.del_dialog.move(x, y)
    #    self.del_dialog.show()

    def show_custom_valid_apps_dialog(self):
        """显示自定义valid_apps添加界面"""
        self.add_dialog = QDialog(self)
        self.add_dialog.setWindowTitle("添加自定义游戏进程")
        self.add_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.add_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(46, 46, 46, 0.95);
                border-radius: {int(15 * self.parent().scale_factor)}px;
                border: {int(2 * self.parent().scale_factor)}px solid #444444;
            }}
        """)
        self.add_dialog.move(int(340 * self.parent().scale_factor), int(100 * self.parent().scale_factor))
        self.add_dialog.setFixedWidth(int(600 * self.parent().scale_factor))
        layout = QVBoxLayout(self.add_dialog)
        layout.setSpacing(int(10 * self.parent().scale_factor))
        layout.setContentsMargins(
            int(20 * self.parent().scale_factor),
            int(20 * self.parent().scale_factor),
            int(20 * self.parent().scale_factor),
            int(20 * self.parent().scale_factor)
        )

        # 名称输入（只读）
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("点击选择游戏名称")
        name_edit.setReadOnly(True)
        name_edit.setFixedHeight(int(50 * self.parent().scale_factor))
        name_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: {int(1 * self.parent().scale_factor)}px solid #666666;
                border-radius: {int(10 * self.parent().scale_factor)}px;
                padding: {int(10 * self.parent().scale_factor)}px;
                font-size: {int(20 * self.parent().scale_factor)}px;
            }}
            QLineEdit:hover {{
                background-color: #3f3f3f;
                color: white;
            }}
        """)
        layout.addWidget(name_edit)

        # 点击name_edit弹出选择窗口
        def show_game_name_selector():
            selector_dialog = QDialog(self.add_dialog)
            selector_dialog.setWindowTitle("选择游戏名称")
            selector_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
            selector_dialog.setStyleSheet(f"""
                QDialog {{
                    background-color: rgba(46, 46, 46, 0.98);
                    border-radius: {int(10 * self.parent().scale_factor)}px;
                    border: {int(2 * self.parent().scale_factor)}px solid #444444;
                }}
            """)
            vbox = QVBoxLayout(selector_dialog)
            vbox.setSpacing(int(10 * self.parent().scale_factor))
            vbox.setContentsMargins(
                int(20 * self.parent().scale_factor),
                int(20 * self.parent().scale_factor),
                int(20 * self.parent().scale_factor),
                int(20 * self.parent().scale_factor)
            )
            # 列出所有游戏名称
            for game in games:
                btn = QPushButton(game["name"])
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #444444;
                        color: white;
                        border-radius: {int(8 * self.parent().scale_factor)}px;
                        font-size: {int(16 * self.parent().scale_factor)}px;
                        padding: {int(10 * self.parent().scale_factor)}px;
                    }}
                    QPushButton:hover {{
                        background-color: #555555;
                    }}
                """)
                btn.clicked.connect(lambda checked, n=game["name"]: (name_edit.setText(n), selector_dialog.accept()))
                vbox.addWidget(btn)
            selector_dialog.setLayout(vbox)
            selector_dialog.exec_()
        name_edit.mousePressEvent = lambda event: show_game_name_selector()

        # 路径输入
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("路径（如 C:\\xxx\\xxx.exe）")
        self.path_edit.setFixedHeight(int(50 * self.parent().scale_factor))
        self.path_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: {int(1 * self.parent().scale_factor)}px solid #444444;
                border-radius: {int(10 * self.parent().scale_factor)}px;
                padding: {int(10 * self.parent().scale_factor)}px;
                font-size: {int(20 * self.parent().scale_factor)}px;
            }}
        """)
        layout.addWidget(self.path_edit)

        # 选择文件按钮
        select_file_btn = QPushButton("手动选择exe")
        select_file_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #5f5f5f;
                color: white;
                border: none;
                border-radius: {int(8 * self.parent().scale_factor)}px;
                padding: {int(8 * self.parent().scale_factor)}px {int(16 * self.parent().scale_factor)}px;
                font-size: {int(14 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #808080;
            }}
            QPushButton:pressed {{
                background-color: #333333;
            }}
        """)
        layout.addWidget(select_file_btn)

        # 新增：选择运行中进程按钮
        select_proc_btn = QPushButton("选择运行中进程")
        select_proc_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #5f5f5f;
                color: white;
                border: none;
                border-radius: {int(8 * self.parent().scale_factor)}px;
                padding: {int(8 * self.parent().scale_factor)}px {int(16 * self.parent().scale_factor)}px;
                font-size: {int(14 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #808080;
            }}
            QPushButton:pressed {{
                background-color: #333333;
            }}
        """)
        layout.addWidget(select_proc_btn)

        # 保存按钮
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #008CBA;
                color: white;
                border: none;
                border-radius: {int(8 * self.parent().scale_factor)}px;
                padding: {int(10 * self.parent().scale_factor)}px {int(20 * self.parent().scale_factor)}px;
                font-size: {int(16 * self.parent().scale_factor)}px;
            }}
            QPushButton:hover {{
                background-color: #007B9E;
            }}
            QPushButton:pressed {{
                background-color: #006F8A;
            }}
        """)
        layout.addWidget(save_btn)

        # 新增：如果set.json中已存在该游戏的自定义进程，显示删除按钮
        def has_custom_valid_app(game_name):
            return (
                "custom_valid_apps" in settings
                and any(item.get("name") == game_name for item in settings["custom_valid_apps"])
            )

        def remove_custom_valid_app():
            name = name_edit.text().strip()
            if not name:
                return
            # 删除settings中的自定义进程
            if "custom_valid_apps" in settings:
                settings["custom_valid_apps"] = [
                    item for item in settings["custom_valid_apps"] if item.get("name") != name
                ]
                # 同步删除valid_apps中的对应项
                global valid_apps
                valid_apps = [app for app in valid_apps if app.get("name") != name]
                load_apps()
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4)
            self.add_dialog.hide()
            # 可选：刷新主界面
            if self.parent() and hasattr(self.parent(), "deep_reload_games"):
                self.parent().deep_reload_games()

        # 判断是否需要显示删除按钮
        if has_custom_valid_app(name_edit.text()):
            del_btn = QPushButton("删除该游戏自定义进程")
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #ff4444;
                    color: white;
                    border-radius: {int(8 * self.parent().scale_factor)}px;
                    font-size: {int(16 * self.parent().scale_factor)}px;
                    padding: {int(10 * self.parent().scale_factor)}px {int(20 * self.parent().scale_factor)}px;
                }}
                QPushButton:hover {{
                    background-color: #ff6666;
                }}
            """)
            del_btn.clicked.connect(remove_custom_valid_app)
            layout.addWidget(del_btn)

        # 监听name_edit变化，动态显示/隐藏删除按钮
        def on_name_changed(text):
            # 先移除已有的删除按钮
            for i in reversed(range(layout.count())):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, QPushButton) and widget.text() == "删除该游戏自定义进程":
                    layout.removeWidget(widget)
                    widget.deleteLater()
            # 如果有自定义进程，添加删除按钮
            if has_custom_valid_app(text):
                del_btn = QPushButton("删除该游戏自定义进程")
                del_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #ff4444;
                        color: white;
                        border-radius: {int(8 * self.parent().scale_factor)}px;
                        font-size: {int(16 * self.parent().scale_factor)}px;
                        padding: {int(10 * self.parent().scale_factor)}px {int(20 * self.parent().scale_factor)}px;
                    }}
                    QPushButton:hover {{
                        background-color: #ff6666;
                    }}
                """)
                del_btn.clicked.connect(remove_custom_valid_app)
                layout.addWidget(del_btn)
        name_edit.textChanged.connect(on_name_changed)
        # 文件选择逻辑
        #def select_file():
        #    file_dialog = QFileDialog(dialog)
        #    file_dialog.setWindowTitle("选择可执行文件或快捷方式")
        #    file_dialog.setNameFilter("可执行文件 (*.exe *.lnk)")
        #    file_dialog.setFileMode(QFileDialog.ExistingFile)
        #    if file_dialog.exec_():
        #        selected_file = file_dialog.selectedFiles()[0]
        #        selected_file = selected_file.replace('/', '\\')
        #        path_edit.setText(selected_file)
        #    self.show()  
        #    dialog.show()
        select_file_btn.clicked.connect(self.select_file)
        # 选择运行中进程逻辑
        def select_running_process():
            proc_dialog = QDialog(self.add_dialog)
            proc_dialog.setWindowTitle("选择运行中进程")
            proc_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
            proc_dialog.setStyleSheet(f"""
                QDialog {{
                    background-color: rgba(46, 46, 46, 0.98);
                    border-radius: {int(10 * self.parent().scale_factor)}px;
                    border: {int(2 * self.parent().scale_factor)}px solid #444444;
                }}
            """)
            vbox = QVBoxLayout(proc_dialog)
            vbox.setSpacing(int(10 * self.parent().scale_factor))
            vbox.setContentsMargins(
                int(20 * self.parent().scale_factor),
                int(20 * self.parent().scale_factor),
                int(20 * self.parent().scale_factor),
                int(20 * self.parent().scale_factor)
            )

            # 枚举所有有前台窗口且不是隐藏的进程
            hwnd_pid_map = {}
            def enum_window_callback(hwnd, lParam):
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    hwnd_pid_map[pid] = hwnd
                return True
            win32gui.EnumWindows(enum_window_callback, None)

            # 收集进程信息
            proc_list = []
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if (
                        proc.info['pid'] in hwnd_pid_map
                        and proc.info['exe']
                        and proc.info['name'].lower() != "explorer.exe"
                        and proc.info['name'].lower() != "desktopgame.exe"   # 屏蔽自身
                    ):
                        proc_list.append(proc)
                except Exception:
                    continue
                
            if not proc_list:
                label = QLabel("没有检测到可用进程")
                label.setStyleSheet("color: white; font-size: 16px;")
                vbox.addWidget(label)
            else:
                for proc in proc_list:
                    proc_name = proc.info.get('name', '未知')
                    proc_exe = proc.info.get('exe', '')
                    btn = QPushButton(f"{proc_name} ({proc_exe})")
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #444444;
                            color: white;
                            border-radius: {int(8 * self.parent().scale_factor)}px;
                            font-size: {int(14 * self.parent().scale_factor)}px;
                            padding: {int(8 * self.parent().scale_factor)}px;
                            text-align: left;
                        }}
                        QPushButton:hover {{
                            background-color: #555555;
                        }}
                    """)
                    btn.clicked.connect(lambda checked, exe=proc_exe: self.path_edit.setText(exe) or proc_dialog.accept())
                    vbox.addWidget(btn)

            proc_dialog.setLayout(vbox)
            x = 350 * self.parent().scale_factor
            y = 100 * self.parent().scale_factor
            proc_dialog.move(x, y)
            proc_dialog.show()
        select_proc_btn.clicked.connect(select_running_process)
        # 保存逻辑
        def save_custom():
            name = name_edit.text().strip()
            path = self.path_edit.text().strip()
            if name and path:
                if "custom_valid_apps" not in settings:
                    settings["custom_valid_apps"] = []
                settings["custom_valid_apps"].append({"name": name, "path": path})
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4)
                valid_apps.append({"name": name, "path": path})
                name_edit.clear()
                self.path_edit.clear()
                self.add_dialog.hide()
        save_btn.clicked.connect(save_custom)
        self.add_dialog.setLayout(layout)
        x = 350 * self.parent().scale_factor
        y = 100 * self.parent().scale_factor
        self.add_dialog.move(x, y)
        self.add_dialog.show()

    def select_file(self):
        """选择可执行文件或快捷方式（非阻塞，适用于SettingsWindow）"""
        # 先隐藏所有相关弹窗
        if hasattr(self, 'add_dialog') and self.add_dialog.isVisible():
            self.add_dialog.hide()
        if hasattr(self, 'del_dialog') and self.del_dialog.isVisible():
            self.del_dialog.hide()
        self.hide()
        # 启动文件选择线程
        self.file_dialog_thread = FileDialogThread(self)
        self.file_dialog_thread.file_selected.connect(self.handle_file_selected)  # 连接信号到槽
        self.file_dialog_thread.start()  # 启动线程
    def handle_file_selected(self, selected_file):
        """处理选中的文件（适用于SettingsWindow）"""
        self.show()
        if hasattr(self, 'add_dialog') and self.add_dialog.isVisible() == False:
            self.add_dialog.show()
        # 填充路径
        self.path_edit.setText(selected_file.replace('/', '\\'))

    # 检查程序是否设置为开机自启
    def is_startup_enabled(self):
        command = ['schtasks', '/query', '/tn', "DesktopGameStartup"]
        try:
            # 如果任务存在，将返回0
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return self.set_startup_enabled(enable=False)
        except subprocess.CalledProcessError:
            return self.set_startup_enabled(enable=True)
    
    # 设置程序开机自启
    def set_startup_enabled(self,enable):
        if enable:
            app_path = sys.executable
            command = [
                'schtasks', '/create', '/tn', "DesktopGameStartup", '/tr', f'"{app_path}" startup',
                '/sc', 'onlogon', '/rl', 'highest', '/f'
            ]
            subprocess.run(command, check=True)
        else:
            try:
                command = ['schtasks', '/delete', '/tn', "DesktopGameStartup", '/f']
                subprocess.run(command, check=True)
            except FileNotFoundError:
                pass
            
    def toggle_killexplorer(self):
        """切换 killexplorer 状态并保存设置"""
        settings["killexplorer"] = not settings.get("killexplorer", False)
        self.killexplorer_button.setText(f"沉浸模式: {'√' if settings['killexplorer'] else '×'}")
        
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        self.parent().killexplorer = settings["killexplorer"]
        if self.parent().killexplorer == True:
            hide_desktop_icons()
            hide_taskbar()
            self.parent().winTaskbar.show()

    def toggle_freeze(self):
        """切换 freeze 状态并保存设置"""
        settings["freeze"] = not settings.get("freeze", False)
        self.freeze_button.setText(f"回主页时尝试冻结游戏 {'√' if settings['freeze'] else '×'}")
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        self.parent().freeze = settings["freeze"]

    def update_buttonsindexset(self, value):
        """更新主页游戏数量并保存设置"""
        self.parent().buttonsindexset = value
        self.buttonsindexset_label.setText(f"主页游戏数量: {value}")
        self.parent().reload_interface()

        # 保存 buttonsindexset 设置
        settings["buttonsindexset"] = value
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def update_row_count(self, value):
        """更新每行游戏数量并保存设置"""
        self.parent().row_count = value
        self.row_count_label.setText(f"每行游戏数量: {value}")
        self.parent().reload_interface()

        # 保存 row_count 设置
        settings["row_count"] = value
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)



    def restart_program(self):
        """重启程序"""
        QApplication.quit()
        # 只传递可执行文件的路径，不传递其他参数
        subprocess.Popen([sys.executable])

    def close_program(self):
        """完全关闭程序"""
        self.close_program_button.setText("正在退出程序...")
        self.close_program_button.setEnabled(False)  # 禁用按钮以防止重复点击
        # 如果开启了沉浸模式
        if self.parent().killexplorer and hasattr(self.parent(), 'winTaskbar'):
            self.parent().winTaskbar.on_back_to_desktop()
        # 退出程序
        QTimer.singleShot(500, QApplication.quit)


# 应用程序入口
if __name__ == "__main__":
    global STARTUP  # 声明 STARTUP 为全局变量
    # 获取程序所在目录
    z_order = []
    def enum_windows_callback(hwnd, lParam):
        z_order.append(hwnd)
        return True
    win32gui.EnumWindows(enum_windows_callback, None)
    
    # 打印当前工作目录
    print("当前工作目录:", os.getcwd())
    unique_args = list(dict.fromkeys(sys.argv))
    if len(unique_args) > 1 and unique_args[1] == "startup":
        STARTUP = True
    else:
        STARTUP = False
    # 避免重复运行
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        if proc.info['exe'] == sys.executable and proc.info['pid'] != current_pid:
            proc.terminate()
            proc.wait()
    app = QApplication(sys.argv)
    selector = GameSelector()
    selector.show()
    # 去除重复的路径

    sys.exit(app.exec_())