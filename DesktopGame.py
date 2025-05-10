import shutil
import sys
import json
import threading
import winreg
import pygame
import win32gui,win32process,psutil,win32api
from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu , QVBoxLayout, QDialog, QGridLayout, QWidget, QPushButton, QLabel, QDesktopWidget, QHBoxLayout, QFileDialog, QSlider, QLineEdit, QProgressBar, QScrollArea, QFrame
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtCore import QDateTime, Qt, QThread, pyqtSignal, QTimer, QPoint  
import subprocess, time, os,win32con, ctypes, re, win32com.client, ctypes, time, pyautogui
from ctypes import wintypes
#PyInstaller --add-data "fav.ico;." DesktopGame.py -i '.\fav.ico' --uac-admin --noconsole
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
# 读取 JSON 数据
json_path = f"{APP_INSTALL_PATH}\\config\\apps.json"
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)
    ###下面俩行代码用于QuickStreamAppAdd的伪排序清除，若感到困惑可删除###
    for idx, entry in enumerate(data["apps"]):
        entry["name"] = re.sub(r'^\d{2} ', '', entry["name"])  # 去掉开头的两位数字和空格

if ctypes.windll.shell32.IsUserAnAdmin()==0:
    ADMIN = False
elif ctypes.windll.shell32.IsUserAnAdmin()==1:
    ADMIN = True
# 筛选具有标签路径的条目
games = [
    app for app in data["apps"]
    if "output_image" in app.get("image-path", "") or "SGDB" in app.get("image-path", "") or "igdb" in app.get("image-path", "") or "steam/appcache/librarycache/" in app.get("image-path", "")
]
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

# 存储解析后的有效软件条目
valid_apps = []
def get_target_path(lnk_file):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(lnk_file)
    return shortcut.TargetPath
for app in data.get("apps", []):
    cmda = app.get("cmd")
    if cmda is None:
        continue  # 跳过无 cmd 的条目
    cmd = cmda.strip('"')
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
print(valid_apps)


# 焦点判断线程的标志变量
focus = True
focus_lock = threading.Lock()
# 游戏运行状态监听线程
class MonitorRunningAppsThread(QThread):
    play_reload_signal = pyqtSignal()  # 用于通知主线程重载
    play_app_name_signal = pyqtSignal(list)  # 用于传递 play_app_name 到主线程

    def __init__(self, play_lock, play_app_name, valid_apps):
        super().__init__()
        self.play_lock = play_lock
        self.play_app_name = play_app_name
        self.valid_apps = valid_apps
        self.running = True

    def check_running_apps(self):
        """检查当前运行的应用"""
        current_running_apps = set()

        # 获取当前运行的所有进程
        for process in psutil.process_iter(['pid', 'exe']):
            try:
                exe_path = process.info['exe']
                if exe_path:
                    # 检查进程路径是否在 valid_apps 中
                    for app in self.valid_apps:
                        if exe_path.lower() == app['path'].lower():
                            current_running_apps.add(app['name'])
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

class ConfirmDialog(QDialog):
    def __init__(self, variable1, scale_factor=1.0):
        super().__init__()
        self.variable1 = variable1
        self.scale_factor = scale_factor
        self.setWindowTitle("游戏确认")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(int(800 * self.scale_factor), int(400 * self.scale_factor))  # 更新后的固定尺寸
        self.setStyleSheet("""
            QDialog {
                background-color: #2E2E2E;
                border: 5px solid #4CAF50;
            }
            QLabel {
                font-size: 36px;
                color: #FFFFFF;
                margin-bottom: 40px;
                text-align: center;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 20px 0;
                font-size: 32px;
                margin: 0;
                width: 100%;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #388e3c;
            }
            QVBoxLayout {
                margin: 40px;
                spacing: 0;
            }
            QHBoxLayout {
                justify-content: center;
                spacing: 0;
            }
        """)

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
        self.accept()

    def cancel_action(self):
        print("用户点击了取消按钮")
        self.reject()
    
    def showEvent(self, event):
        """窗口显示时的事件处理"""
        super().showEvent(event)
        self.ignore_input_until = pygame.time.get_ticks() + 350  # 打开窗口后1秒内忽略输入

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
                        border: 1px solid yellow;
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
class MouseWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Create a label to display the text
        self.label = QLabel("↖(L3R3关闭鼠标映射)", self)
        self.label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 15px; color: white; border: 1px solid black; border-radius: 0px; background-color: rgba(0, 0, 0, 125);")
        self.label.adjustSize()
    
        # Get screen geometry and set the label position
        screen_geometry = QApplication.primaryScreen().geometry()
        label_width = self.label.width()
        label_height = self.label.height()
        self.label.move(screen_geometry.width() - label_width - 30, screen_geometry.height() - label_height - 30)

        # Set window properties
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.7)  # 设置窗口透明度为 50%
        self.setGeometry(screen_geometry)
        self.show()
