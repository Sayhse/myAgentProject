---
name: automated-test-runner
description: 自动化测试运行与修复工具，用于读取项目 README.md 文件，执行其中的命令，运行测试套件，自动修复测试失败，并生成 Allure 测试报告。当用户提到"运行测试"、"自动修复测试错误"、"执行项目测试"或需要自动化测试流程时使用。
---

# Automated Test Runner

## Overview

本技能自动化执行项目测试流程：读取项目根目录的 README.md 文件，解析其中的安装和测试命令，执行测试套件（支持 pytest 等框架），自动检测测试失败并修复代码，最终生成 Allure 测试报告并返回报告路径。

本技能适用于任何包含 README.md 和测试套件的项目，特别是使用 Allure 作为测试报告框架的项目。

## 工作流程

### 1. 读取 README.md
- 定位项目根目录下的 `README.md` 文件
- 解析文件内容，提取常见的安装和测试命令（如 `npm install`、`pip install -r requirements.txt`、`pytest`、`mvn test` 等）
- 识别用于生成 Allure 报告的命令（如 `pytest --alluredir=allure-results`）

### 2. 安装依赖
- 根据 README.md 中提取的安装命令，在项目目录中执行依赖安装
- 如果 README.md 中没有明确命令，尝试使用常见包管理器（如 npm、pip、maven）自动安装

### 3. 执行测试
- 运行测试命令，捕获标准输出和错误输出
- 监控测试执行过程，记录测试结果
- 如果测试失败，收集详细的错误信息（包括堆栈跟踪、断言失败详情等）

### 4. 自动修复代码
- 分析测试失败的根本原因
- 定位到有问题的源代码文件
- 自动修复常见的错误类型：
  - 语法错误
  - 导入缺失
  - 函数调用参数不匹配
  - 断言条件错误
  - 资源路径问题
- 如果自动修复失败，将错误详情和上下文提供给 Claude 模型进行智能修复

### 5. 生成测试报告
- 执行 Allure 报告生成命令（如 `allure generate allure-results -o allure-report --clean`）
- 验证报告生成成功，获取报告目录路径
- 返回 Allure 报告路径给用户

## 使用示例

### 典型请求
- "帮我运行这个项目的测试"
- "自动修复测试错误并生成报告"
- "执行项目根目录下的所有测试"

### 输入输出格式
- **输入**：项目绝对路径（如 `C:\projects\my-app`）
- **输出**：Allure 报告路径和测试结果摘要

## 脚本使用说明

本技能包含以下脚本：

- `F:/bb-study/python/FirstProduct/myAgentProject/skills/automated-test-runner/scripts/parse_readme.py` - 解析 README.md 提取命令
- `F:/bb-study/python/FirstProduct/myAgentProject/skills/automated-test-runner/scripts/run_tests.py` - 执行测试并捕获结果
- `F:/bb-study/python/FirstProduct/myAgentProject/skills/automated-test-runner/scripts/fix_errors.py` - 自动修复常见测试错误
- `F:/bb-study/python/FirstProduct/myAgentProject/skills/automated-test-runner/scripts/generate_report.py` - 生成 Allure 报告

具体用法请参考各脚本的文档说明。

## 资源文件

### F:/bb-study/python/FirstProduct/myAgentProject/skills/automated-test-runner/scripts/ 目录
包含以下自动化脚本：

- `parse_readme.py` - 解析 README.md 文件，提取安装和测试命令
- `run_tests.py` - 执行测试命令，捕获输出和错误
- `fix_errors.py` - 自动修复常见的测试错误
- `generate_report.py` - 生成 Allure 测试报告

### F:/bb-study/python/FirstProduct/myAgentProject/skills/automated-test-runner/references/ 目录
包含参考文档：

- `allure_guide.md` - Allure 测试报告配置和使用指南
- `test_frameworks.md` - 常见测试框架（pytest, unittest, jest）的识别和执行模式

### F:/bb-study/python/FirstProduct/myAgentProject/skills/automated-test-runner/assets/ 目录
包含模板文件：

- `allure_config` - Allure 配置文件模板
- `test_template` - 测试用例模板文件

**注意**：不需要的目录可以删除，但建议保留 scripts/ 目录中的核心脚本。
