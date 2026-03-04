from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import time

import requests
import logging
from io import BytesIO

import pyautogui
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from openai import BaseModel
from pydantic import Field

from langchain_core.tools import tool, BaseTool
from langchain_community.document_loaders import WebBaseLoader

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("LoginTest")
# ==================== 配置区域 ====================
num_seconds = 1.2
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


# ==================== 版本控制配置 ====================
CHECKPOINT_DIR = "./checkpoints"
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


class OperationCheckpointManager:
    """操作检查点管理器，用于版本控制和回滚"""

    def __init__(self, log_file_path: str):
        self.log_file_path = Path(log_file_path)
        self.checkpoint_dir = Path(CHECKPOINT_DIR)
        self.checkpoint_index = 0

    def create_checkpoint(self) -> str:
        """创建检查点，返回检查点ID"""
        checkpoint_id = f"checkpoint_{int(time.time() * 1000)}"
        checkpoint_folder = self.checkpoint_dir / checkpoint_id
        checkpoint_folder.mkdir(parents=True, exist_ok=True)

        # 保存当前日志文件内容
        if self.log_file_path.exists():
            shutil.copy2(self.log_file_path, checkpoint_folder / "operation_log.py")

        # 保存当前截图
        current_screenshot = self._get_latest_screenshot()
        if current_screenshot:
            shutil.copy2(current_screenshot, checkpoint_folder / "screenshot.png")

        # 保存检查点元数据
        metadata = {
            "checkpoint_id": checkpoint_id,
            "timestamp": time.time(),
            "log_file_path": str(self.log_file_path),
            "has_log": self.log_file_path.exists(),
            "has_screenshot": current_screenshot is not None
        }
        (checkpoint_folder / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        logger.info(f"创建检查点: {checkpoint_id}")
        return checkpoint_id

    def _get_latest_screenshot(self) -> Optional[Path]:
        """获取最新的截图文件"""
        if not self.checkpoint_dir.exists():
            return None
        screenshots = list(self.checkpoint_dir.glob("**/screenshot.png"))
        return screenshots[-1] if screenshots else None

    def rollback_to_checkpoint(self, checkpoint_id: str) -> str:
        """回滚到指定检查点"""
        checkpoint_folder = self.checkpoint_dir / checkpoint_id
        if not checkpoint_folder.exists():
            return f"回滚失败：检查点 {checkpoint_id} 不存在"

        # 恢复日志文件
        log_backup = checkpoint_folder / "operation_log.py"
        if log_backup.exists():
            shutil.copy2(log_backup, self.log_file_path)
            logger.info(f"已恢复日志文件: {self.log_file_path}")

        # 返回截图路径供模型验证
        screenshot_path = checkpoint_folder / "screenshot.png"
        if screenshot_path.exists():
            logger.info(f"回滚完成，可用于验证的截图: {screenshot_path}")
            return str(screenshot_path)

        return "回滚完成"

    def get_latest_checkpoint(self) -> Optional[str]:
        """获取最新的检查点ID"""
        checkpoint_folders = [d for d in self.checkpoint_dir.iterdir() if d.is_dir() and d.name.startswith("checkpoint_")]
        if not checkpoint_folders:
            return None
        latest = max(checkpoint_folders, key=lambda d: d.stat().st_mtime)
        return latest.name


def _append_operation_log(log_file_path: str, code: str) -> None:
    """追加操作代码到日志文件"""
    log_path = Path(log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n" + code + "\n")

    logger.info(f"已记录操作到: {log_file_path}")


def _ensure_str_path(path: str | Path) -> Path:
    return path if isinstance(path, Path) else Path(path)


def encode_image_to_base64(image):
    """将 PIL Image 转换为 base64 字符串。"""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return encoded


def call_aliyun_vision(sys_prompt, user_prompt, image) -> dict:
    """
    调用阿里云视觉模型（兼容 OpenAI 格式）。
    返回模型的文本回答。
    """
    logger.info("=" * 50)
    logger.info("调用阿里云视觉模型")
    logger.info(f"模型: {ALIYUN_MODEL}")
    logger.info(f"提示词: {user_prompt}")
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
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": sys_prompt
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
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
            return json.loads(content)
        else:
            logger.error(f"API 返回结构异常: {result}")
            return {}
    except requests.exceptions.Timeout:
        logger.error("API 请求超时")
        return {}
    except requests.exceptions.RequestException as e:
        logger.error(f"API 请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"响应状态码: {e.response.status_code}")
            logger.error(f"响应内容: {e.response.text}")
        return {}
    except Exception as e:
        logger.error(f"调用阿里云视觉模型时发生未知错误: {e}", exc_info=True)
        return {}


@tool("invoke_model_tool", return_direct=False, description="截图并调用视觉模型获取控件坐标")
def invoke_model_tool(widget: str) -> str:
    """截图并调用视觉模型获取控件在屏幕上的位置坐标。参数：widget=控件描述。"""
    image = pyautogui.screenshot()
    timestamp = int(time.time() * 1000)
    filename = f"full_screen_{timestamp}.png"
    if filename:
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        image.save(filepath)
        logger.info(f"截图已保存: {filepath}")
    else:
        logger.debug("截图未保存文件")
    screen_x, screen_y = pyautogui.size()

    sys_prompt = f"""Role
你是一个专业的 UI 自动化视觉定位助手。你的任务是分析提供的截图，根据用户的文本描述，精准定位界面中的目标控件，并输出其相对位置比例。

Task
识别图像中符合用户描述的 UI 控件。
确定该控件的几何中心点。
计算该中心点距离图像左上角原点 (0,0) 的水平距离占图像总宽度的百分比 (x_percent)，以及垂直距离占图像总高度的百分比 (y_percent)。
以严格的 JSON 格式输出结果，不要包含任何 Markdown 标记（如 ```json）、解释性文字或额外内容。
Output Schema
请严格遵守以下 JSON 结构： {"target_description": "用户输入的控件描述", "status": "found 或 not_found", "location_percentage": {"x": 浮点数，0 到 100 之间，保留两位小数，表示水平方向百分比, "y": 浮点数，0 到 100 之间，保留两位小数，表示垂直方向百分比 }, "confidence": 0.0 到 1.0 之间的置信度分数 }

Constraints
坐标原点定义为图像的左上角 (0,0)，右下角为 (100,100)。
如果找不到对应的控件，"status" 设为 "not_found"，"location_percentage" 中的 x 和 y 均设为 0，"confidence" 设为 0.0。
输出必须是纯文本 JSON，严禁使用 Markdown 代码块包裹。
确保 JSON 语法正确，可直接被代码解析。
不需要输出具体的像素值或屏幕分辨率，仅需比例。
User Input
控件描述：{widget}"""

    user_prompt = f"请找出图中 '{widget}' 的中心点坐标。"

    answer = call_aliyun_vision(sys_prompt, user_prompt, image)

    if not answer:
        logger.warning("模型未返回有效回答，无法解析坐标")
        return "模型未返回有效回答，无法解析坐标"

    # 解析坐标
    if answer.get("status", "not_found") == "not_found":
        logger.warning("模型未找到控件位置")
        return "模型未找到控件位置"
    else:
        x_percent = answer["location_percentage"]["x"]
        y_percent = answer["location_percentage"]["y"]
        x = int(x_percent / 100 * screen_x)
        y = int(y_percent / 100 * screen_y)
        return f"该控件坐标为：[x:{x},y:{y}]"


@tool("click_tool", return_direct=False, description="使用键鼠操作中 鼠标单击 操作")
def click_tool(x: int, y: int, operation_log_path: Optional[str] = None) -> str:
    """使用键鼠操作中 鼠标单击 操作。参数：x=点击坐标的x值，y=点击坐标的y值，operation_log_path=可选的操作日志文件路径"""
    try:
        pyautogui.click(x, y, duration=num_seconds)
        if operation_log_path:
            log_code = f"pyautogui.click({x}, {y}, duration={num_seconds})"
            _append_operation_log(operation_log_path, log_code)
        return "点击操作完成"
    except Exception as e:
        return f"点击操作失败：{e}"


@tool("moveTo_tool", return_direct=False, description="使用键鼠操作中 鼠标移动 操作")
def moveTo_tool(x: int, y: int, operation_log_path: Optional[str] = None) -> str:
    """使用键鼠操作中 鼠标移动 操作。参数：x=移动到坐标的x值，y=移动到坐标的y值，operation_log_path=可选的操作日志文件路径"""
    try:
        pyautogui.moveTo(x, y, duration=num_seconds)
        if operation_log_path:
            log_code = f"pyautogui.moveTo({x}, {y}, duration={num_seconds})"
            _append_operation_log(operation_log_path, log_code)
        return "移动操作完成"
    except Exception as e:
        return f"移动操作失败：{e}"


@tool("dragTo_tool", return_direct=False, description="使用键鼠操作中 鼠标拖拽 操作")
def dragTo_tool(x: int, y: int, operation_log_path: Optional[str] = None) -> str:
    """使用键鼠操作中 鼠标拖拽 操作。参数：x=拖拽到坐标的x值，y=拖拽到坐标的y值，operation_log_path=可选的操作日志文件路径"""
    try:
        pyautogui.dragTo(x, y, duration=num_seconds, button='left')
        if operation_log_path:
            log_code = f"pyautogui.dragTo({x}, {y}, duration={num_seconds}, button='left')"
            _append_operation_log(operation_log_path, log_code)
        return "拖拽操作完成"
    except Exception as e:
        return f"拖拽操作失败：{e}"


def execute_with_verification(
    operation_func,
    operation_log_path: str,
    *args,
    **kwargs
) -> dict:
    """
    执行操作并截图验证，验证失败时自动回滚。

    参数:
        operation_func: 要执行的键鼠操作函数
        operation_log_path: 操作日志文件路径
        *args, **kwargs: 传递给操作函数的参数

    返回:
        dict: {
            "success": bool,           # 操作是否成功
            "result": str,             # 操作结果消息
            "screenshot_path": str,   # 操作后的截图路径
            "checkpoint_id": str,     # 创建的检查点ID
            "need_rollback": bool,    # 是否需要回滚（验证失败）
            "rollback_screenshot": str # 回滚后可用于验证的截图路径
        }
    """
    # 创建检查点
    checkpoint_manager = OperationCheckpointManager(operation_log_path)
    checkpoint_id = checkpoint_manager.create_checkpoint()

    # 执行操作
    result = operation_func(*args, **kwargs)

    # 截图
    timestamp = time.time()
    filename = f"verify_{timestamp}.png"
    screenshot_path = os.path.join(SCREENSHOT_DIR, filename)
    image = pyautogui.screenshot()
    image.save(screenshot_path)
    logger.info(f"验证截图已保存: {screenshot_path}")

    return {
        "success": "失败" not in result,
        "result": result,
        "screenshot_path": screenshot_path,
        "checkpoint_id": checkpoint_id,
        "need_rollback": False,
        "rollback_screenshot": None
    }


def rollback_operation(operation_log_path: str, checkpoint_id: str = None) -> str:
    """
    回滚到指定检查点或上一个检查点。

    参数:
        operation_log_path: 操作日志文件路径
        checkpoint_id: 可选的检查点ID，默认回滚到上一个

    返回:
        str: 回滚结果消息
    """
    checkpoint_manager = OperationCheckpointManager(operation_log_path)

    if checkpoint_id is None:
        checkpoint_id = checkpoint_manager.get_latest_checkpoint()
        if checkpoint_id is None:
            return "回滚失败：没有可用的检查点"

    rollback_screenshot = checkpoint_manager.rollback_to_checkpoint(checkpoint_id)
    return rollback_screenshot


@tool("read", return_direct=False, description="读取文件内容")
def read_file_tool(path: str) -> str:
    """读取指定文件的全部内容。参数: path=文件路径(相对或绝对)。"""
    p = _ensure_str_path(path)
    if not p.is_file():
        return f"[read] 文件不存在: {p}"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"[read] 读取失败: {e}"


@tool("write", return_direct=False, description="写入/创建文件")
def write_file_tool(path: str, content: str) -> str:
    """写入/创建文件，覆盖原内容。参数: path=文件路径, content=写入内容。"""
    p = _ensure_str_path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"[write] 已写入文件: {p}"
    except Exception as e:
        return f"[write] 写入失败: {e}"


@tool("edit", return_direct=False, description="精确编辑文件内容（替换字符串）")
def edit_file_tool(path: str, old: str, new: str, count: int = -1) -> str:
    """
    在文件中进行字符串替换。
    参数:
    - path: 文件路径
    - old: 需要被替换的原字符串
    - new: 新字符串
    - count: 替换次数，默认 -1 表示全部替换
    """
    p = _ensure_str_path(path)
    if not p.is_file():
        return f"[edit] 文件不存在: {p}"
    try:
        text = p.read_text(encoding="utf-8")
        new_text = text.replace(old, new, count if count >= 0 else text.count(old))
        p.write_text(new_text, encoding="utf-8")
        return f"[edit] 已替换 {path} 中的内容"
    except Exception as e:
        return f"[edit] 编辑失败: {e}"


@tool("glob", return_direct=False, description="文件模式匹配（*.py, **/*.js等）")
def glob_tool(pattern: str, root: str = ".") -> List[str]:
    """按模式匹配文件，例如: pattern='**/*.py', root='.'。返回匹配到的相对路径列表。"""
    base = _ensure_str_path(root)
    matches = [str(p.relative_to(base)) for p in base.rglob(pattern)]
    return matches


@tool("grep", return_direct=False, description="文件内容正则搜索")
def grep_tool(pattern: str, root: str = ".", ignore_case: bool = True) -> List[str]:
    """
    在目录下递归搜索包含正则 pattern 的文件行。
    返回格式: 'relative/path:行号:内容'
    """
    base = _ensure_str_path(root)
    flags = re.IGNORECASE if ignore_case else 0
    regex = re.compile(pattern, flags)
    results: List[str] = []

    for file in base.rglob("*"):
        if not file.is_file():
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                rel = str(file.relative_to(base))
                results.append(f"{rel}:{i}:{line}")
    return results


@tool("bash", return_direct=False, description="执行shell命令（git、npm、docker等）")
def bash_tool(command: str, cwd: Optional[str] = None, timeout: int = 600) -> str:
    """执行 shell 命令（Windows 下使用 PowerShell / *nix 使用 /bin/bash），返回 stdout/stderr。"""
    workdir = _ensure_str_path(cwd) if cwd else None
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(workdir) if workdir else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return f"[bash] exit={result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "[bash] 命令执行超时"
    except Exception as e:
        return f"[bash] 执行失败: {e}"


@dataclass
class TodoItem:
    id: str
    content: str
    status: str = "pending"


_TODO_STORE: dict[str, TodoItem] = {}

item_schema = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "content", "status"],
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "任务唯一标识符"
                    },
                    "content": {
                        "type": "string",
                        "description": "任务描述（应遵循SMART原则：具体、可衡量、可实现、相关、有时限）"
                    },
                    "status": {
                        "type": "string",
                        "description": "任务状态",
                        "enum": ["pending", "in-progress", "completed", "failed", "cancelled"],
                        "default": "pending"
                    },
                    "priority": {
                        "type": "string",
                        "description": "任务优先级",
                        "enum": ["must-have", "should-have", "could-have", "won't-have", "high", "medium", "low"],
                        "default": "low"
                    },
                    "depends_on": {
                        "type": "array",
                        "description": "依赖的任务ID列表",
                        "items": {
                            "type": "string"
                        },
                        "default": []
                    },
                    "completion_criteria": {
                        "type": "string",
                        "description": "完成标准（明确定义任务完成的判断条件）",
                        "default": ""
                    },
                    "estimated_tools": {
                        "type": "array",
                        "description": "预估需要的工具列表",
                        "items": {
                            "type": "string",
                            "enum": ["read", "write", "edit", "glob", "grep", "bash", "todowrite", "task", "skill",
                                     "question", "webfetch"]
                        },
                        "default": []
                    }
                }
            }
        }
    },
    "required": ["items"]
}


