# Allure 测试报告指南

## Allure 简介

Allure 是一个灵活的轻量级测试报告工具，支持多种测试框架（pytest, JUnit, TestNG, Cucumber 等）。它提供了美观的 HTML 报告，包含丰富的测试执行详情。

## 安装 Allure

### Windows
1. 使用 Scoop:
   ```powershell
   scoop install allure
   ```

2. 手动安装:
   - 下载 Allure 命令行工具: https://github.com/allure-framework/allure2/releases
   - 解压到 `C:\Program Files\Allure`
   - 将 `bin` 目录添加到系统 PATH

### macOS
```bash
brew install allure
```

### Linux
```bash
# Ubuntu/Debian
sudo apt-add-repository ppa:qameta/allure
sudo apt-get update
sudo apt-get install allure

# 或使用 Snap
sudo snap install allure
```

## 基本用法

### 1. 生成测试结果
使用测试框架生成 Allure 兼容的结果文件：

```bash
# pytest
pytest --alluredir=allure-results

# JUnit
mvn test -Dallure.results.directory=allure-results

# TestNG
# 在 testng.xml 中配置 Allure 监听器
```

### 2. 生成 HTML 报告
```bash
allure generate allure-results -o allure-report --clean
```

### 3. 查看报告
```bash
# 打开报告（默认浏览器）
allure open allure-report

# 或启动本地服务器
allure serve allure-results
```

## 与测试框架集成

### pytest
1. 安装 allure-pytest:
   ```bash
   pip install allure-pytest
   ```

2. 运行测试:
   ```bash
   pytest --alluredir=allure-results
   ```

3. 配置 pytest.ini:
   ```ini
   [pytest]
   addopts = --alluredir=allure-results
   ```

### JUnit 5
1. 添加依赖:
   ```xml
   <dependency>
       <groupId>io.qameta.allure</groupId>
       <artifactId>allure-junit5</artifactId>
       <version>2.27.0</version>
   </dependency>
   ```

2. 配置 surefire 插件:
   ```xml
   <plugin>
       <groupId>org.apache.maven.plugins</groupId>
       <artifactId>maven-surefire-plugin</artifactId>
       <version>3.0.0-M5</version>
       <configuration>
           <argLine>
               -javaagent:"${settings.localRepository}/org/aspectj/aspectjweaver/${aspectj.version}/aspectjweaver-${aspectj.version}.jar"
           </argLine>
       </configuration>
   </plugin>
   ```

### TestNG
1. 添加依赖:
   ```xml
   <dependency>
       <groupId>io.qameta.allure</groupId>
       <artifactId>allure-testng</artifactId>
       <version>2.27.0</version>
   </dependency>
   ```

2. 配置 testng.xml:
   ```xml
   <listeners>
       <listener class-name="io.qameta.allure.testng.AllureTestNg" />
   </listeners>
   ```

## Allure 报告结构

### 结果目录 (`allure-results/`)
- `*.json` - 测试结果数据
- `*-attachment.*` - 测试附件（截图、日志等）
- `categories.json` - 自定义分类
- `environment.properties` - 环境变量

### 报告目录 (`allure-report/`)
- `index.html` - 报告主页
- `widgets/` - 图表和小部件数据
- `data/` - 原始测试数据
- `plugins/` - 报告插件

## 高级功能

### 添加测试步骤
```python
import allure

@allure.step("登录系统")
def login(username, password):
    # 登录逻辑
    pass

@allure.step("验证用户信息")
def verify_user_info(user):
    # 验证逻辑
    pass
```

### 添加附件
```python
import allure

# 添加文本附件
allure.attach("这是日志内容", name="log.txt", attachment_type=allure.attachment_type.TEXT)

# 添加图片附件
with open("screenshot.png", "rb") as f:
    allure.attach(f.read(), name="screenshot", attachment_type=allure.attachment_type.PNG)
```

### 添加测试描述
```python
@allure.description("""
这是一个详细的测试描述。
可以包含多行文本。
""")
def test_example():
    pass
```

### 添加严重级别
```python
@allure.severity(allure.severity_level.CRITICAL)
def test_critical_feature():
    pass
```

## 环境配置

### 环境变量文件
创建 `environment.properties` 文件：
```properties
OS=Windows 10
Browser=Chrome 120
Python=3.11
Allure=2.27.0
```

### 分类配置
创建 `categories.json` 文件：
```json
[
  {
    "name": "产品缺陷",
    "matchedStatuses": ["failed"]
  },
  {
    "name": "测试缺陷",
    "matchedStatuses": ["broken"]
  }
]
```

## 故障排除

### 常见问题

1. **Allure 命令未找到**
   - 检查 PATH 环境变量
   - 重新安装 Allure

2. **报告生成失败**
   - 确保结果目录存在且包含数据
   - 检查文件权限
   - 尝试清理旧报告：`allure generate --clean`

3. **测试结果未显示**
   - 检查测试框架是否正确配置
   - 验证 Allure 监听器是否正确加载
   - 查看是否生成了 .json 结果文件

4. **附件无法显示**
   - 检查附件路径是否正确
   - 验证附件文件权限
   - 确保使用正确的 MIME 类型

### 调试技巧

- 使用 `--verbose` 选项查看详细输出
- 检查 allure-results 目录中的 JSON 文件
- 查看测试框架的日志输出
- 验证 Allure 版本兼容性

## 最佳实践

1. **标准化结果目录**
   - 使用固定的目录名称（如 `allure-results`）
   - 在 CI/CD 流水线中保留结果文件

2. **定期清理**
   - 定期清理旧的报告目录
   - 使用 `--clean` 选项覆盖旧报告

3. **环境隔离**
   - 为不同环境生成不同的报告
   - 包含环境信息在报告中

4. **版本控制**
   - 将 Allure 配置纳入版本控制
   - 记录 Allure 版本要求

## 参考资源

- 官方文档: https://docs.qameta.io/allure/
- GitHub 仓库: https://github.com/allure-framework/allure2
- 示例项目: https://github.com/allure-examples

---

*最后更新: 2025年2月*