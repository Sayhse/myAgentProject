# 测试框架指南

## 支持的测试框架

### 1. pytest (Python)
**识别特征**:
- 命令: `pytest`, `python -m pytest`
- 配置文件: `pytest.ini`, `setup.cfg`, `tox.ini`, `pyproject.toml`
- 测试文件: `test_*.py`, `*_test.py`
- 常用选项: `-v`, `--tb=short`, `-x`, `--lf`

**安装**:
```bash
pip install pytest
pip install pytest-allure  # Allure 支持
```

**运行命令**:
```bash
# 基本运行
pytest

# 生成 Allure 结果
pytest --alluredir=allure-results

# 指定测试目录
pytest tests/

# 指定测试文件
pytest tests/test_example.py

# 指定测试类
pytest tests/test_example.py::TestClass

# 指定测试方法
pytest tests/test_example.py::TestClass::test_method
```

**配置文件示例** (`pytest.ini`):
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --alluredir=allure-results
```

### 2. unittest (Python 标准库)
**识别特征**:
- 命令: `python -m unittest`
- 测试文件: `test_*.py`
- 测试类继承自 `unittest.TestCase`

**运行命令**:
```bash
# 发现并运行所有测试
python -m unittest discover

# 指定测试目录
python -m unittest discover -s tests

# 指定测试模式
python -m unittest discover -p "test_*.py"

# 运行特定测试模块
python -m unittest tests.test_example

# 运行特定测试类
python -m unittest tests.test_example.TestClass

# 运行特定测试方法
python -m unittest tests.test_example.TestClass.test_method
```

**与 Allure 集成**:
需要安装 `allure-python-commons`:
```bash
pip install allure-python-commons
```

### 3. JUnit (Java)
**识别特征**:
- 命令: `mvn test`, `gradle test`
- 配置文件: `pom.xml`, `build.gradle`
- 测试目录: `src/test/java`

**Maven 运行命令**:
```bash
# 运行所有测试
mvn test

# 跳过测试
mvn clean install -DskipTests

# 运行特定测试类
mvn test -Dtest=TestClass

# 运行特定测试方法
mvn test -Dtest=TestClass#testMethod

# 生成 Allure 结果
mvn test -Dallure.results.directory=allure-results
```

**Gradle 运行命令**:
```bash
# 运行所有测试
gradle test

# 运行特定测试类
gradle test --tests "TestClass"

# 运行特定测试方法
gradle test --tests "TestClass.testMethod"
```

### 4. Jest (JavaScript/TypeScript)
**识别特征**:
- 命令: `npm test`, `yarn test`, `jest`
- 配置文件: `jest.config.js`, `package.json`
- 测试文件: `*.test.js`, `*.spec.js`, `__tests__/*.js`

**运行命令**:
```bash
# 基本运行
npm test

# 使用 jest 直接运行
npx jest

# 监听模式
npm test -- --watch

# 覆盖率报告
npm test -- --coverage

# 指定测试文件
npm test -- tests/example.test.js
```

**与 Allure 集成**:
需要安装 `jest-allure`:
```bash
npm install jest-allure --save-dev
```

配置 `jest.config.js`:
```javascript
module.exports = {
  testRunner: "jest-jasmine2",
  setupFilesAfterEnv: ["jest-allure/dist/setup"],
  reporters: ["default", "jest-allure"]
};
```

### 5. Mocha (JavaScript)
**识别特征**:
- 命令: `npm test`, `mocha`
- 配置文件: `.mocharc.js`, `package.json`
- 测试文件: `test/*.js`

**运行命令**:
```bash
# 基本运行
npx mocha

# 指定测试目录
npx mocha test/

# 指定测试文件
npx mocha test/example.js

# 使用 Allure 报告
npx mocha --reporter mocha-allure-reporter
```

### 6. RSpec (Ruby)
**识别特征**:
- 命令: `rspec`, `bundle exec rspec`
- 测试文件: `*_spec.rb`
- 配置文件: `.rspec`

**运行命令**:
```bash
# 运行所有测试
rspec

# 运行特定文件
rspec spec/models/user_spec.rb

# 运行特定测试
rspec spec/models/user_spec.rb:25
```

## 测试命令识别模式

### 常见命令格式

1. **安装依赖**:
   - `npm install`
   - `yarn install`
   - `pip install -r requirements.txt`
   - `bundle install`
   - `mvn install`
   - `gradle build`

2. **运行测试**:
   - `pytest`
   - `python -m pytest`
   - `python -m unittest`
   - `npm test`
   - `yarn test`
   - `mvn test`
   - `gradle test`
   - `jest`
   - `rspec`

3. **清理命令**:
   - `mvn clean`
   - `gradle clean`
   - `npm run clean`
   - `rm -rf node_modules`

### 配置文件识别

**Python 项目**:
- `requirements.txt` - Python 依赖
- `setup.py` - 包配置
- `pyproject.toml` - 现代 Python 配置
- `pytest.ini` - pytest 配置

**Java 项目**:
- `pom.xml` - Maven 配置
- `build.gradle` - Gradle 配置

**JavaScript 项目**:
- `package.json` - npm 配置
- `yarn.lock` - Yarn 锁文件
- `jest.config.js` - Jest 配置

**通用配置**:
- `.gitignore` - Git 忽略文件
- `README.md` - 项目说明
- `Dockerfile` - Docker 配置

## 测试目录结构

### Python 项目
```
project/
├── src/
│   └── module/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── test_module.py
│   └── conftest.py
├── requirements.txt
└── pytest.ini
```

### Java 项目 (Maven)
```
project/
├── src/
│   ├── main/
│   │   └── java/
│   │       └── com/
│   │           └── example/
│   │               └── App.java
│   └── test/
│       └── java/
│           └── com/
│               └── example/
│                   └── AppTest.java
├── pom.xml
└── allure-results/
```

### JavaScript 项目
```
project/
├── src/
│   └── index.js
├── tests/
│   └── index.test.js
├── package.json
└── jest.config.js
```

## 错误模式识别

### pytest 错误
```
============================= FAILURES ==============================
_________________________ test_example __________________________

def test_example():
>       assert 1 == 2
E       assert 1 == 2

test_example.py:5: AssertionError
```

### JUnit 错误
```
Tests run: 1, Failures: 1, Errors: 0, Skipped: 0, Time elapsed: 0.05 sec <<< FAILURE!
testExample(com.example.TestClass)  Time elapsed: 0.05 sec  <<< FAILURE!
java.lang.AssertionError: expected:<1> but was:<2>
```

### Jest 错误
```
FAIL  tests/example.test.js
  ● Test suite failed to run

    expect(received).toBe(expected)
    
    Expected: 2
    Received: 1
```

## 自动化修复策略

### 1. 依赖缺失
- 自动安装缺失的包
- 更新 requirements.txt / package.json

### 2. 导入错误
- 添加缺失的 import 语句
- 修复模块路径

### 3. 语法错误
- 修复括号不匹配
- 修复引号不匹配
- 修复缩进错误

### 4. 断言错误
- 分析期望值和实际值
- 建议正确的断言条件

### 5. 配置错误
- 修复配置文件语法
- 更新配置选项

## 最佳实践

### 测试命名
- 使用描述性名称
- 遵循框架的命名约定
- 包含测试场景描述

### 测试组织
- 按功能模块组织测试
- 使用适当的测试夹具
- 保持测试独立

### 错误处理
- 提供清晰的错误信息
- 包含足够的调试信息
- 使用适当的断言

### 报告生成
- 定期生成测试报告
- 包含环境信息
- 归档历史报告

---

*最后更新: 2025年2月*