# @Time    : 2026/3/1 12:25
# @Author  : Yun
# @FileName: pywinauto_test
# @Software: PyCharm
# @Desc    :
import time
from pywinauto import Application, Desktop

# 启动WPS
app = Application(backend='uia').start('D:/Software/WPS Office/ksolaunch.exe')
time.sleep(1)
print(app.process)

# 从桌面查找标题为“WPS Office”的窗口
main_window = Desktop(backend="uia").window(title="WPS Office")
main_window.wait('visible', timeout=2)  # 等待窗口可见

# 获取所有标题为“新建”的按钮，并点击左侧边栏的那个（通常第二个）
new_btns = main_window.descendants(title="新建", control_type="Button")
if len(new_btns) >= 2:
    new_btns[0].click()  # 点击左侧边栏的“新建”按钮
else:
    new_btns[0].click()  # 只有一个则点击第一个
# 假设 main_window 是你之前获取的WPS主窗口
new_window = main_window.child_window(title="新建", control_type="Window")
# new_window.print_control_identifiers()
