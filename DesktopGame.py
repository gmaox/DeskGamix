import glob
import shutil
import sys
import json
import threading
import winreg
from PyQt5 import QtWidgets
from PyQt5 import QtGui
import pygame
import win32gui,win32process,psutil,win32api
from PyQt5.QtWidgets import QApplication, QListWidgetItem, QMessageBox, QSystemTrayIcon, QMenu , QVBoxLayout, QDialog, QGridLayout, QWidget, QPushButton, QLabel, QDesktopWidget, QHBoxLayout, QFileDialog, QSlider, QLineEdit, QProgressBar, QScrollArea, QFrame
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor
from PyQt5.QtCore import QDateTime, QSize, Qt, QThread, pyqtSignal, QTimer, QPoint, QProcess 
import subprocess, time, os,win32con, ctypes, re, win32com.client, ctypes, time, pyautogui
from ctypes import wintypes
#& C:/Users/86150/AppData/Local/Programs/Python/Python38/python.exe -m PyInstaller --add-data "fav.ico;." --add-data '1.png;.' -w DesktopGame.py -i '.\fav.ico' --uac-admin --noconfirm
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
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        ###下面俩行代码用于QuickStreamAppAdd的伪排序清除，若感到困惑可删除###
        for idx, entry in enumerate(data["apps"]):
            entry["name"] = re.sub(r'^\d{2} ', '', entry["name"])  # 去掉开头的两位数字和空格
    # 筛选具有标签路径的条目
    games = [
        app for app in data["apps"]
        if "output_image" in app.get("image-path", "") or "SGDB" in app.get("image-path", "") or "igdb" in app.get("image-path", "") or "steam/appcache/librarycache/" in app.get("image-path", "")
    ]

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
print(more_apps)
print(valid_apps)