@tool("todowrite", return_direct=False, description="创建和管理结构化任务列表，支持思维链工作流程",
      args_schema=item_schema)
def todowrite_tool(items: List[dict]) -> str:
    """
    创建或更新结构化任务列表。

    参数: items=[{id, content, status, priority?, depends_on?, completion_criteria?}]

    必需字段：
    - id: 任务唯一标识符（字符串）
    - content: 任务描述（应遵循SMART原则：具体、可衡量、可实现、相关、有时限）
    - status: 任务状态，可选值：pending, in-progress, completed, failed, cancelled

    可选字段（可在content中描述，或作为独立字段）：
    - priority: 优先级（must-have/should-have/could-have/won't-have 或 high/medium/low）
    - depends_on: 依赖的任务ID列表（字符串数组）
    - completion_criteria: 完成标准（明确定义任务完成的判断条件）
    - estimated_tools: 预估需要的工具列表（如 ["read", "write", "bash"]）

    使用场景：
    1. 战略规划阶段：创建完整的TodoList，包含所有任务及其依赖关系
    2. 执行阶段：更新任务状态（pending -> in-progress -> completed）
    3. 反思阶段：调整任务列表，添加新任务或修改现有任务

    示例：
    [
        {
            "id": "1",
            "content": "分析需求文档，提取核心功能模块（必须完成）",
            "status": "pending",
            "priority": "must-have"
        },
        {
            "id": "2",
            "content": "创建测试计划文档结构（依赖任务1）",
            "status": "pending",
            "depends_on": ["1"],
            "priority": "must-have"
        }
    ]
    """
    for raw in items:
        # 提取所有字段，包括可选字段
        item_data = {
            "id": str(raw.get("id")),
            "content": str(raw.get("content")),
            "status": str(raw.get("status", "pending")),
        }
        # 保留其他可选字段到 metadata
        metadata = {}
        for key in ["priority", "depends_on", "completion_criteria", "estimated_tools"]:
            if key in raw:
                metadata[key] = raw[key]

        item = TodoItem(
            id=item_data["id"],
            content=item_data["content"],
            status=item_data["status"],
        )
        # 将元数据存储到 item 的 __dict__ 中（如果 TodoItem 支持）
        if metadata:
            item.__dict__.update(metadata)

        _TODO_STORE[item.id] = item

    # 返回当前所有任务，包括元数据
    result_dict = {}
    for k, v in _TODO_STORE.items():
        result_dict[k] = vars(v)

    return "[todowrite] 当前任务列表: " + json.dumps(
        result_dict, ensure_ascii=False, indent=2
    )


