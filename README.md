# 语言/Language

- [中文说明](#中文说明)
- [English Instructions](#english-instructions)

---

## 中文说明

### 项目简介

本项目是一个基于 Python 的智能自动化答题机器人，专为 [ReadTheory](https://readtheory.org/) 英语阅读理解平台设计。它结合了浏览器自动化（Selenium）、人工智能 API（讯飞星火和 HuggingFace）、文本分析等多种技术，实现了自动登录、内容抓取、智能选项分析、自动答题等全流程，极大提升刷题效率。

### 功能简介

- **自动化登录和答题**：使用 Selenium 自动操作 Chrome 浏览器，自动完成登录和答题流程。
- **多种智能分析方式**：
  - 讯飞星火大模型（SparkAI）自动答题
  - HuggingFace API 智能分析
  - 基于关键词的 TF-IDF/增强文本分析算法
- **自动统计答题与准确率**，支持多轮答题，自动进入下一题，异常自动刷新重试。
- **支持 Windows 和 macOS**，自动适配 Chrome 路径和驱动。
- **代码结构清晰，易于扩展。**

### 技术栈

- Python 3.8 及以上
- Selenium（浏览器自动化）
- scikit-learn、numpy（TF-IDF 文本分析）
- websocket-client、requests（API 通信）
- 多线程、正则分析等

### 环境准备

1. **安装 Python 3.8 及以上版本**

2. **安装依赖库**
   ```bash
   pip install selenium scikit-learn numpy websocket-client requests
   ```

3. **安装 Chrome 浏览器及 ChromeDriver**
   - [下载 Chrome 浏览器](https://www.google.com/chrome/)
   - [下载与浏览器版本匹配的 ChromeDriver](https://chromedriver.chromium.org/downloads)
   - 将 chromedriver 加到系统 PATH 或与 Main.py 同目录

4. **（可选）申请 AI API 密钥**
   - [讯飞星火开放平台](https://www.xfyun.cn/)
   - [HuggingFace Token](https://huggingface.co/settings/tokens)
   - 在 `CONFIG` 字典中填写对应信息

### 快速开始

1. **克隆代码**
   ```bash
   git clone https://github.com/m3lanCH0lic/Auto-answer-readtheory-.git
   cd Auto-answer-readtheory-
   ```

2. **配置 API 密钥（可选）**
   编辑 `Main.py`，在 `CONFIG` 字典中填写你的 API 信息：

   ```python
   CONFIG = {
       "spark_appid": "你的讯飞星火AppID",
       "spark_api_key": "你的讯飞星火API Key",
       "spark_api_secret": "你的讯飞星火API Secret",
       "huggingface_token": "你的HuggingFace Token"
   }
   ```

   如无需 AI 辅助，可留空，程序将仅用关键词分析答题。

3. **运行脚本**
   ```bash
   python Main.py
   ```

4. **按提示操作**
   - 输入 ReadTheory 用户名、密码
   - 输入测验数量（回车默认为 20）
   - 程序自动完成后输出统计信息

---

## English Instructions

### Project Overview

This project is a Python-based smart auto-answer bot for the [ReadTheory](https://readtheory.org/) English reading platform. It combines browser automation (Selenium), AI APIs (SparkAI, HuggingFace), and text analysis techniques to automate login, content extraction, smart answer analysis, and answer submission—greatly improving quiz efficiency.

### Features

- **Auto login and answering**: Uses Selenium to control Chrome for automated login and answering.
- **Multiple smart analysis modes**:
  - SparkAI (iFlytek) large model answering
  - HuggingFace API smart analysis
  - Keyword and TF-IDF/enhanced text analysis
- **Automatic quiz statistics and accuracy**, supports multi-round quiz, auto next/refresh/retry.
- **Supports Windows and macOS**, with chrome binary path auto-detection.
- **Clear code structure, easy for extension.**

### Tech Stack

- Python 3.8+
- Selenium (browser automation)
- scikit-learn, numpy (TF-IDF text analysis)
- websocket-client, requests (API communication)
- Multithreading, regex, etc.

### Prerequisites

1. **Install Python 3.8+**

2. **Install dependencies**
   ```bash
   pip install selenium scikit-learn numpy websocket-client requests
   ```

3. **Install Chrome browser and ChromeDriver**
   - [Download Chrome browser](https://www.google.com/chrome/)
   - [Download the matching ChromeDriver](https://chromedriver.chromium.org/downloads)
   - Place chromedriver in system PATH or in the same directory as Main.py

4. **(Optional) Acquire AI API Keys**
   - [SparkAI (iFlytek) Open Platform](https://www.xfyun.cn/)
   - [HuggingFace Token](https://huggingface.co/settings/tokens)
   - Fill in the `CONFIG` dictionary in Main.py

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/m3lanCH0lic/Auto-answer-readtheory-.git
   cd Auto-answer-readtheory-
   ```

2. **Configure API Keys (optional)**
   Edit `Main.py`, fill your API keys in the `CONFIG` dictionary:

   ```python
   CONFIG = {
       "spark_appid": "your SparkAI AppID",
       "spark_api_key": "your SparkAI API Key",
       "spark_api_secret": "your SparkAI API Secret",
       "huggingface_token": "your HuggingFace Token"
   }
   ```

   Leave blank to use only the keyword analysis method.

3. **Run the script**
   ```bash
   python Main.py
   ```

4. **Follow the prompts**
   - Enter your ReadTheory username and password
   - Enter number of quizzes (default 20)
   - The program will run automatically and output statistics

---

## FAQ

1. **Login or answering fails?**
   - Double-check username/password and site structure.
   - Ensure Chrome and ChromeDriver are matched.

2. **API call fails?**
   - Check API keys and network connectivity.

3. **Element not found?**
   - The ReadTheory website may have changed—adjust XPath in the code if needed.

---

## Disclaimer

- For research, study, and non-commercial use only.
- Do not use against ReadTheory's TOS. Account risks are your own responsibility.

---

## Feedback & Contribution

Feel free to submit issues or suggestions via [GitHub Issues](https://github.com/m3lanCH0lic/Auto-answer-readtheory-/issues)!

---
