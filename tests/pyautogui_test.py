# @Time    : 2026/2/28 10:39
# @Author  : Yun
# @FileName: pywinauto_test
# @Software: PyCharm
# @Desc    :
import time

import pyautogui

time.sleep(1)

x,y = pyautogui.size()
print(x,y)

time.sleep(2)
x = 2560 * 0.8836
y = 1600 * 0.9753

pyautogui.moveTo(x, y, duration=1)
time.sleep(0.5)
# pyautogui.click(x, y, duration=0.5)

pyautogui.hotkey('win', 'r')
# time.sleep(1)
# x = 2560 * 0.2183
# y = 1600 * 0.2556
#
# pyautogui.moveTo(x, y, duration=1)
# pyautogui.click(x, y, duration=0.5)
#
# time.sleep(1)
# x = 2560 * 0.2453
# y = 1600 * 0.2852
#
# pyautogui.moveTo(x, y, duration=1)
# pyautogui.click(x, y, duration=0.5)
# time.sleep(1)
# pyautogui.write('Hello, World!', interval=0.1)
#
#
# time.sleep(1)
# x = 2560 * 0.05
# y = 1600 * 0.09

# pyautogui.moveTo(x, y, duration=1)
# pyautogui.click(x, y, duration=0.5)
#
# time.sleep(1)
# x = 2560 * 0.05
# y = 1600 * 0.05
#
# pyautogui.moveTo(x, y, duration=1)
# pyautogui.click(x, y, duration=0.5)