class GameSelector(QWidget): 
    def __init__(self):
        global play_reload
        super().__init__()
        self.is_mouse_simulation_running = False
        self.ignore_input_until = 0  # 初始化防抖时间戳
        self.current_section = 0  # 0=游戏选择区域，1=控制按钮区域

        self.setWindowIcon(QIcon('fav.ico'))
        #if STARTUP:
        #    self.setWindowOpacity(0.0)  # 设置窗口透明度为全透明
        self.scale_factor = settings.get("scale_factor", 1.0)  # 从设置中读取缩放因数
        self.scale_factor2 = self.scale_factor * 2  # 用于按钮和图像的缩放因数
        self.more_section = 0  # 0=主页面，1=更多页面
        self.setWindowTitle("游戏选择器")
        QApplication.setFont(QFont("Microsoft YaHei"))  # 设置字体为微软雅黑
        # 获取屏幕的分辨率
        screen = QDesktopWidget().screenGeometry()
        # 设置窗口大小为屏幕分辨率
        self.resize(screen.width(), screen.height())
        self.setWindowFlags(Qt.FramelessWindowHint)  # 全屏无边框
        self.setStyleSheet("background-color: #1e1e1e;")  # 设置深灰背景色
        self.killexplorer = settings.get("killexplorer", False)
        self.freeze = settings.get("freeze", False)
        self.freezeapp = None
        if self.killexplorer == True and STARTUP == False:
            subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])
        self.showFullScreen()
        # 确保窗口捕获焦点
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.activateWindow()
        self.raise_()
        if STARTUP:
            hwnd = int(self.winId())
            ctypes.windll.user32.ShowWindow(hwnd, 0) # 0=SW_HIDE
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
        self.more_button = QPushButton("更多")
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
                border: {int(2 * self.scale_factor)}px solid #ffff88;
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
                border: {int(2 * self.scale_factor)}px solid #ffff88;
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
                border: {int(2 * self.scale_factor)}px solid #ffff88;
            }}
        """)
        self.quit_button.clicked.connect(self.hide_window)

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
                border: {int(2 * self.scale_factor)}px solid #ffff88;
            }}
        """)
        self.settings_button.clicked.connect(self.show_settings_window)

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
        self.in_floating_window = False
        # 添加游戏按钮
        self.buttons = []
        if sorted_games:  # 只在有游戏时添加按钮
            for index, game in enumerate(sorted_games[:self.buttonsindexset]):
                button = self.create_game_button(game, index)
                #self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)    #由self.buttonsindexset和sorted_games的长度决定是否要添加更多按钮（暂时不做
                self.grid_layout.addWidget(button, 0, index)
                self.buttons.append(button)
            
            # 添加“更多”按钮
            more_button = QPushButton("🟦🟦\n🟦🟦")
            more_button.setFont(QFont("Microsoft YaHei", 40))
            more_button.setFixedSize(int(140 * self.scale_factor2), int(140 * self.scale_factor2))
            more_button.clicked.connect(self.switch_to_all_software)  # 绑定“更多”按钮的功能
            self.grid_layout.addWidget(more_button, 0, len(sorted_games[:self.buttonsindexset]))  # 添加到最后一列
            self.buttons.append(more_button)

        else:
            # 添加一个提示按钮
            no_games_button = QPushButton("请点击-更多-按钮添加含有快捷方式的目录后\n使用-设置-刷新游戏-按钮添加主页面游戏")
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
        self.scroll_area.setAttribute(Qt.WA_AcceptTouchEvents)  # 滚动支持
        self.scroll_area.setContentsMargins(0, 0, 0, 0)  # 设置边距为0

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
        self.valid_apps = valid_apps  # 在这里填充 valid_apps
        self.monitor_thread = MonitorRunningAppsThread(self.play_lock, self.play_app_name, self.valid_apps)
        self.monitor_thread.play_app_name_signal.connect(self.update_play_app_name)  # 连接信号到槽
        self.monitor_thread.play_reload_signal.connect(self.handle_reload_signal)  # 连接信号到槽
        self.monitor_thread.start() 
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

        # 初始化时隐藏悬浮窗
        self.control_buttons = []
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
            if i == 0:
                btn.setText("🖱️")
                btn.clicked.connect(self.mouse_simulation)
            elif i == 1:
                btn.setText("🔇")
                btn.clicked.connect(self.toggle_mute)
            elif i == 2:
                btn.setText("🔉")
                btn.clicked.connect(self.decrease_volume)
            elif i == 3:
                btn.setText("🔊")
                btn.clicked.connect(self.increase_volume)
            elif i == 4:
                btn.setText("🔒")
                btn.clicked.connect(self.lock_system)
            elif i == 5:
                btn.setText("💤")
                btn.clicked.connect(self.sleep_system)
            elif i == 6:
                btn.setText("🔌")
                btn.clicked.connect(self.shutdown_system)
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
        # 连接手柄连接信号到槽函数
        self.controller_thread.controller_connected_signal.connect(self.update_controller_status)
        for controller_data in self.controller_thread.controllers.values():
            controller_name = controller_data['controller'].get_name()
            self.update_controller_status(controller_name)
        # 右侧文字
        right_label = QLabel("A / 进入游戏        B / 最小化        Y / 收藏        X / 更多            📦️DeskGamix v0.92")
        right_label.setStyleSheet(f"""
            QLabel {{
                font-family: "Microsoft YaHei"; 
                color: white;
                font-size: {int(25 * self.scale_factor)}px;
                padding-bottom: {int(10 * self.scale_factor)}px;
                padding-right: {int(50 * self.scale_factor)}px;
            }}
        """)
        texta_layout.addWidget(right_label, alignment=Qt.AlignRight)
        
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
        self.tray_icon.setIcon(QIcon("fav.ico"))  # 设置托盘图标为 fav.ico
        # 创建托盘菜单
        tray_menu = QMenu(self)
        restore_action = tray_menu.addAction("显示窗口")
        restore_action.triggered.connect(self.show_window)  # 点击显示窗口
        exit_action = tray_menu.addAction("退出")
        exit_action.triggered.connect(self.exitdef)  # 点击退出程序
        self.tray_icon.activated.connect(self.show_window) 
        self.tray_icon.setContextMenu(tray_menu)  # 设置托盘菜单
        self.tray_icon.show()  # 显示托盘图标

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
    def hide_window(self):
        """隐藏窗口"""
        hwnd = int(self.winId())
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0=SW_HIDE
    def switch_to_all_software(self):
        """切换到“所有软件”界面"""
        self.scale_factor2 = self.scale_factor  # 用于按钮和图像的缩放因数
        self.current_index = 0
        self.more_section = 1
        self.scroll_area.setFixedHeight(int(self.height()*0.89))  # 设置为90%高度
        self.toggle_control_buttons(False)  # 隐藏控制按钮
        self.reload_interface()
    def switch_to_main_interface(self):
        """切换到主界面"""
        self.scale_factor2 = self.scale_factor * 2  # 用于按钮和图像的缩放因数
        self.current_section = 0
        self.current_index = 0
        self.more_section = 0
        self.scroll_area.setFixedHeight(int(320 * self.scale_factor * 2.4))  # 设置为固定高度
        self.toggle_control_buttons(True)  # 显示控制按钮
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
    def is_virtual_keyboard_open(self):
        """检查是否已经打开虚拟键盘"""
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name'] and process.info['name'].lower() == 'osk.exe':
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False
    def close_virtual_keyboard(self):
        """关闭虚拟键盘"""
        for process in psutil.process_iter(['name']):
            try:
                if process.info['name'] and process.info['name'].lower() == 'osk.exe':
                    process.terminate()  # 终止虚拟键盘进程
                    process.wait()  # 等待进程完全关闭
                    print("虚拟键盘已关闭")
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    def mouse_simulation(self):
        """开启鼠标映射"""
        # 检查是否已经在运行
        if self.is_mouse_simulation_running:
            print("鼠标映射已在运行，忽略重复调用")
            return

        # 设置标志为 True，表示正在运行
        self.is_mouse_simulation_running = True

        pygame.init()
        pygame.joystick.init()
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
        self.hide_window()
        print("鼠标映射")
        axes = joystick.get_numaxes()
        # 一般DualShock4轴数为6，XBox为5
        if axes >= 6:
            rt_axis = 5   # DualShock4右扳机在轴5
        else:
            rt_axis = 2   # Xbox手柄右扳机通常映射在轴2

        # 根据手柄类型设置左扳机轴号
        if axes >= 6:
            lt_axis = 4   # DualShock4左扳机在轴4
        else:
            lt_axis = 2   # Xbox手柄左扳机通常映射在轴2
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
        window = MouseWindow()
        last_mouse_x, last_mouse_y = -1, -1  # 初始化上一次鼠标位置

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
        try:
            while running:
                # 动态检测新手柄加入或移除
                for event in pygame.event.get():
                    if event.type == pygame.JOYDEVICEADDED:
                        joystick = pygame.joystick.Joystick(event.device_index)
                        joystick.init()
                        joysticks.append(joystick)
                        joystick_states[joystick.get_instance_id()] = {"scrolling_up": False, "scrolling_down": False}
                        print(f"手柄已连接: {joystick.get_name()}")
    
                    elif event.type == pygame.JOYDEVICEREMOVED:
                        for joystick in joysticks:
                            if joystick.get_instance_id() == event.instance_id:
                                print(f"手柄已断开: {joystick.get_name()}")
                                joysticks.remove(joystick)
                                del joystick_states[event.instance_id]
                                break
                pygame.event.pump()
                #self.setCursor(Qt.ArrowCursor)  # 设置鼠标光标为箭头形状
                #ctypes.windll.user32.SetSystemCursor(
                #    ctypes.windll.user32.LoadCursorW(0, win32con.IDC_HAND),
                #    win32con.OCR_NORMAL
                #)
                mouse_x, mouse_y = pyautogui.position()
                # 仅当鼠标位置发生变化时更新窗口位置
                if (mouse_x, mouse_y) != (last_mouse_x, last_mouse_y):
                    # 更新窗口位置
                    window.label.move(mouse_x, mouse_y)
                    #window.label.setText("↖")
                    last_mouse_x, last_mouse_y = mouse_x, mouse_y
                # 遍历所有手柄，处理输入
                joycount = pygame.joystick.get_count()
                for joystick in joysticks:
                    #pygame.mouse.set_visible(True)  # 显示鼠标光标
                    mapping = ControllerMapping(joystick) #切换对应的手柄映射
                    #ctypes.windll.user32.ShowCursor(True)  # 显示鼠标光标
                    # GUIDE 按钮退出
                    if joystick.get_button(mapping.guide) or joystick.get_button(mapping.right_stick_in) or joystick.get_button(mapping.left_stick_in):
                        running = False  # 设置状态标志为 False，退出循环
                        # 设置右下角坐标
                        print("退出鼠标映射")
                        if self.is_virtual_keyboard_open():
                            self.close_virtual_keyboard()
                        right_bottom_x = screen_width - 1  # 最右边
                        right_bottom_y = screen_height - 1  # 最底部
                        # 移动鼠标到屏幕右下角
                        pyautogui.moveTo(right_bottom_x, right_bottom_y)
                        #time.sleep(0.5)  
                        break
                    
                    if joystick.get_button(mapping.start):  # START键打开键盘

                        if self.is_virtual_keyboard_open():
                            self.close_virtual_keyboard()
                        else:
                            pyautogui.moveTo(int(screen_width/2), int(screen_height/1.5))  # 移动鼠标到屏幕中心
                            self.open_virtual_keyboard()
                        time.sleep(0.5)  # 延迟0.2秒，避免重复触发
                    if joystick.get_button(mapping.back):  # SELECT键模拟win+tab
                        pyautogui.hotkey('win', 'tab')
                        time.sleep(0.5)  # 延迟0.2秒，避免重复触发

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
                    # 检查是否使用 hat 输入
                    if mapping.has_hat:
                        hat_value = joystick.get_hat(0)  # 获取第一个 hat 的值
                        if hat_value == (-1, 0):  # 左
                            # 音量减
                            self.decrease_volume()
                            time.sleep(0.2)  # 延迟0.2秒，避免重复触发
                        elif hat_value == (1, 0):  # 右
                            # 音量加
                            self.increase_volume()
                            time.sleep(0.2)  # 延迟0.2秒，避免重复触发
                        elif joystick.get_button(mapping.button_x) or hat_value == (0, -1):  # 下
                            scrolling_down = True
                        elif joystick.get_button(mapping.button_y) or hat_value == (0, 1):  # 上
                            scrolling_up = True
                        else:
                            scrolling_down = False
                            scrolling_up = False
                    else:
                        # 如果不使用 hat，则检查按钮输入
                        if joystick.get_button(mapping.dpad_left):
                            # 音量减
                            self.decrease_volume()
                            time.sleep(0.2)  # 延迟0.2秒，避免重复触发
                        elif joystick.get_button(mapping.dpad_right):
                            # 音量加
                            self.increase_volume()
                            time.sleep(0.2)  # 延迟0.2秒，避免重复触发

                        # 检查滚动状态
                        if joystick.get_button(mapping.button_x) or joystick.get_button(mapping.dpad_down):  # X键或D-pad下
                            scrolling_down = True
                        else:
                            scrolling_down = False

                        if joystick.get_button(mapping.button_y) or joystick.get_button(mapping.dpad_up):  # Y键或D-pad上
                            scrolling_up = True
                        else:
                            scrolling_up = False

                    # 读取左摇杆轴值（0: X 轴，1: Y 轴）
                    x_axis = joystick.get_axis(0)
                    y_axis = joystick.get_axis(1)
                    # 读取右扳机轴值，实现灵敏度切换
                    rt_val = joystick.get_axis(rt_axis)
                    # 读取左扳机轴值
                    lt_val = joystick.get_axis(lt_axis)

                    # 读取右摇杆轴值（2: X 轴，3: Y 轴）
                    rx_axis = joystick.get_axis(2)  # 右摇杆 X 轴
                    ry_axis = joystick.get_axis(3)  # 右摇杆 Y 轴

                    # 根据左扳机值切换灵敏度（优先级高于右扳机）
                    if lt_val > 0.8:  # 如果左扳机值大于 0.8，设置为高灵敏度
                        sensitivity = SENS_HIGH
                    elif rt_val > 0.5:  # 如果右扳机值大于 0.5，设置为低灵敏度
                        sensitivity = SENS_LOW
                        sensitivity1 = SENS_HIGH
                    #elif rt_val > 0.5 and lt_val > 0.8:  # 如果两个扳机都按下(这样按有病吧？)
                    #    sensitivity = SENS_HIGH
                    #    sensitivity1 = SENS_HIGH
                    else:  # 默认设置
                        sensitivity = SENS_MEDIUM
                        sensitivity1 = SENS_LOW

                    # 使用右摇杆控制鼠标移动（低灵敏度）
                    dx = dy = 0
                    if abs(rx_axis) > DEADZONE:
                        dx = rx_axis * sensitivity1
                    if abs(ry_axis) > DEADZONE:
                        dy = ry_axis * sensitivity1
                    # PyAutoGUI中 y 轴正值向下移动，与摇杆上推为负值刚好对应
                    pyautogui.moveRel(dx, dy)

                    # 根据摇杆值控制鼠标移动，加入死区处理
                    dx = dy = 0
                    if abs(x_axis) > DEADZONE:
                        dx = x_axis * sensitivity
                    if abs(y_axis) > DEADZONE:
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

    def open_virtual_keyboard(self):
        """开启系统虚拟键盘"""
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "open", "osk.exe", None, None, 1)
        except FileNotFoundError:
            print("无法找到虚拟键盘程序")
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
    def lock_system(self):
        ctypes.windll.user32.LockWorkStation()

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
        pixmap = QPixmap(game["image-path"]).scaled(int(200 * self.scale_factor2), int(267 * self.scale_factor2), Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
        button.clicked.connect(lambda checked, idx=index: self.launch_game(idx))
        
        # 创建星标（如果已收藏）
        if game["name"] in settings["favorites"]:
            star_label = QLabel("⭐", button)  # 将星标作为按钮的子控件
            star_label.setStyleSheet(f"""
                QLabel {{
                    color: yellow;
                    font-size: {int(20 * self.scale_factor2)}px;
                    padding: {int(5 * self.scale_factor2)}px;
                    background-color: rgba(46, 46, 46, 0.7);
                    border-radius: {int(5 * self.scale_factor2)}px;
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
        if self.player:
            self.setWindowOpacity(0.95)
        else:
            self.setWindowOpacity(1)
        # 更新游戏名称标签
        if self.current_section == 0:  # 游戏选择区域
            if self.more_section == 0 and self.current_index == self.buttonsindexset:  # 如果是“更多”按钮
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
                            border: {int(2 * self.scale_factor)}px solid #ffff88;
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
                            border: {int(2 * self.scale_factor)}px solid #ffff88;
                        }}
                    """)

        if self.current_section == 0: 
            for index, button in enumerate(self.buttons):
                if index == self.current_index:
                    button.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #2e2e2e; 
                            border-radius: {int(10 * self.scale_factor2)}px; 
                            border: {int(3 * self.scale_factor2)}px solid yellow;
                        }}
                        QPushButton:hover {{
                            border: {int(3 * self.scale_factor2)}px solid #ffff88;
                        }}
                    """)
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
        elif self.current_section == 1:  # 控制按钮区域
            for index, btn in enumerate(self.control_buttons):
                if index == self.current_index:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #3e3e3e;
                            border-radius: 62%;
                            font-size: {int(40 * self.scale_factor)}px; 
                            border: {int(4 * self.scale_factor)}px solid yellow;
                        }}
                        QPushButton:hover {{
                            border: {int(4 * self.scale_factor)}px solid #00ff00;
                        }}
                    """)
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
        #if self.buttons:
        #    current_button = self.buttons[self.current_index]
        #    button_pos = current_button.mapTo(self.scroll_widget, current_button.pos())
        #    scroll_area_height = self.scroll_area.viewport().height()
        #    if button_pos.y() < self.scroll_area.verticalScrollBar().value():
        #        self.scroll_area.verticalScrollBar().setValue(button_pos.y())
        #    elif button_pos.y() + current_button.height() > self.scroll_area.verticalScrollBar().value() + scroll_area_height:
        #        self.scroll_area.verticalScrollBar().setValue(button_pos.y() + current_button.height() - scroll_area_height)
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
        if self.buttons and self.current_section == 0:
            current_button = self.buttons[self.current_index]
            scroll_area_width = self.scroll_area.viewport().width()
            button_pos = current_button.mapToGlobal(QPoint(0, 0))  # 获取按钮在屏幕中的绝对位置
            scroll_area_pos = self.scroll_area.mapToGlobal(QPoint(0, 0))  # 获取滚动区域在屏幕中的绝对位置
            button_width = current_button.width()
            
            if self.current_index == 0:
                # 第一个按钮，滚动到最左边
                self.scroll_area.horizontalScrollBar().setValue(0)
            elif self.current_index >= 1:
                # 使用QPoint实现精确定位并改进调整滚动的方式
                button_pos = QPoint(current_button.mapToGlobal(QPoint(0, 0)))  # 获取当前按钮的精确位置
                scroll_value = self.scroll_area.horizontalScrollBar().value()  # 获取当前滚动值
                # 当靠近左边缘且移动距离大于3时调整滚动
                if button_pos.x() < scroll_area_pos.x():
                    second_button_pos = self.buttons[0].mapToGlobal(QPoint(0, 0)).x()
                    scroll_value = button_pos.x() - second_button_pos
                    self.scroll_area.horizontalScrollBar().setValue(scroll_value)
                
                # 当靠近右边缘且移动距离大于3时调整滚动
                elif button_pos.x() + button_width > scroll_area_pos.x() + scroll_area_width:
                    second_button_pos = self.buttons[min(3, len(self.buttons) - 1)].mapToGlobal(QPoint(0, 0)).x()
                    scroll_value = button_pos.x() - second_button_pos
                    self.scroll_area.horizontalScrollBar().setValue(scroll_value)
                    print(button_pos.x())
                    asdffasf=button_pos.x()
        #
        #self.game_name_label.move(button_pos.x(), button_pos.y() - self.game_name_label.height())
        #self.game_name_label.show()
        # 新增文本显示，复制game_name_label的内容
        if self.current_section == 0: 
            button_pos = current_button.mapToGlobal(QPoint(0, 0))  # 重新加载按钮的最新位置
            if hasattr(self, 'additional_game_name_label') and isinstance(self.additional_game_name_label, QLabel):
                try:
                    self.additional_game_name_label.deleteLater()  # 删除之前生成的 additional_game_name_label
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
                }}
            """)
        # background-color: #575757;    
        # border-radius: 10px;          
        # border: 2px solid #282828;
            self.additional_game_name_label.adjustSize()  # 调整标签大小以适应文本
            print(self.game_name_label.text(), button_pos.x(), button_pos.x() + (button_width - self.additional_game_name_label.width()) // 2, button_pos.y() - self.game_name_label.height() - 20)
            self.additional_game_name_label.move(button_pos.x() + (button_width - self.additional_game_name_label.width()) // 2, button_pos.y() - self.game_name_label.height() - 20)  # 居中在按钮中央
            self.additional_game_name_label.show()
        else:
            if hasattr(self, 'additional_game_name_label') and isinstance(self.additional_game_name_label, QLabel):
                try:
                    self.additional_game_name_label.deleteLater()  # 删除之前生成的 additional_game_name_label
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
    def keyPressEvent(self, event):
        """处理键盘事件"""
        if getattrs:
            with focus_lock:  #焦点检查-只有打包后才能使用
                if not focus: 
                    return
        if self.in_floating_window and self.floating_window:
            # 添加防抖检查
            if not self.floating_window.can_process_input():
                return
            
            if event.key() == Qt.Key_Up:
                self.floating_window.current_index = max(0, self.floating_window.current_index - 1)
                self.floating_window.update_highlight()
            elif event.key() == Qt.Key_Down:
                self.floating_window.current_index = min(
                    len(self.floating_window.buttons) - 1,
                    self.floating_window.current_index + 1
                )
                self.floating_window.update_highlight()
            elif event.key() == Qt.Key_Return:
                self.execute_more_item()
            elif event.key() == Qt.Key_Escape:
                self.floating_window.hide()
                self.in_floating_window = False
            return
            
        current_time = pygame.time.get_ticks()  # 获取当前时间（毫秒）
        # 如果在忽略输入的时间段内，则不处理
        if current_time < self.ignore_input_until:
            return
        # 如果按键间隔太短，则不处理
        if current_time - self.last_input_time < self.input_delay:
            return

        # 新增焦点切换逻辑
        if event.key() == Qt.Key_Down and self.current_section == 0 and self.more_section == 0:
            self.current_section = 1  # 切换到控制按钮区域
            if self.current_index < 3:
                self.current_index = int(self.current_index * 2)
            else:
                self.current_index = 6
            self.update_highlight()
            print("当前区域：控制按钮区域")
        elif event.key() == Qt.Key_Up and self.current_section == 1 and self.more_section == 0:
            self.current_section = 0  # 返回游戏选择区域
            self.current_index = int(self.current_index/2)
            self.update_highlight()
            print("当前区域：游戏选择区域")
        elif event.key() == Qt.Key_Escape and self.more_section == 1:
            self.switch_to_main_interface()
        else:
            # 修改后的导航逻辑
            if self.current_section == 0:  # 游戏选择区域
                if event.key() == Qt.Key_Up:
                    self.move_selection(-self.row_count)  # 向上移动
                elif event.key() == Qt.Key_Down:
                    self.move_selection(self.row_count)  # 向下移动
                elif event.key() == Qt.Key_Left:
                    self.move_selection(-1)  # 向左移动
                elif event.key() == Qt.Key_Right:
                    self.move_selection(1)  # 向右移动
                elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    self.launch_game(self.current_index)  # 启动游戏
                elif event.key() == Qt.Key_Escape:
                    #self.exitdef()  # 退出程序
                    self.hide_window()
            else:  # 控制按钮区域
                if event.key() == Qt.Key_Left:
                    self.current_index = max(0, self.current_index - 1)
                elif event.key() == Qt.Key_Right:
                    self.current_index = min(len(self.control_buttons)-1, self.current_index + 1)
                elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    self.control_buttons[self.current_index].click()
                
                self.update_highlight()

        # 更新最后一次按键时间
        self.last_input_time = current_time
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
    # 焦点检测线程
    def focus_thread():
        global focus
        while True:
            # 获取当前活动窗口句柄
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                print("未找到活动窗口")
                #return False  # 未找到活动窗口
                focus = False
            else:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(pid)
                exe_path = process.exe()
                exe_name = os.path.basename(exe_path)
                with focus_lock:
                    if exe_name == "DesktopGame.exe":
                        focus = True
                        print("焦点在游戏窗口")
                    else:
                        focus = False
                        print("焦点不在游戏窗口")
            time.sleep(0.1)  # 稍微休眠，避免线程占用过多 CPU
    
    # 启动焦点判断线程
    thread = threading.Thread(target=focus_thread, daemon=True)
    thread.start()   

    def launch_game(self, index):
        """启动选中的游戏"""
        sorted_games = self.sort_games()
        game = sorted_games[index]
        game_cmd = game["cmd"]
        game_name = game["name"]
        image_path = game.get("image-path", "")
        self.ignore_input_until = pygame.time.get_ticks() + 600

        if self.more_section == 0 and self.current_index == self.buttonsindexset: # 如果点击的是“更多”按钮
            self.switch_to_all_software()
            return
        #冻结相关
        if self.freezeapp:
            os.system(f'pssuspend64.exe -r {self.freezeapp}')
            self.freezeapp = None
        if game["name"] in self.player:
            for app in valid_apps:
                if app["name"] == game["name"]:
                    game_path = app["path"]
                    break
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
            return
        if self.player:
            # 创建确认弹窗
            self.confirm_dialog = ConfirmDialog("已经打开了一个游戏，还要再打开一个吗？")
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  # 设置屏蔽时间为800毫秒
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            else:
                pass
        self.controller_thread.show_launch_window(game_name, image_path)
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
        if game_cmd:
            #self.showMinimized()
            subprocess.Popen(game_cmd, shell=True)
            #self.showFullScreen()
            self.ignore_input_until = pygame.time.get_ticks() + 1000
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
                if self.freeze and self.freezeapp == None:
                    if os.path.exists("pssuspend64.exe"):
                        pass_exe=['ZFGameBrowser.exe', 'amdow.exe', 'audiodg.exe', 'cmd.exe', 'cncmd.exe', 'copyq.exe', 'frpc.exe', 'gamingservicesnet.exe', 'memreduct.exe', 'mmcrashpad_handler64.exe','GameBarPresenceWriter.exe', 'HipsTray.exe', 'HsFreezer.exe', 'HsFreezerMagiaMove.exe', 'PhoneExperienceHost.exe','PixPin.exe', 'PresentMon-x64.exe','msedgewebview2.exe', 'plugin_host-3.3.exe', 'plugin_host-3.8.exe','explorer.exe','System Idle Process', 'System', 'svchost.exe', 'Registry', 'smss.exe', 'csrss.exe', 'wininit.exe', 'winlogon.exe', 'services.exe', 'lsass.exe', 'atiesrxx.exe', 'amdfendrsr.exe', 'atieclxx.exe', 'MemCompression', 'ZhuDongFangYu.exe', 'wsctrlsvc.exe', 'AggregatorHost.exe', 'wlanext.exe', 'conhost.exe', 'spoolsv.exe', 'reWASDService.exe', 'AppleMobileDeviceService.exe', 'ABService.exe', 'mDNSResponder.exe', 'Everything.exe', 'SunloginClient.exe', 'RtkAudUService64.exe', 'gamingservices.exe', 'SearchIndexer.exe', 'MoUsoCoreWorker.exe', 'SecurityHealthService.exe', 'HsFreezerEx.exe', 'GameInputSvc.exe', 'TrafficProt.exe', 'HipsDaemon.exe','python.exe', 'pythonw.exe', 'qmbrowser.exe', 'reWASDEngine.exe', 'sihost.exe', 'sublime_text.exe', 'taskhostw.exe', 'SearchProtocolHost.exe','crash_handler.exe', 'crashpad_handler.exe', 'ctfmon.exe', 'dasHost.exe', 'dllhost.exe', 'dwm.exe', 'fontdrvhost.exe','RuntimeBroker.exe','taskhostw.exe''WeChatAppEx.exe', 'WeChatOCR.exe', 'WeChatPlayer.exe', 'WeChatUtility.exe', 'WidgetService.exe', 'Widgets.exe', 'WmiPrvSE.exe', 'Xmp.exe','QQScreenshot.exe', 'RadeonSoftware.exe', 'SakuraFrpService.exe', 'SakuraLauncher.exe', 'SearchHost.exe', 'SecurityHealthSystray.exe', 'ShellExperienceHost.exe', 'StartMenuExperienceHost.exe', 'SystemSettings.exe', 'SystemSettingsBroker.exe', 'TextInputHost.exe', 'TrafficMonitor.exe', 'UserOOBEBroker.exe','WeChatAppEx.exe','360zipUpdate.exe', 'AMDRSServ.exe', 'AMDRSSrcExt.exe', 'APlayer.exe', 'ApplicationFrameHost.exe', 'CPUMetricsServer.exe', 'ChsIME.exe', 'DownloadSDKServer.exe','QMWeiyun.exe'];save_input=[]
                        if exe_name in pass_exe:
                            print(f"当前窗口 {exe_name} 在冻结列表中，跳过冻结")
                            return True
                        os.system(f'pssuspend64.exe {exe_name}')
                        self.freezeapp = exe_name
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
        # 跟踪焦点状态
        current_time = pygame.time.get_ticks()
        # 如果在屏蔽输入的时间段内，则不处理
        if current_time < self.ignore_input_until:
            return
        
        if current_time - self.last_input_time < self.input_delay:
            return
        if getattrs:
            with focus_lock:  #焦点检查-只有打包后才能使用
                if not focus: 
                    if action == 'GUIDE':
                        if ADMIN:
                            try:
                                # 将所有界面标记归零（没必要似乎
                                #self.current_index = 0
                                #self.current_section = 0
                                #self.more_section = 0
                                if current_time < ((self.ignore_input_until)+2000):
                                    return
                                self.ignore_input_until = pygame.time.get_ticks() + 500 
                                if STARTUP:
                                    if self.killexplorer == True:
                                        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])
                                        STARTUP = False

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
                                    time.sleep(0.2)
                                # 移动鼠标到屏幕右下角并进行右键点击
                                    pyautogui.rightClick(right_bottom_x, right_bottom_y)
                                    # 恢复原来的 Z 顺序
                                    #for hwnd in reversed(z_order):
                                    SetWindowPos(hwnd, -2, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                            except Exception as e:
                                print(f"Error: {e}")
                        else:
                            self.showFullScreen()
                            self.last_input_time = current_time
                    return
        if self.is_mouse_simulation_running == True:
            return
        if self.in_floating_window and self.floating_window:
            # 添加防抖检查
            if not self.floating_window.can_process_input():
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
                if self.can_toggle_window():
                    self.floating_window.hide()
                    self.in_floating_window = False
            elif action == 'Y':
                self.floating_window.toggle_favorite()
            self.last_input_time = current_time
            return
        
        if hasattr(self, 'confirm_dialog') and self.confirm_dialog.isVisible():  # 如果确认弹窗显示中
            print("确认弹窗显示中")
            self.confirm_dialog.handle_gamepad_input(action)
            return

        # 新增焦点切换逻辑
        if action == 'DOWN' and self.current_section == 0 and self.more_section == 0:
            self.current_section = 1  # 切换到控制按钮区域
            if self.current_index < 3:
                self.current_index = int(self.current_index * 2)
            else:
                self.current_index = 6
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
                    if not self.in_floating_window and self.can_toggle_window():
                        #self.exitdef()  # 退出程序
                        self.hide_window()
                        
                self.update_highlight()
            else:
                if action == 'UP' and self.more_section == 1:
                    self.move_selection(-self.row_count)  # 向上移动
                elif action == 'DOWN' and self.more_section == 1:
                    self.move_selection(self.row_count)  # 向下移动
                elif action == 'LEFT':
                    if self.current_index == 0:  # 如果当前是第一项，保持不变
                        return
                    self.move_selection(-1)  # 向左移动
                elif action == 'RIGHT':
                    if self.current_index < len(self.buttons) - 1:  # 检查是否已经是最后一个按钮
                        self.move_selection(1)  # 向右移动
                elif action == 'A':
                    self.launch_game(self.current_index)  # 启动游戏
                elif action == 'B':
                    if not self.in_floating_window and self.can_toggle_window():
                        #self.exitdef()  # 退出程序
                        self.hide_window()
                elif action == 'Y':
                    self.toggle_favorite()  # 收藏/取消收藏游戏
                elif action == 'X':  # X键开悬浮窗
                    self.show_more_window()  # 打开悬浮窗

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
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        if hasattr(self, 'controller_thread'):
            self.controller_thread.stop()
            self.controller_thread.wait()
        
        if self.killexplorer == True:
            subprocess.run(["start", "explorer.exe"], shell=True)
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
            self.confirm_dialog = ConfirmDialog(f"是否关闭下列程序？\n{game_name}")
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  # 设置屏蔽时间为800毫秒
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
                        proc.terminate()  # 结束进程
                        proc.wait()  # 等待进程完全终止
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
    
    def reload_interface(self):
        """重新加载界面"""
        # 清除现有按钮
        #if self.butto:
        #    return
        #self.butto=True
        for button in self.buttons:
            button.setParent(None)
        self.buttons.clear()
        
        # 重新添加按钮
        sorted_games = self.sort_games()
        if sorted_games:  # 只在有游戏时添加按钮
            if self.more_section == 0:
                for index, game in enumerate(sorted_games[:self.buttonsindexset]):
                    button = self.create_game_button(game, index)
                    #self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)
                    self.grid_layout.addWidget(button, 0, index)
                    self.buttons.append(button)

                # 添加“更多”按钮
                more_button = QPushButton("🟦🟦\n🟦🟦")
                more_button.setFont(QFont("Microsoft YaHei", 40))
                more_button.setFixedSize(int(140 * self.scale_factor2), int(140 * self.scale_factor2))
                more_button.clicked.connect(self.switch_to_all_software)  # 绑定“更多”按钮的功能
                self.grid_layout.addWidget(more_button, 0, len(sorted_games[:self.buttonsindexset]))  # 添加到最后一列
                self.buttons.append(more_button)
            else:
                for index, game in enumerate(sorted_games):
                    button = self.create_game_button(game, index)
                    self.grid_layout.addWidget(button, index // self.row_count, index % self.row_count)
                    self.buttons.append(button)

        # 将代码放入一个函数中
        def delayed_execution():
            self.update_highlight()
        
        # 使用 QTimer 延迟 50 毫秒后执行
        QTimer.singleShot(25, delayed_execution)
        #self.butto=False

    def show_more_window(self):
        """显示更多选项窗口"""
        if not self.can_toggle_window():
            return
            
        if not self.floating_window:
            self.floating_window = FloatingWindow(self)
            
        # 计算悬浮窗位置
        button_pos = self.more_button.mapToGlobal(self.more_button.rect().bottomLeft())
        self.floating_window.move(button_pos.x(), button_pos.y() + 10)
        
        self.floating_window.show()
        self.in_floating_window = True
        self.floating_window.update_highlight()

    def execute_more_item(self, file=None):
        """执行更多选项中的项目"""
        if not self.floating_window:
            return
    
        sorted_files = self.floating_window.sort_files()  # 提前定义 sorted_files
    
        if file:
            current_file = file
        else:
            current_file = sorted_files[self.floating_window.current_index]
    
        current_file["path"] = os.path.abspath(os.path.join("./morefloder/", current_file["path"]))
    
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
        subprocess.Popen(current_file["path"], shell=True)
        self.floating_window.update_highlight()
        self.floating_window.hide()
        self.in_floating_window = False

    def can_toggle_window(self):
        """检查是否可以切换悬浮窗状态"""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_window_toggle_time < self.window_toggle_delay:
            return False
        self.last_window_toggle_time = current_time
        return True

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

    def refresh_games(self):
        """刷新游戏列表，处理 extra_paths 中的快捷方式"""
        subprocess.Popen("QuickStreamAppAdd.exe", shell=True)
        self.confirm_dialog = ConfirmDialog("是否要重启程序以应用更改？")
        result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
        self.ignore_input_until = pygame.time.get_ticks() + 350  # 设置屏蔽时间为800毫秒
        if not result == QDialog.Accepted:  
            return
        else:
            self.restart_program()
        return

    def update_controller_status(self, controller_name):
        """更新左侧标签显示的手柄名称"""
        if hasattr(self, 'left_label') and isinstance(self.left_label, QLabel):
            self.left_label.setText(f"🎮️ {controller_name}")
        else:
            print("left_label 未正确初始化")

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
        
        # 预创建 launch_overlay
        self.create_launch_overlay()

    def create_launch_overlay(self):
        """预创建启动游戏的悬浮窗"""
        self.parent.launch_overlay = QWidget(self.parent)
        self.parent.launch_overlay.setObjectName("launchOverlay")
        self.parent.launch_overlay.setStyleSheet("""
            QWidget#launchOverlay {
                background-color: rgba(46, 46, 46, 0.9);
            }
            QLabel {
                font-size: 36px;
                color: #FFFFFF;
                margin-bottom: 40px;
                text-align: center;
                background: transparent;  /* 设置文字背景透明 */
            }
        """)

        # 设置悬浮窗大小为父窗口大小
        self.parent.launch_overlay.setFixedSize(self.parent.size())

        # 创建垂直布局
        self.overlay_layout = QVBoxLayout(self.parent.launch_overlay)
        self.overlay_layout.setAlignment(Qt.AlignCenter)

        # 创建图片标签和文本标签
        self.overlay_image = QLabel()
        self.overlay_image.setAlignment(Qt.AlignCenter)
        self.overlay_layout.addWidget(self.overlay_image)

        self.overlay_text = QLabel()
        self.overlay_text.setAlignment(Qt.AlignCenter)
        self.overlay_layout.addWidget(self.overlay_text)

        # 初始时隐藏
        self.parent.launch_overlay.hide()

    def show_launch_window(self, game_name, image_path):
        """显示启动游戏的悬浮窗"""

        # 将悬浮窗置于最上层并显示
        self.parent.launch_overlay.raise_()
        self.parent.launch_overlay.show()

        # 更新图片
        if image_path:
            pixmap = QPixmap(image_path).scaled(
                int(400 * self.parent.scale_factor),
                int(533 * self.parent.scale_factor),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.overlay_image.setPixmap(pixmap)
            self.overlay_image.show()
        else:
            self.overlay_image.hide()

        # 更新文本
        self.overlay_text.setText(f"正在启动 {game_name}")

        # 将悬浮窗置于最上层并显示函数
        self.selection_count = 0  # 初始化计数器
    
        def select_code():
            if self.selection_count < 39:
                self.parent.launch_overlay.raise_()
                self.selection_count += 1
            else:
                timer.stop()  # 停止计时器
    
        timer = QTimer(self)
        timer.timeout.connect(select_code)
        timer.start(150)  
        QTimer.singleShot(6000, self.parent.launch_overlay.hide)
        
    def stop(self):
        """停止线程"""
        self._running = False
        
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
                            print(f"Controller {controller.get_instance_id()} connected: {controller.get_name()}")
                            self.controller_connected_signal.emit(controller.get_name())
                        except pygame.error as e:
                            print(f"Failed to initialize controller {event.device_index}: {e}")
                
                    elif event.type == pygame.JOYDEVICEREMOVED:
                        if event.instance_id in self.controllers:
                            print(f"Controller {event.instance_id} disconnected")
                            del self.controllers[event.instance_id]

                # 处理所有已连接手柄的输入
                for controller_data in self.controllers.values():
                    controller = controller_data['controller']
                    mapping = controller_data['mapping']
                    
                    # 处理 hat 输入（D-pad）
                    if mapping.controller_type == "xbox360":
                        try:
                            for i in range(controller.get_numhats()):
                                hat = controller.get_hat(i)
                                if hat != (0, 0):  # 只在 hat 不在中心位置时处理
                                    current_time = time.time()
                                    if current_time - self.last_hat_time > self.hat_delay:
                                        if hat[1] == 1:  # 上
                                            print("HAT UP signal emitted")  # hat 上
                                            self.gamepad_signal.emit('UP')
                                        elif hat[1] == -1:  # 下
                                            print("HAT DOWN signal emitted")  # hat 下
                                            self.gamepad_signal.emit('DOWN')
                                        if hat[0] == -1:  # 左
                                            print("HAT LEFT signal emitted")  # hat 左
                                            self.gamepad_signal.emit('LEFT')
                                        elif hat[0] == 1:  # 右
                                            print("HAT RIGHT signal emitted")  # hat 右
                                            self.gamepad_signal.emit('RIGHT')
                                        self.last_hat_time = current_time
                                    else:
                                        self.last_hat_value = (0, 0)  # 重置上一次的 hat 值
                        except Exception as e:
                            print(f"Hat error: {e}")

                    # 读取摇杆
                    try:
                        left_x = controller.get_axis(mapping.left_stick_x)
                        left_y = controller.get_axis(mapping.left_stick_y)
                        right_x = controller.get_axis(mapping.right_stick_x)
                        right_y = controller.get_axis(mapping.right_stick_y)
                    except:
                        left_x = left_y = right_x = right_y = 0
                    
                    buttons = [controller.get_button(i) for i in range(controller.get_numbuttons())]
                    current_time = time.time()

                    # 检查摇杆移动
                    if time.time() - self.last_move_time > self.move_delay:
                        # 左摇杆
                        if left_y < -self.axis_threshold:
                            print("LEFT STICK UP signal emitted")  # 左摇杆上
                            self.gamepad_signal.emit('UP')
                            self.last_move_time = current_time
                        elif left_y > self.axis_threshold:
                            print("LEFT STICK DOWN signal emitted")  # 左摇杆下
                            self.gamepad_signal.emit('DOWN')
                            self.last_move_time = current_time
                        if left_x < -self.axis_threshold:
                            self.gamepad_signal.emit('LEFT')
                            self.last_move_time = current_time
                        elif left_x > self.axis_threshold:
                            self.gamepad_signal.emit('RIGHT')
                            self.last_move_time = current_time
                        
                        # 右摇杆
                        if right_y < -self.axis_threshold:
                            print(f"RIGHT STICK UP signal emitted{right_y}")  # 右摇杆上
                            self.gamepad_signal.emit('UP')
                            self.last_move_time = current_time
                        elif right_y > self.axis_threshold:
                            print("RIGHT STICK DOWN signal emitted")  # 右摇杆下
                            self.gamepad_signal.emit('DOWN')
                            self.last_move_time = current_time
                        if right_x < -self.axis_threshold:
                            self.gamepad_signal.emit('LEFT')
                            self.last_move_time = current_time
                        elif right_x > self.axis_threshold:
                            self.gamepad_signal.emit('RIGHT')
                            self.last_move_time = current_time

                    # 根据不同手柄类型处理 D-pad
                    if mapping.controller_type == "ps4":
                        # PS4 使用按钮
                        try:
                            if buttons[mapping.dpad_up]:
                                print("PS4 DPAD UP signal emitted")  # PS4 D-pad 上
                                self.gamepad_signal.emit('UP')
                            if buttons[mapping.dpad_down]:
                                print("PS4 DPAD DOWN signal emitted")  # PS4 D-pad 下
                                self.gamepad_signal.emit('DOWN')
                            if buttons[mapping.dpad_left]:
                                self.gamepad_signal.emit('LEFT')
                            if buttons[mapping.dpad_right]:
                                self.gamepad_signal.emit('RIGHT')
                        except:
                            pass
                    elif mapping.controller_type != "xbox360":  # 其他手柄（除了 Xbox 360）
                        # 其他手柄使用默认按钮方式
                        try:
                            if buttons[mapping.dpad_up]:
                                print("OTHER DPAD UP signal emitted")  # 其他手柄 D-pad 上
                                self.gamepad_signal.emit('UP')
                            if buttons[mapping.dpad_down]:
                                print("OTHER DPAD DOWN signal emitted")  # 其他手柄 D-pad 下
                                self.gamepad_signal.emit('DOWN')
                            if buttons[mapping.dpad_left]:
                                self.gamepad_signal.emit('LEFT')
                            if buttons[mapping.dpad_right]:
                                self.gamepad_signal.emit('RIGHT')
                        except:
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

class FloatingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        bat_dir = './morefloder'
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
            time.sleep(0.1)
            if self.select_add_btn:  # 确保按钮已经定义
                self.layout.removeWidget(self.select_add_btn)
            if self.select_del_btn:  # 确保按钮已经定义
                self.layout.removeWidget(self.select_del_btn)

        sorted_files = self.sort_files()
        for file in sorted_files:
            btn = QPushButton(file["name"])
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

            self.buttons.append(btn)
            self.layout.addWidget(btn)
            btn.clicked.connect(lambda checked, f=file: self.parent().execute_more_item(f))

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
        """选择bat文件"""
        file_dialog = QFileDialog(self, "选择要启动的文件", "", "Executable and Shortcut Files (*.exe *.lnk)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        if file_dialog.exec_():
            selected_file = file_dialog.selectedFiles()[0]
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
                        border: {int(2 * self.parent().scale_factor)}px solid yellow;
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
            
        print(f"Detected controller: {self.controller_name}")

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

        # 添加调整缩放因数的选项
        self.scale_factor_label = QLabel(f"界面缩放因数: {parent.scale_factor:.1f}")
        self.scale_factor_label.setStyleSheet(f"color: white; font-size: {int(16 * parent.scale_factor)}px;")
        self.scale_factor_label.setFixedHeight(int(30 * parent.scale_factor))  # 固定高度为30像素
        self.layout.addWidget(self.scale_factor_label)

        self.scale_factor_slider = QSlider(Qt.Horizontal)
        self.scale_factor_slider.setMinimum(5)
        self.scale_factor_slider.setMaximum(30)
        self.scale_factor_slider.setValue(int(parent.scale_factor * 10))
        self.scale_factor_slider.valueChanged.connect(self.update_scale_factor)
        self.layout.addWidget(self.scale_factor_slider)

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

        # 添加切换 killexplorer 状态的按钮
        #self.killexplorer_button = QPushButton(f"沉浸模式 {'√' if settings.get('killexplorer', False) else '×'}")
        #self.killexplorer_button.setStyleSheet(f"""
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
        #self.killexplorer_button.clicked.connect(self.toggle_killexplorer)
        #self.layout.addWidget(self.killexplorer_button)

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
        
        self.asdasgg_label = QLabel("提示：在手柄映射时通过系统\n托盘图标可打开主页面进行设置")
        self.asdasgg_label.setStyleSheet(f"color: white; font-size: {int(14 * parent.scale_factor)}px;")
        self.asdasgg_label.setFixedHeight(int(50 * parent.scale_factor))  # 固定高度为30像素
        self.layout.addWidget(self.asdasgg_label)
        
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

    def toggle_freeze(self):
        """切换 freeze 状态并保存设置"""
        settings["freeze"] = not settings.get("freeze", False)
        self.freeze_button.setText(f"回主页时尝试冻结游戏 {'√' if settings['freeze'] else '×'}")
        
        # 保存设置
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)


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

    def update_scale_factor(self, value):
        """更新缩放因数并保存设置"""
        scale_factor = value / 10.0
        self.parent().scale_factor = scale_factor
        self.scale_factor_label.setText(f"界面缩放因数: {scale_factor:.1f}")
        self.parent().reload_interface()
        # 保存缩放因数设置
        settings["scale_factor"] = scale_factor
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
        # 如果开启了沉浸模式，需要恢复explorer
        if self.parent().killexplorer:
            subprocess.run(["start", "explorer.exe"], shell=True)
        # 退出程序
        QTimer.singleShot(500, QApplication.quit())


# 应用程序入口
if __name__ == "__main__":
    global STARTUP  # 声明 STARTUP 为全局变量
    # 获取程序所在目录
    z_order = []
    def enum_windows_callback(hwnd, lParam):
        z_order.append(hwnd)
        return True
    win32gui.EnumWindows(enum_windows_callback, None)
    print(z_order)
    
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