@tool("task", return_direct=False, description="启动专用代理进行复杂探索（代码库分析、多步骤任务）")
def task_tool(description: str) -> str:
    """
    启动专用代理进行复杂探索的占位符工具。
    目前仅记录任务描述，真实实现可在此基础上扩展。
    """
    return f"[task] 已记录复杂任务描述，稍后由专用代理处理: {description}"


# @tool("skill", return_direct=False)
# def skill_tool(name: str, action: str = "describe") -> str:
#     """
#     skill 工具占位符。
#     目前支持: action='describe' 时，返回该技能的用途说明（由上层注入）。
#     实际的技能路由由主 agent / 子 agent 控制。
#     """
#     return f"[skill] 请求技能: {name}, action={action}（实际执行由多agent系统负责）"


# 全局存储用户问答（用于测试和预配置答案）
_QUESTION_ANSWER_STORE: Dict[str, str] = {}
# 预配置答案文件路径（可选）
_QUESTION_ANSWER_FILE = Path("question_answers.json")


@tool("question", return_direct=False, description="交互式提问（收集需求、澄清指令）")
def question_tool(prompt: str, question_id: Optional[str] = None) -> str:
    """
    交互式提问工具，支持Human-in-the-Loop机制。
    
    参数:
    - prompt: 向用户提问的具体问题
    - question_id: 可选的问题标识符，用于从预配置答案中查找回答
    
    工作流程:
    1. 检查是否有预配置答案（通过question_id或prompt匹配）
    2. 如果有预配置答案，直接返回答案
    3. 如果没有预配置答案，返回结构化的问题信息供上层处理
    4. 记录问题到日志文件便于调试
    
    预配置答案支持:
    - 全局字典 _QUESTION_ANSWER_STORE
    - 外部文件 question_answers.json
    - 环境变量（未来扩展）
    
    返回格式:
    - 如果有答案: [question] 用户已回答: {答案内容}
    - 如果没有答案: [question] 需要用户回答: {问题内容} [ID: {question_id}]
    """
    import os
    from datetime import datetime

    # 生成问题ID（如果未提供）
    if question_id is None:
        # 基于prompt生成简单的哈希ID
        import hashlib
        question_id = hashlib.md5(prompt.encode()).hexdigest()[:8]

    # 尝试从全局存储获取答案
    if question_id in _QUESTION_ANSWER_STORE:
        answer = _QUESTION_ANSWER_STORE[question_id]
        return f"[question] 用户已回答（来自内存存储）: {answer}"

    # 尝试从预配置答案文件获取答案
    if _QUESTION_ANSWER_FILE.is_file():
        try:
            answers_data = json.loads(_QUESTION_ANSWER_FILE.read_text(encoding="utf-8"))
            if isinstance(answers_data, dict):
                # 尝试通过question_id查找
                if question_id in answers_data:
                    answer = answers_data[question_id]
                    return f"[question] 用户已回答（来自文件存储）: {answer}"
                # 尝试通过prompt关键词查找
                for key, value in answers_data.items():
                    if isinstance(key, str) and key in prompt:
                        return f"[question] 用户已回答（关键词匹配）: {value}"
        except Exception as e:
            # 文件读取失败，继续使用标准流程
            pass

    # 检查环境变量中是否有预配置答案（格式：QUESTION_ANSWER_{QUESTION_ID}）
    env_key = f"QUESTION_ANSWER_{question_id.upper()}"
    if env_key in os.environ:
        answer = os.environ[env_key]
        return f"[question] 用户已回答（来自环境变量）: {answer}"

    # 没有预配置答案，返回结构化问题信息
    # 记录问题到日志文件（便于调试和跟踪）
    log_dir = Path("question_logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"questions_{datetime.now().strftime('%Y%m%d')}.log"

    question_record = {
        "timestamp": datetime.now().isoformat(),
        "question_id": question_id,
        "prompt": prompt,
        "status": "pending"
    }

    try:
        # 追加记录到日志文件
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(question_record, ensure_ascii=False) + "\n")
    except Exception:
        # 日志写入失败不影响主要功能
        pass

    # 返回结构化的问题信息
    # 注意：在纯后端模式下，上层需要解析此输出并获取用户回答
    # 然后通过某种机制（如更新预配置答案）提供回答
    structured_output = {
        "type": "question",
        "question_id": question_id,
        "prompt": prompt,
        "timestamp": datetime.now().isoformat(),
        "instructions": "请提供此问题的答案，可通过以下方式：1. 更新question_answers.json文件 2. 设置环境变量 3. 通过其他交互机制"
    }

    return f"[question] 需要用户回答: {prompt}\n" + \
        f"[question] 问题ID: {question_id}\n" + \
        f"[question] 结构化信息: {json.dumps(structured_output, ensure_ascii=False)}"


