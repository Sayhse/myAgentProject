import os
import time
import base64
import subprocess
import logging
from io import BytesIO
from datetime import datetime

from PIL import Image
import pyautogui
import requests

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("LoginTest")

# ==================== 配置区域 ====================
# 天翼云电脑客户端可执行文件路径（请根据实际安装路径修改）
CLIENT_PATH = r"D:\Software\CtyunCloud\CtyunClouddeskPublic\bin\clouddesktop-qml.exe"

# 阿里云视觉模型 API 配置（兼容 OpenAI 格式）
# 获取 API Key：https://help.aliyun.com/zh/model-studio/get-api-key
ALIYUN_API_KEY = "sk-dc529e6be2344352adcfc82f48712f3e"

# 根据地域选择对应的 base_url
ALIYUN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# 视觉模型名称（注意：必须为视觉模型，如 qwen-vl-plus / qwen3-vl-plus）
ALIYUN_MODEL = "qwen3.5-plus"  # 如果此模型不支持图像，请修改为 qwen3-vl-plus 或 qwen-vl-plus

# 截图保存路径
SCREENSHOT_DIR = "./screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ==================== 辅助函数 ====================

def take_screenshot(filename=None):
    """截取当前屏幕，返回 PIL Image 对象，并可选保存文件。"""
    logger.info("正在截取屏幕...")
    screenshot = pyautogui.screenshot()
    if filename:
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        screenshot.save(filepath)
        logger.info(f"截图已保存: {filepath}")
    else:
        logger.debug("截图未保存文件")
    return screenshot

def encode_image_to_base64(image):
    """将 PIL Image 转换为 base64 字符串。"""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    logger.debug(f"图片 base64 长度: {len(encoded)} 字符")
    return encoded