# 焦点判断线程的标志变量
focus = True
focus_lock = threading.Lock()
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
class ScreenshotLoaderThread(QThread):
    """后台线程用于加载和缩放图片"""
    screenshot_loaded = pyqtSignal(list)  # 信号，用于通知主线程加载完成

    def __init__(self, screenshots, icon_size):
        super().__init__()
        self.screenshots = screenshots
        self.icon_size = icon_size

    def run(self):
        loaded_screenshots = []
        for path, game, ts in self.screenshots:
            try:
                pixmap = QtGui.QPixmap(path)
                thumb = pixmap.scaled(
                    int(self.icon_size), int(self.icon_size), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                loaded_screenshots.append((thumb, path, game, ts))
            except Exception as e:
                print(f"加载图片失败: {path}, 错误: {e}")
        self.screenshot_loaded.emit(loaded_screenshots)

class ScreenshotWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_dialog = None  # 新增：记录当前弹窗
        self.filter_game_name = None  # 当前筛选的游戏名
        self.setWindowTitle("截图浏览")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(1800, 1000)
        self.icon_size = 256 * getattr(self, 'scale_factor', 1.0)
        # ScreenshotWindow.__init__ 内左侧面板部分
        # 统一按钮样式
        btn_style = f"""
            QPushButton {{
                background-color: #444444;
                color: white;
                text-align: center;
                padding: {int(10 * getattr(self, 'scale_factor', 1.0))}px;
                border: none;
                font-size: {int(30 * getattr(self, 'scale_factor', 1.0))}px;
            }}
            QPushButton:hover {{
                background-color: #555555;
            }}
        """

        BTN_HEIGHT = 90  # 统一按钮高度

        def on_backup_save_clicked():
            open_maobackup("--quick-dgaction")
        def on_backup_restore_clicked(): 
            open_maobackup("--quick-dgrestore")
        def open_maobackup(sysargv):
            exe_path = os.path.join(program_directory, "maobackup.exe")
            game_name = self.game_name_label.text()
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
                                self.confirm_dialog = ConfirmDialog("※"+msg.get("message", "")).exec_()
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
                self.confirm_dialog = ConfirmDialog("未找到maobackup.exe").exec_()
        def on_view_backup_list_clicked(): pass
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
            options = ["跟随全局", "不冻结", "内置核心冻结", "调用雪藏冻结"]
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
            self.close()  # 关闭当前窗口
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
            # 弹出输入框让用户输入新名称
            old_name = self.game_name_label.text()
            new_name, ok = QtWidgets.QInputDialog.getText(
                self,
                "重命名游戏",
                '<span style="color:white;">请输入新的游戏名称：</span>',
                QLineEdit.Normal,
                old_name
            )
            
            if ok and new_name and new_name != old_name:
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
            self.confirm_dialog = ConfirmDialog("确认从游戏列表移除该游戏吗？\n（不会删除游戏数据）")
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            self.confirm_dialog = ConfirmDialog("确认从游戏列表移除该游戏吗？\n（二次确认）")
            result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
            self.ignore_input_until = pygame.time.get_ticks() + 350  
            if not result == QDialog.Accepted:  # 如果按钮没被点击
                return
            self.qsaa_thread = QuickStreamAppAddThread(args=["-delete", str(self.game_name_label.text())])
            if self.parent() and hasattr(self.parent(), "deep_reload_games"):
                self.qsaa_thread.finished_signal.connect(self.parent().deep_reload_games)
                self.qsaa_thread.finished_signal.connect(self.close)
            self.qsaa_thread.start()


        # 主水平布局
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 左侧信息面板
        self.left_panel = QWidget(self)
        left_panel_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_panel_layout.setAlignment(Qt.AlignTop)

        # 游戏名标签
        self.game_name_label = QLabel("游戏名称", self.left_panel)
        self.game_name_label.setStyleSheet("color: white; font-size: 40px; font-weight: bold;")
        self.game_name_label.setMaximumWidth(self.width() // 2- 150)
        self.play_time_label = QLabel(self.left_panel)
        self.play_time_label.setStyleSheet("color: white; font-size: 30px; font-weight: normal;")
        left_panel_layout.addWidget(self.game_name_label)
        left_panel_layout.setSpacing(10)
        left_panel_layout.addWidget(self.play_time_label)
        left_panel_layout.setSpacing(19)

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
        self.info_label2.setStyleSheet("color: #aaa; font-size: 16px; padding: 0px;")
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
        self.info_label1.setStyleSheet("color: #aaa; font-size: 16px; padding: 0px;")
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
        self.listWidget.setSpacing(10)
        self.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.listWidget.itemClicked.connect(self.on_item_clicked)
        self.listWidget.setFocus()

        # 右侧布局（包含listWidget）
        right_panel = QWidget(self)
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_layout.addWidget(self.listWidget, alignment=Qt.AlignRight)  # 确保列表靠右对齐、
        self.info_label = QLabel(self)
        self.info_label.setStyleSheet("color: #aaa; font-size: 18px; padding: 8px;")
        self.info_label.setAlignment(Qt.AlignLeft)
        right_layout.addWidget(self.info_label)

        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(right_panel)

        # 用 QWidget 包裹 main_layout
        main_widget = QWidget(self)
        main_widget.setLayout(self.main_layout)

        # 外层垂直布局
        layout = QtWidgets.QVBoxLayout(self)
        # 关闭按钮放在最上面
        self.closeButton = QPushButton("关闭", self)
        self.closeButton.setFixedHeight(50)
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
        layout.addWidget(main_widget)
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
        self.load_screenshots()
        self.listWidget.clear()  # 加载前先清除原图片
        item = QListWidgetItem()
        item.setFlags(Qt.NoItemFlags)
        label = QLabel("正在加载截图...")
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
            self.left_panel.show()
            self.listWidget.setFixedWidth(int(self.width() / 1.7) - 74)
            self.icon_size = int(256 * getattr(self, 'scale_factor', 1.0) * 1.8)
        else:
            self.current_screenshots = list(self.all_screenshots)
            self.left_panel.hide()
            self.listWidget.setFixedWidth(self.width() - 60)
            self.icon_size = 256 * getattr(self, 'scale_factor', 1.0)
            self.has_load_more_button = False

        self.listWidget.setIconSize(QSize(int(self.icon_size), int(self.icon_size)))

        # 启动后台线程加载图片
        self.loader_thread = ScreenshotLoaderThread(self.current_screenshots, self.icon_size)
        self.loader_thread.screenshot_loaded.connect(self.on_screenshots_loaded)
        self.loader_thread.finished.connect(self.update_highlight)
        self.loader_thread.start()

    def load_all_images_and_refresh(self):
        """加载全部图片并刷新列表"""
        # 记录当前索引
        self.restore_index_after_load = self.current_index
        self.load_all_images = True
        self.reload_screenshots()

    def update_highlight(self):
        """更新高亮状态"""
        self.buttons = [self.listWidget.item(i) for i in range(self.listWidget.count())]
        info_text = ""
        if self.buttons:
            self.current_index = max(0, min(self.current_index, len(self.buttons) - 1))
            # 检查是否高亮到“加载全部图片”按钮
            if getattr(self, "has_load_more_button", False) and self.current_index == getattr(self, "load_more_item_index", -1):
                self.load_all_images_and_refresh()
                self.info_label.setText("")
                return  # 刷新后不再继续
            if not self.in_left_panel:
                self.listWidget.setCurrentItem(self.buttons[self.current_index])
                self.listWidget.scrollToItem(self.buttons[self.current_index])
                for i, item in enumerate(self.buttons):
                    if i == self.current_index:
                        item.setBackground(QColor("#93ffff"))
                        # 显示信息
                        img_path = item.data(Qt.UserRole)
                        # 查找截图元数据并获取索引
                        if getattr(self, "has_load_more_button", False):
                            allidx = ".."
                        else:
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
        """更新 UI，显示加载完成的图片"""
        self.listWidget.clear()
        # 没有截图时显示提示文字
        if not loaded_screenshots and not getattr(self, "has_load_more_button", False):
            item = QListWidgetItem()
            item.setFlags(Qt.NoItemFlags)
            label = QLabel("还没有截图\n在游戏中按下L3+R3记录美好时刻～")
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            label.setStyleSheet("color: #aaa; font-size: 28px;")
            label.setMinimumHeight(220)
            label.setMinimumWidth(self.listWidget.viewport().width() - 40)
            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, label)
            item.setSizeHint(label.sizeHint())
            return
        for thumb, path, game, ts in loaded_screenshots:
            icon = QtGui.QIcon(thumb)
            item = QListWidgetItem(icon, "")
            item.setData(Qt.UserRole, path)
            self.listWidget.addItem(item)
        # 如果需要“加载全部图片”按钮
        if getattr(self, "has_load_more_button", False):
            btn_item = QListWidgetItem()
            btn_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            btn_widget = QPushButton("加载更多截图...")
            btn_widget.setStyleSheet("font-size: 16px; color: #aaa; background: #666; border-radius: 12px;")
            #btn_widget.setFixedSize(self.icon_size, self.icon_size)
            btn_widget.clicked.connect(self.load_all_images_and_refresh)
            btn_widget.setMinimumHeight(20)
            btn_widget.setMinimumWidth(self.listWidget.viewport().width() - 40)

            self.listWidget.addItem(btn_item)
            self.listWidget.setItemWidget(btn_item, btn_widget)
            btn_item.setSizeHint(btn_widget.sizeHint())
            self.load_more_item_index = self.listWidget.count() - 1  # 记录按钮索引
        else:
            self.load_more_item_index = None
        # 加载完成后恢复索引并高亮
        if hasattr(self, "restore_index_after_load"):
            self.current_index = min(self.restore_index_after_load, self.listWidget.count() - 1)
            del self.restore_index_after_load
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
            # 检查是否要跳到“加载全部图片”按钮
            if getattr(self, "has_load_more_button", False) and hasattr(self, "load_more_item_index"):
                if offset == row_count and self.current_index == self.load_more_item_index - 1:
                    # 当前在最后一张图片，向下跳到“加载全部图片”按钮
                    self.current_index = self.load_more_item_index
                    self.update_highlight()
                    return
                elif new_index == self.load_more_item_index:
                    # 其它情况直接跳到按钮
                    self.current_index = self.load_more_item_index
                    self.update_highlight()
                    return
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
                self.close()
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
                self.close()
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
                self.close()
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
                        padding: {int(10 * getattr(self, 'scale_factor', 1.0))}px;
                        border: {int(2 * getattr(self, 'scale_factor', 1.0))}px solid #93ffff;
                        font-size: {int(30 * getattr(self, 'scale_factor', 1.0))}px;
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #444444;
                        color: white;
                        text-align: center;
                        padding: {int(10 * getattr(self, 'scale_factor', 1.0))}px;
                        border: none;
                        font-size: {int(30 * getattr(self, 'scale_factor', 1.0))}px;
                    }}
                    QPushButton:hover {{
                        background-color: #555555;
                    }}
                """)

    def start_fullscreen_preview(self):
        """显示当前选中图片的全屏预览对话框"""
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
        self.is_fullscreen_preview.setWindowFlag(Qt.Window)
        self.is_fullscreen_preview.showFullScreen()
        
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
        info_bar.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 200);
                color: white;
                font-size: 16px;
                padding: 10px;
                border-bottom: 1px solid #333;
            }
        """)
        info_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        info_bar.setFixedHeight(40)  # 设置固定高度
        info_bar.setTextFormat(Qt.RichText)
        info_bar.setTextInteractionFlags(Qt.TextBrowserInteraction)
        info_bar.setOpenExternalLinks(False)  # 不自动打开外部链接
        info_bar.linkActivated.connect(self.handle_info_bar_link)
        def close_fullscreen_preview(event):
            """关闭全屏预览窗口"""
            if hasattr(self, 'is_fullscreen_preview') and self.is_fullscreen_preview:
                self.is_fullscreen_preview.close()  # 修复调用
                self.is_fullscreen_preview = None  # 清除引用
        #info_bar.mousePressEvent = close_fullscreen_preview
        main_layout.addWidget(info_bar)
        
        # 创建图片标签
        label = QtWidgets.QLabel(self.is_fullscreen_preview)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: black;")
        label.mousePressEvent = close_fullscreen_preview
        main_layout.addWidget(label)
    
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
            scaled_width = int(screen.width() * 0.9)
            scaled_height = int(screen.height() * 0.9)
            scaled = pix.scaled(scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(scaled)
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
            self.confirm_dialog = ConfirmDialog(f"确认删除选中的截图？\n{path}")
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
                self.confirm_dialog = ConfirmDialog(f"确认删除选中的截图？\n{path}")
                if self.confirm_dialog.exec_():
                    if os.path.exists(path):
                        os.remove(path)
                    row = self.listWidget.row(item)
                    self.listWidget.takeItem(row)
                    # 同时从数据列表移除
                    self.all_screenshots = [s for s in self.all_screenshots if s[0] != path]
                    self.current_screenshots = [s for s in self.current_screenshots if s[0] != path]
                    self.reload_screenshots()
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
        if "※" in self.variable1:
            self.label.setStyleSheet("font-size: 24px; color: #FFFFFF; margin-bottom: 40px; text-align: center;")
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
class MouseWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Create a label to display the text
        self.label = QLabel("↖(L3R3关闭映射)", self)
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
class MouseSimulationThread(QThread):
    finished_signal = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self._running = True

    def run(self):
        self.parent.is_mouse_simulation_running = True
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            self.parent.show_window()
            self.parent.is_mouse_simulation_running = False
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
        axes = joysticks[0].get_numaxes()
        if axes >= 6:
            rt_axis = 5
        else:
            rt_axis = 2
        if axes >= 6:
            lt_axis = 4
        else:
            lt_axis = 2
        SENS_HIGH = 100.0
        SENS_MEDIUM = 25.0
        SENS_LOW  = 10.0
        sensitivity = SENS_MEDIUM
        sensitivity1 = SENS_LOW
        DEADZONE = 0.1
        clock = pygame.time.Clock()
        scrolling_up = False
        scrolling_down = False
        window = self.parent.mouse_window 
        last_mouse_x, last_mouse_y = -1, -1
        left_button_down = False
        right_button_down = False
        screen_width, screen_height = pyautogui.size()
        pyautogui.moveTo(int(screen_width/2), int(screen_height/2))
        time.sleep(0.7)
        running = True
        try:
            while running and self._running and self.parent.is_mouse_simulation_running:
                for event in pygame.event.get():
                    if event.type == pygame.JOYDEVICEADDED:
                        joystick = pygame.joystick.Joystick(event.device_index)
                        joystick.init()
                        joysticks.append(joystick)
                        joystick_states[joystick.get_instance_id()] = {"scrolling_up": False, "scrolling_down": False}
                    elif event.type == pygame.JOYDEVICEREMOVED:
                        for joystick in joysticks:
                            if joystick.get_instance_id() == event.instance_id:
                                joysticks.remove(joystick)
                                del joystick_states[event.instance_id]
                                break
                pygame.event.pump()
                mouse_x, mouse_y = pyautogui.position()
                if (mouse_x, mouse_y) != (last_mouse_x, last_mouse_y):
                    window.label.move(mouse_x, mouse_y)
                    last_mouse_x, last_mouse_y = mouse_x, mouse_y
                joycount = pygame.joystick.get_count()
                for joystick in joysticks:
                    mapping = ControllerMapping(joystick)
                    if joystick.get_button(mapping.guide) or joystick.get_button(mapping.right_stick_in) or joystick.get_button(mapping.left_stick_in):
                        running = False
                        if self.parent.is_virtual_keyboard_open():
                            self.parent.close_virtual_keyboard()
                        if self.parent.is_magnifier_open():
                            self.parent.close_magnifier()
                        right_bottom_x = screen_width - 1
                        right_bottom_y = screen_height - 1
                        pyautogui.moveTo(right_bottom_x, right_bottom_y)
                        break
                    if joystick.get_button(mapping.button_a) or joystick.get_button(mapping.right_bumper):
                        if not left_button_down:
                            pyautogui.mouseDown()
                            left_button_down = True
                    else:
                        if left_button_down:
                            pyautogui.mouseUp()
                            left_button_down = False
                    if joystick.get_button(mapping.button_b) or joystick.get_button(mapping.left_bumper):
                        if not right_button_down:
                            pyautogui.mouseDown(button='right')
                            right_button_down = True
                    else:
                        if right_button_down:
                            pyautogui.mouseUp(button='right')
                            right_button_down = False
                    if mapping.has_hat:
                        hat_value = joystick.get_hat(0)
                        if hat_value == (-1, 0):
                            self.parent.decrease_volume()
                            time.sleep(0.2)
                        elif hat_value == (1, 0):
                            self.parent.increase_volume()
                            time.sleep(0.2)
                        elif joystick.get_button(mapping.button_x) or hat_value == (0, -1):
                            scrolling_down = True
                        elif joystick.get_button(mapping.button_y) or hat_value == (0, 1):
                            scrolling_up = True
                        else:
                            scrolling_down = False
                            scrolling_up = False
                    else:
                        if joystick.get_button(mapping.dpad_left):
                            self.parent.decrease_volume()
                            time.sleep(0.2)
                        elif joystick.get_button(mapping.dpad_right):
                            self.parent.increase_volume()
                            time.sleep(0.2)
                        if joystick.get_button(mapping.button_x) or joystick.get_button(mapping.dpad_down):
                            scrolling_down = True
                        else:
                            scrolling_down = False
                        if joystick.get_button(mapping.button_y) or joystick.get_button(mapping.dpad_up):
                            scrolling_up = True
                        else:
                            scrolling_up = False
                    x_axis = joystick.get_axis(0)
                    y_axis = joystick.get_axis(1)
                    rt_val = joystick.get_axis(rt_axis)
                    lt_val = joystick.get_axis(lt_axis)
                    rx_axis = joystick.get_axis(2)
                    ry_axis = joystick.get_axis(3)
                    def backandstart_pressed():
                        if joystick.get_button(mapping.back):
                            pyautogui.hotkey('win', 'a')
                            screen_width, screen_height = pyautogui.size()
                            pyautogui.moveTo(screen_width * 7 / 8, screen_height * 6 / 8)
                            time.sleep(0.5)
                        if joystick.get_button(mapping.start):
                            if not self.parent.is_magnifier_open():
                                self.parent.open_magnifier()
                            else:
                                self.parent.close_magnifier()
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
                        if self.parent.is_magnifier_open():
                            self.parent.close_magnifier()
                        else:
                            if self.parent.is_virtual_keyboard_open():
                                self.parent.close_virtual_keyboard()
                            else:
                                pyautogui.moveTo(int(screen_width/2), int(screen_height/1.5))
                                self.parent.open_virtual_keyboard()
                        time.sleep(0.5)
                    if joystick.get_button(mapping.back):
                        pyautogui.hotkey('win', 'tab')
                        pyautogui.moveTo(int(screen_width/2), int(screen_height/2))
                        time.sleep(0.5)
                    dx = dy = 0
                    if abs(rx_axis) > DEADZONE:
                        self.parent.move_mouse_once()
                        dx = rx_axis * sensitivity1
                    if abs(ry_axis) > DEADZONE:
                        self.parent.move_mouse_once()
                        dy = ry_axis * sensitivity1
                    pyautogui.moveRel(dx, dy)
                    dx = dy = 0
                    if abs(x_axis) > DEADZONE:
                        self.parent.move_mouse_once()
                        dx = x_axis * sensitivity
                    if abs(y_axis) > DEADZONE:
                        self.parent.move_mouse_once()
                        dy = y_axis * sensitivity
                    pyautogui.moveRel(dx, dy)
                    if scrolling_up:
                        pyautogui.scroll(50)
                    if scrolling_down:
                        pyautogui.scroll(-50)
                    clock.tick(int(60*joycount))
        except KeyboardInterrupt:
            print("程序已退出。")
        finally:
            self.parent.is_mouse_simulation_running = False
            self.finished_signal.emit()
            print("鼠标已退出")
    def stop(self):
        self._running = False
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
        global play_reload
        super().__init__()
        self.back_start_pressed_time = None  # 初始化按键按下时间
        self.back_start_action = set()
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
        self.resize(1, 1)  # 初始设置为1x1，后续会调整为全屏
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
        self.resize(screen.width(), screen.height()) # 设置窗口大小为屏幕分辨率
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
        self.in_floating_window = False
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
        self.monitor_thread = MonitorRunningAppsThread(self.play_lock, self.play_app_name)
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
        self.left_layout.addWidget(self.screenshot_button)

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
                btn.setText("🔉")
                btn.clicked.connect(self.decrease_volume)
            elif i == 1:
                btn.setText("🔊")
                btn.clicked.connect(self.increase_volume)
            elif i == 2:
                btn.setText("🔇")
                btn.clicked.connect(self.deep_reload_games)
            elif i == 3:
                btn.setText("🖱️")
                btn.clicked.connect(lambda checked=False: (self.hide_window(), self.mouse_simulation()))
            elif i == 4:
                btn.setText("🗺️")
                btn.clicked.connect(self.show_img_window)
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
        right_label = QLabel("A / 进入游戏        B / 最小化        Y / 收藏        X / 更多            📦️DeskGamix v0.95-Alpha")
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
        self.tray_icon.setToolTip("DeskGamix")
        def create_tray_menu():
            tray_menu = QMenu(self)
            sorted_games = self.sort_games()
            if sorted_games:
                tray_menu.addSeparator()
                #for idx, game in enumerate(sorted_games[:self.buttonsindexset]):    #正序显示的代码
                for idx, game in enumerate(reversed(sorted_games[:self.buttonsindexset])):
                    #game_action = tray_menu.addAction(game["name"])
                    game_action = tray_menu.addAction(game["name"][:24] + "..." if len(game["name"]) > 24 else game["name"])
                    #def launch_and_close_tray(i=idx):    #正序显示的代码
                    game_action.triggered.connect(lambda checked=False, i=len(sorted_games[:self.buttonsindexset])-1-idx: (self.tray_icon.contextMenu().hide(), self.launch_game(i)))
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
                tool_action = tools_menu.addAction(app["name"])
                def launch_tool(checked=False, path=app["path"]):
                    self.hide_window()
                    if isinstance(path, str) and path.strip():
                        subprocess.Popen(path, shell=True)
                tool_action.triggered.connect(launch_tool)
            tray_menu.addMenu(tools_menu)
            tray_menu.addSeparator()
            restart_action = tray_menu.addAction("重启程序")
            restart_action.triggered.connect(self.restart_program)
            restore_action = tray_menu.addAction("显示主页面")
            restore_action.triggered.connect(self.show_window)
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

        # 初始菜单
        self.tray_icon.setContextMenu(create_tray_menu())

        def tray_icon_activated(reason):
            if self.is_mouse_simulation_running:
                self.is_mouse_simulation_running = False
                return
            if reason == QSystemTrayIcon.Context:  # 右键
                self.tray_icon.setContextMenu(create_tray_menu())
            elif reason == QSystemTrayIcon.Trigger:  # 左键
                self.show_window()

        self.tray_icon.activated.connect(tray_icon_activated)
        self.tray_icon.show()  # 显示托盘图标
        # 新增：每分钟记录游玩时间
        self.play_time_timer = QTimer(self)
        self.play_time_timer.timeout.connect(self.update_play_time)
        self.play_time_timer.start(60 * 1000)  # 60秒

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
        self.scroll_area.setFixedHeight(int(self.height()*0.85))  # 设置为90%高度
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
            ctypes.windll.shell32.ShellExecuteW(None, "open", "magnify.exe", None, None, 1)
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

    def mouse_simulation(self):
        """开启鼠标映射（线程方式）"""
        if self.is_mouse_simulation_running:
            print("鼠标映射已在运行，忽略重复调用")
            return
        if not hasattr(self, 'mouse_window') or self.mouse_window is None:
            self.mouse_window = MouseWindow()
        else:
            self.mouse_window.show()
        self.mouse_sim_thread = MouseSimulationThread(self)
        self.mouse_sim_thread.finished_signal.connect(self.on_mouse_simulation_finished)
        self.mouse_sim_thread.start()

    def on_mouse_simulation_finished(self):
        self.is_mouse_simulation_running = False
        if hasattr(self, 'mouse_window') and self.mouse_window:
            self.mouse_window.close()
            self.mouse_window = None
            
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

        # 修改：点击时先判断光标位置
        def on_button_clicked(checked=False, idx=index):
            if self.current_index != idx:
                self.current_index = idx
                self.update_highlight()
            else:
                self.launch_game(idx)
        button.clicked.connect(on_button_clicked)

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
                            border: {int(2 * self.scale_factor)}px solid #555555;
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
                            border: {int(4 * self.scale_factor)}px solid #93ffff;
                        }}
                        QPushButton:hover {{
                            border: {int(4 * self.scale_factor)}px solid #25ade7;
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
        if self.buttons and self.current_section == 0 and self.more_section == 1:
            current_button = self.buttons[self.current_index]
            # 修正：获取按钮在scroll_widget中的准确位置
            button_pos = current_button.mapTo(self.scroll_widget, QPoint(0, 0))
            scroll_area_height = self.scroll_area.viewport().height()
            scroll_bar = self.scroll_area.verticalScrollBar()
            # 如果按钮顶部超出可视区域
            if button_pos.y() < scroll_bar.value():
                scroll_bar.setValue(button_pos.y())
            # 如果按钮底部超出可视区域
            elif button_pos.y() + current_button.height() > scroll_bar.value() + scroll_area_height:
                scroll_bar.setValue(button_pos.y() + current_button.height() - scroll_area_height)
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
                # 第一个按钮，滚动到最左边
                self.scroll_area.horizontalScrollBar().setValue(0)
            elif self.current_index >= 1:
                button_pos = QPoint(current_button.mapToGlobal(QPoint(0, 0)))  # 获取当前按钮的精确位置
                scroll_value = self.scroll_area.horizontalScrollBar().value()  # 获取当前滚动值
                # 当靠近左边缘且左侧还有游戏时，稍微偏移一点让左侧游戏露出
                if button_pos.x() < scroll_area_pos.x() + offset and self.current_index > 0:
                    second_button_pos = self.buttons[0].mapToGlobal(QPoint(0, 0)).x()
                    scroll_value = button_pos.x() - second_button_pos - offset
                    self.scroll_area.horizontalScrollBar().setValue(scroll_value)
                # 当靠近右边缘且移动距离大于3时调整滚动
                elif button_pos.x() + button_width > scroll_area_pos.x() + scroll_area_width:
                    second_button_pos = self.buttons[min(3, len(self.buttons) - 1)].mapToGlobal(QPoint(0, 0)).x()
                    scroll_value = button_pos.x() - second_button_pos
                    self.scroll_area.horizontalScrollBar().setValue(scroll_value)
        #
        #self.game_name_label.move(button_pos.x(), button_pos.y() - self.game_name_label.height())
        #self.game_name_label.show()
        # 新增文本显示，复制game_name_label的内容
        if self.current_section == 0 and self.more_section == 0: 
            self.game_name_label.setStyleSheet(f"""QLabel {{color: #1e1e1e;}}""")
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
                        #print("焦点在游戏窗口")
                    else:
                        focus = False
                        #print("焦点不在游戏窗口")
            time.sleep(0.1)  # 稍微休眠，避免线程占用过多 CPU
    
    # 启动焦点判断线程
    thread = threading.Thread(target=focus_thread, daemon=True)
    thread.start()   
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
        self.ignore_input_until = pygame.time.get_ticks() + 600

        if self.more_section == 0 and self.current_index == self.buttonsindexset: # 如果点击的是"更多"按钮
            self.switch_to_all_software()
            return
        #冻结相关
        if os.path.exists("pssuspend64.exe"):
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
                                    ['pssuspend64.exe', '-r', os.path.basename(game_path)],
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
        self.ignore_input_until = pygame.time.get_ticks() + 1000
        # 新增：如果该游戏在 on_mapping_clicked 里，自动开启鼠标映射
        if "on_mapping_clicked" in settings and game_name in settings["on_mapping_clicked"]:
            self.mouse_simulation()
        if game_cmd:
            #self.showMinimized()
            subprocess.Popen(game_cmd, shell=True)
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
                self.confirm_dialog = ConfirmDialog("该游戏未绑定进程\n点击确定后将打开自定义进程页面")
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
                    if os.path.exists("pssuspend64.exe"):
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
                                ['pssuspend64.exe', exe_name],
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
        # 跟踪焦点状态
        current_time = pygame.time.get_ticks()
        # 如果在屏蔽输入的时间段内，则不处理
        if current_time < self.ignore_input_until:
            return
        
        if current_time - self.last_input_time < self.input_delay:
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
                        for i in range(0, 101, 2):
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
                                self.in_floating_window = False
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
        
        if hasattr(self, 'confirm_dialog') and self.confirm_dialog.isVisible():  # 如果确认弹窗显示中
            print("确认弹窗显示中")
            self.ignore_input_until = current_time + 500
            self.confirm_dialog.handle_gamepad_input(action)
            return
        if hasattr(self, 'screenshot_window') and self.screenshot_window.isVisible():
            # 如果 screenshot_window 有 confirm_dialog，优先转发
            if hasattr(self.screenshot_window, 'confirm_dialog') and self.screenshot_window.confirm_dialog and self.screenshot_window.confirm_dialog.isVisible():
                self.screenshot_window.handle_gamepad_input(action)
                self.ignore_input_until = pygame.time.get_ticks() + 300 
                return
            print("截图悬浮窗显示中")
            self.ignore_input_until = current_time + 200
            self.screenshot_window.handle_gamepad_input(action)
            return
        
        if self.in_floating_window and self.floating_window:
            # 如果 floating_window 有 confirm_dialog，优先转发
            if hasattr(self.floating_window, 'confirm_dialog') and self.floating_window.confirm_dialog and self.floating_window.confirm_dialog.isVisible():
                self.floating_window.handle_gamepad_input(action)
                self.ignore_input_until = pygame.time.get_ticks() + 300 
                return
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
                elif action == 'START':  # START键打开游戏详情
                    self.open_selected_game_screenshot()
                elif action == 'BACK':  # SELECT键打开设置
                    if current_time < ((self.ignore_input_until)+500):
                        return
                    self.ignore_input_until = pygame.time.get_ticks() + 500 
                    if not self.in_floating_window and self.can_toggle_window():
                        self.mouse_simulation()
                        self.show_settings_window()
                        QTimer.singleShot(10, lambda: pyautogui.moveTo(int(self.settings_button.mapToGlobal(self.settings_button.rect().center()).x()+100), int(self.settings_button.mapToGlobal(self.settings_button.rect().center()).y())+270))
                elif action == 'GUIDE':  # 回桌面
                    if current_time < ((self.ignore_input_until)+500):
                        return
                    self.ignore_input_until = pygame.time.get_ticks() + 500 
                    if not self.in_floating_window and self.can_toggle_window():
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
        self.in_floating_window = False
        if enable_mouse_sim:
            self.mouse_simulation()

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

        # 添加点击事件，点击悬浮窗时隐藏
        def hide_overlay(event):
            self.parent.launch_overlay.hide()
        self.parent.launch_overlay.mousePressEvent = hide_overlay

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
                                            #print("HAT UP signal emitted")  # hat 上
                                            self.gamepad_signal.emit('UP')
                                        elif hat[1] == -1:  # 下
                                            #print("HAT DOWN signal emitted")  # hat 下
                                            self.gamepad_signal.emit('DOWN')
                                        if hat[0] == -1:  # 左
                                            #print("HAT LEFT signal emitted")  # hat 左
                                            self.gamepad_signal.emit('LEFT')
                                        elif hat[0] == 1:  # 右
                                            #print("HAT RIGHT signal emitted")  # hat 右
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
                            #print("LEFT STICK UP signal emitted")  # 左摇杆上
                            self.gamepad_signal.emit('UP')
                            self.last_move_time = current_time
                        elif left_y > self.axis_threshold:
                            #print("LEFT STICK DOWN signal emitted")  # 左摇杆下
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
                    if buttons[mapping.back]:  # Back
                        self.gamepad_signal.emit('BACK')
                    if buttons[mapping.start]:  # Start
                        self.gamepad_signal.emit('START')
                    #if buttons[mapping.left_bumper]:  # LB
                    #    self.gamepad_signal.emit('LB')
                    #if buttons[mapping.right_bumper]:  # RB
                    #    self.gamepad_signal.emit('RB')
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
                self.confirm_dialog = ConfirmDialog(f"是否关闭下列程序？\n{current_file['name']}")
                result = self.confirm_dialog.exec_()  # 显示弹窗并获取结果
                self.ignore_input_until = pygame.time.get_ticks() + 350  # 设置屏蔽时间为800毫秒
            else:
                result = False
            # 关闭窗口
            self.current_index = 0
            self.update_highlight()
            self.hide()
            self.parent().in_floating_window = False
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
        icon_pix = QPixmap("fav.ico").scaled(int(36 * self.parent().scale_factor), int(36 * self.parent().scale_factor), Qt.KeepAspectRatio, Qt.SmoothTransformation)
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