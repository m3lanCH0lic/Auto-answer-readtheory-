# Auto-answer-readtheory-

本项目是一个基于 Python 的智能自动化答题机器人，专为 [ReadTheory](https://readtheory.org/) 英语阅读理解平台设计。它结合了浏览器自动化（Selenium）、人工智能 API（讯飞星火和 HuggingFace）、文本分析等多种技术，实现了自动登录、内容抓取、智能选项分析、自动答题等全流程，极大提升刷题效率。

---

## 功能简介

- **自动化登录和答题**：使用 Selenium 自动操作 Chrome 浏览器，自动完成登录和答题流程。
- **多种智能分析方式**：
  - 讯飞星火大模型（SparkAI）自动答题
  - HuggingFace API 智能分析
  - 基于关键词的文本分析算法
- **自动统计答题与准确率**，支持多轮答题，自动进入下一题，异常自动刷新重试。
- **支持 Windows 和 macOS**，自动适配 Chrome 路径。
- **代码结构清晰，易于扩展。**

---

## 环境准备

### 1. Python 环境

建议使用 Python 3.8 及以上版本。

### 2. 安装依赖

需要以下 Python 库：

```bash
pip install selenium requests websocket-client
```

> 注：如需调用 HuggingFace 或讯飞星火 API，需提前注册相关账号并获取 API Token。

### 3. 准备 Chrome 浏览器及驱动

- 下载并安装 [Google Chrome 浏览器](https://www.google.com/chrome/)
- 下载与 Chrome 版本匹配的 [ChromeDriver](https://chromedriver.chromium.org/downloads) 并配置到环境变量或项目目录

---

## 快速开始

### 1. 克隆代码

```bash
git clone https://github.com/m3lanCH0lic/Auto-answer-readtheory-.git
cd Auto-answer-readtheory-
```

### 2. 配置 API 密钥（可选）

编辑 `Main.py`，在 `CONFIG` 字典中填入你的 API 信息：

```python
CONFIG = {
    "spark_appid": "你的讯飞星火AppID",
    "spark_api_key": "你的讯飞星火API Key",
    "spark_api_secret": "你的讯飞星火API Secret",
    "huggingface_token": "你的HuggingFace Token"
}
```

如无需AI辅助，可留空，程序将仅用关键词分析答题。

### 3. 运行脚本

```bash
python Main.py
```

### 4. 交互说明

- **输入用户名和密码**：按提示输入你的 ReadTheory 账号和密码（密码输入时不回显）。
- **输入测验数量**：可指定要自动完成的测试数量，直接回车默认为 20。
- 程序自动运行，期间会输出进度、分析方法、准确率等信息。
- 支持中断（Ctrl+C）。

---

## 主要技术说明

- **Selenium**：自动控制浏览器，模拟用户操作。
- **WebSocket**：与讯飞星火 API 实时通信，获取 AI 分析结果。
- **requests**：调用 HuggingFace API 进行远程智能分析。
- **正则与文本分析**：当 AI 不可用时，采用关键词分析算法。
- **多线程**：保证 WebSocket 通信与主流程并行。
- **异常和超时处理**：保证程序健壮性和自动恢复能力。

---

## 常见问题

1. **登录失败或答题异常？**
   - 检查用户名、密码是否正确，或网页结构是否有变。
   - 检查 Chrome 浏览器及驱动是否匹配。

2. **API 调用失败？**
   - 检查 API Key 是否有效，网络是否畅通。

3. **无法定位元素？**
   - 可能是网站前端结构变动，需适当调整 XPath。

---

## 免责声明

- 本项目仅供学习和研究自动化与 AI 技术使用，严禁用于商业用途或违反 ReadTheory 平台规则的行为。
- 使用本项目带来的账号风险请自负。

---

## 贡献与反馈

如有建议或问题，欢迎在 [GitHub Issues](https://github.com/m3lanCH0lic/Auto-answer-readtheory-/issues) 提出！

---