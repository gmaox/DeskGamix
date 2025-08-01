# DeskGamix
新概念游戏前端，为非模拟器游戏/家用电脑而生，仿Switch界面

https://wwse.lanzoup.com/b00uz4bjmd
密码:85jl
<details>
<summary>
●开发者想说●
</summary>
不一定是这个名字，也不太可能能寻得好名字

DeskGamix（desk→犹如电脑桌面般轻松操作，gamix→game/mix→代表游戏领域工具/把很多东西融合在一起了（鼠标操控/电源选项/音量调整/暂停-回到-结束游戏））

使用pyqt5+pygame，pyautogui用于突破窗口焦点限制/鼠标操控功能。<small>代码带中文注释，有兴趣可以自己加功能。（GameSelector类为界面主体，涵盖手柄操作逻辑/界面构成/游戏启动逻辑，是进行二次开发的好切入点）</small>

没有界面动画挺可惜的，若您有能力实现这一功能，操作体验将大幅提升。
</details>
  
![1000131674](https://github.com/user-attachments/assets/f2f0966b-c572-4681-8dc4-a279819e04e2)
![1000131675](https://github.com/user-attachments/assets/305dd201-c5b3-472b-a296-7506b650433f)
![1000131676](https://github.com/user-attachments/assets/17416ae1-141b-4851-aca5-09ff6bd97480)


https://github.com/user-attachments/assets/d2b6d54d-dddf-40b1-a04b-074df70ee1cf



该前端的优势：
<p>1.依托qt5的自适应布局，界面布局简单舒适
<p>2.一键启动。playnite等一众前端启动游戏时更倾向于展示游戏介绍信息甚至启动影片，更倾向于电玩店，自用其实不太需要。从开启前端到进入游戏仅需3秒
<p>3.配置简单，更专注于游戏
<p>4.仿switch后台唤起，符合逻辑的关闭应用
<p>5.控件大小可调节，列数可编辑
<p>6.前端集成手柄模拟鼠标键盘，体验舒适
<p>7.无论你是客厅手柄还是掌机玩家，还是偶尔使用键盘鼠标的家用电脑玩家，你都能在这个软件获得较舒适的游戏体验
<p>0.依靠sunshine和qsaa管理游戏列表

  未来会加入的：

1.仿switch横向排列，应用下放置工具栏排列更多中的内容，最后面加上电源选项（已完成

2.对本次运行周期内从前端已经进入的无进程信息游戏，将收藏按钮改变为绑定进程信息。（不需要了）

3.改变触屏进入游戏逻辑（单击变为移动焦点，不确定更改是否合适，低优先级（已完成）

4.加入按键das和arr改善手感（低优先级

0.动画效果（不会做