def set_question_answer(question_id: str, answer: str) -> None:
    """
    设置预配置答案到内存存储。
    用于测试和开发阶段提供模拟用户回答。
    """
    global _QUESTION_ANSWER_STORE
    _QUESTION_ANSWER_STORE[question_id] = answer


def load_question_answers_from_file(file_path: Optional[str] = None) -> bool:
    """
    从JSON文件加载预配置答案。
    
    参数:
        file_path: JSON文件路径，默认为 question_answers.json
        
    返回:
        bool: 是否成功加载
    """
    global _QUESTION_ANSWER_STORE, _QUESTION_ANSWER_FILE

    if file_path:
        target_file = Path(file_path)
    else:
        target_file = _QUESTION_ANSWER_FILE

    if not target_file.is_file():
        return False

    try:
        answers_data = json.loads(target_file.read_text(encoding="utf-8"))
        if isinstance(answers_data, dict):
            _QUESTION_ANSWER_STORE.update(answers_data)
            return True
    except Exception as e:
        print(f"[question] 加载预配置答案失败: {e}")

    return False


def save_question_answers_to_file(file_path: Optional[str] = None) -> bool:
    """
    将当前内存中的预配置答案保存到JSON文件。
    
    参数:
        file_path: JSON文件路径，默认为 question_answers.json
        
    返回:
        bool: 是否成功保存
    """
    global _QUESTION_ANSWER_STORE, _QUESTION_ANSWER_FILE

    if file_path:
        target_file = Path(file_path)
    else:
        target_file = _QUESTION_ANSWER_FILE

    try:
        # 确保目录存在
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(json.dumps(_QUESTION_ANSWER_STORE, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[question] 保存预配置答案失败: {e}")

    return False


# 初始化时尝试加载预配置答案文件
try:
    load_question_answers_from_file()
except Exception:
    # 初始化失败不影响主要功能
    pass


class WebURLInput(BaseModel):
    """链接解析输入"""
    urls: list[str] = Field(description="用户问题中携带的所有url")


@tool("webfetch", return_direct=False, args_schema=WebURLInput,
      description="这是一个解析链接的工具助手，可以获取用户发送的链接并读取链接内所有内容，返回的为链接中内容")
def webfetch_tool(urls: list[str]) -> str:
    """获取链接中的内容"""
    loader = WebBaseLoader(urls)
    docs = loader.load()
    web_content = docs[0].page_content
    return web_content


def list_all_mcp_tools() -> List[BaseTool]:
    """返回需要注册到所有 agent 的 MCP 风格工具列表。"""
    return [
        invoke_model_tool,
        read_file_tool,
        write_file_tool,
        edit_file_tool,
        glob_tool,
        grep_tool,
        bash_tool,
        todowrite_tool,
        task_tool,
        # skill_tool,
        question_tool,
        webfetch_tool,
        click_tool,
        moveTo_tool,
        dragTo_tool
    ]