def call_aliyun_vision(prompt, image):
    """
    调用阿里云视觉模型（兼容 OpenAI 格式）。
    返回模型的文本回答。
    """
    logger.info("=" * 50)
    logger.info("调用阿里云视觉模型")
    logger.info(f"模型: {ALIYUN_MODEL}")
    logger.info(f"提示词: {prompt}")
    logger.info(f"截图尺寸: {image.size}")

    base64_image = encode_image_to_base64(image)

    headers = {
        "Authorization": f"Bearer {ALIYUN_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": ALIYUN_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    }

    # 出于安全考虑，不打印完整 payload（包含 base64 超长内容），但可以打印简略信息
    logger.debug(f"请求URL: {ALIYUN_BASE_URL}")
    logger.debug(f"请求模型: {payload['model']}")

    start_time = time.time()
    try:
        response = requests.post(ALIYUN_BASE_URL, headers=headers, json=payload, timeout=30)
        elapsed = time.time() - start_time
        logger.info(f"API 响应耗时: {elapsed:.2f} 秒")
        logger.info(f"HTTP 状态码: {response.status_code}")

        response.raise_for_status()
        result = response.json()
        logger.debug(f"原始响应: {result}")

        # 兼容 OpenAI 格式的返回结构
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            content = content.strip()
            logger.info(f"模型回答: {content}")
            return content
        else:
            logger.error(f"API 返回结构异常: {result}")
            return ""
    except requests.exceptions.Timeout:
        logger.error("API 请求超时")
        return ""
    except requests.exceptions.RequestException as e:
        logger.error(f"API 请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"响应状态码: {e.response.status_code}")
            logger.error(f"响应内容: {e.response.text}")
        return ""
    except Exception as e:
        logger.error(f"调用阿里云视觉模型时发生未知错误: {e}", exc_info=True)
        return ""

def call_llm_for_coordinates(image, element_description):
    """
    发送截图给视觉模型，获取指定元素的屏幕坐标 (x, y)。
    返回整数元组 (x, y)，如果失败则返回 None。
    """
    logger.info(f"请求获取元素坐标: '{element_description}'")
    prompt = (
        f"请找出图中 '{element_description}' 的中心点坐标。"
        "只返回两个整数，格式为 x y，不要任何其他文字。"
        "屏幕"
    )
    answer = call_aliyun_vision(prompt, image)
    if not answer:
        logger.warning("模型未返回有效回答，无法解析坐标")
        return None

    # 解析坐标
    parts = answer.split()
    if len(parts) == 2:
        try:
            x = int(parts[0])
            y = int(parts[1])
            logger.info(f"解析到坐标: ({x}, {y})")
            return (x, y)
        except ValueError:
            logger.error(f"坐标值不是整数: {answer}")
            return None
    else:
        logger.error(f"坐标格式不正确（需要两个整数）: {answer}")
        return None

def call_llm_for_verification(image, question):
    """
    发送截图给视觉模型，询问一个是否问题，返回布尔值。
    """
    logger.info(f"验证问题: {question}")
    prompt = f"请根据图片回答问题：{question}。只回答“是”或“否”。"
    answer = call_aliyun_vision(prompt, image)
    if answer == "":
        logger.warning("模型未返回有效回答，验证失败")
        return False
    result = answer.strip() == "是"
    logger.info(f"验证结果: {'是' if result else '否'} (模型回答: {answer})")
    return result

# ==================== 测试主流程 ====================

def to_test_login():
    logger.info("========== 开始登录测试 ==========")

    logger.info("1. 启动天翼云电脑客户端...")
    if not os.path.exists(CLIENT_PATH):
        logger.error(f"客户端路径不存在: {CLIENT_PATH}")
        logger.info("请手动启动客户端并确保登录界面可见，然后按 Enter 继续...")
        input("按 Enter 继续...")
    else:
        if os.name == 'nt':  # Windows
            logger.info(f"启动进程: {CLIENT_PATH}")
            subprocess.Popen([CLIENT_PATH])
        else:
            # Linux/macOS 可能需要其他方式
            logger.info(f"尝试使用 open 命令启动: {CLIENT_PATH}")
            subprocess.Popen(["open", CLIENT_PATH])  # macOS 示例
        logger.info("等待 5 秒让客户端加载...")
        time.sleep(5)

    logger.info("2. 截取登录界面并获取账号输入框坐标...")
    screenshot = take_screenshot("login_screen.png")
    account_coords = call_llm_for_coordinates(screenshot, "账号输入框")
    if not account_coords:
        logger.error("无法获取账号输入框坐标，测试终止。")
        return False
    logger.info(f"账号输入框坐标: {account_coords}")

    logger.info("3. 点击账号输入框并输入账号...")
    pyautogui.click(account_coords)
    logger.info(f"已点击坐标 {account_coords}")
    username = "1897977570"  # 请替换为实际账号
    pyautogui.write(username)
    logger.info(f"已输入账号: {username}")
    time.sleep(0.5)

    logger.info("4. 获取密码输入框坐标并输入密码...")
    # 重新截图以获取最新界面（可选）
    # 如果界面未变化，也可以复用之前的截图，但为了准确，重新截图
    screenshot_pwd = take_screenshot("login_screen_for_password.png")
    password_coords = call_llm_for_coordinates(screenshot_pwd, "密码输入框")
    if not password_coords:
        logger.error("无法获取密码输入框坐标，测试终止。")
        return False
    logger.info(f"密码输入框坐标: {password_coords}")
    pyautogui.click(password_coords)
    logger.info(f"已点击坐标 {password_coords}")
    password = "liaoyun2002331!"  # 请替换为实际密码
    pyautogui.write(password)
    logger.info(f"已输入密码: {'*' * len(password)}")  # 避免明文打印密码
    time.sleep(0.5)

    logger.info("5. 获取登录按钮坐标并点击...")
    login_button_coords = call_llm_for_coordinates(screenshot_pwd, "登录按钮")
    if not login_button_coords:
        logger.error("无法获取登录按钮坐标，测试终止。")
        return False
    logger.info(f"登录按钮坐标: {login_button_coords}")
    pyautogui.click(login_button_coords)
    logger.info("已点击登录按钮")

    logger.info("6. 等待登录完成（10秒）...")
    time.sleep(10)

    logger.info("7. 截取桌面并验证是否登录成功...")
    desktop_screenshot = take_screenshot("desktop.png")
    success = call_llm_for_verification(
        desktop_screenshot,
        "是否成功登录并显示了桌面图标或任务栏？"
    )

    if success:
        logger.info("✅ 登录成功，桌面已加载。")
        return True
    else:
        logger.error("❌ 登录失败或桌面未正常加载。")
        return False

if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    logger.info("测试开始（将鼠标移动到屏幕左上角可紧急停止）...")
    result = to_test_login()
    logger.info(f"========== 测试结果: {'通过' if result else '失败'} ==========")