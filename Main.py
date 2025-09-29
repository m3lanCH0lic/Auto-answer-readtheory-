from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementNotVisibleException, NoSuchElementException, TimeoutException, WebDriverException
import time
import random
import requests
import json
from typing import List, Tuple, Optional
import re
from collections import Counter
import websocket
import threading
import _thread as thread
from urllib.parse import urlparse, urlencode
import base64
import hashlib
import hmac
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time
import getpass
import sys
import os
import math
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

class EnhancedElementFinder:
    """增强的元素查找器，使用多种定位策略"""
    
    def __init__(self, driver, timeout=30):
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)
    
    def find_element_with_retry(self, selectors, description="元素", condition=EC.presence_of_element_located):
        """
        使用多种选择器重试查找元素
        selectors: 选择器列表，每个选择器是(by, value)元组或XPath字符串
        condition: 等待条件，默认为元素存在
        """
        for attempt in range(3):
            try:
                for selector in selectors:
                    try:
                        if isinstance(selector, tuple):
                            by, value = selector
                            element = self.wait.until(condition((by, value)))
                        else:
                            element = self.wait.until(condition((By.XPATH, selector)))
                        
                        if hasattr(element, 'is_displayed') and element.is_displayed():
                            return element
                        elif not hasattr(element, 'is_displayed'):
                            return element
                    except:
                        continue
                
                if attempt < 2:
                    time.sleep(2)
                    
            except Exception as e:
                if attempt == 2:
                    print(f"查找{description}失败: {e}")
        
        return None
    
    def find_clickable_with_retry(self, selectors, description="元素"):
        """查找可点击元素 - 复用find_element_with_retry"""
        return self.find_element_with_retry(selectors, description, EC.element_to_be_clickable)

class TFIDFAnalyzer:
    """基于TF-IDF的文本分析器"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    
    def calculate_similarity(self, article, options):
        """计算文章与选项的相似度"""
        try:
            texts = [article] + options
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            article_vector = tfidf_matrix[0]
            similarities = []
            
            for i in range(1, len(texts)):
                option_vector = tfidf_matrix[i]
                similarity = self._cosine_similarity(article_vector, option_vector)
                similarities.append(similarity)
            
            return similarities
            
        except Exception as e:
            print(f"TF-IDF分析失败: {e}")
            return self._fallback_keyword_match(article, options)
    
    def _cosine_similarity(self, vec1, vec2):
        """计算余弦相似度"""
        return (vec1 * vec2.T).toarray()[0][0] / (np.linalg.norm(vec1.toarray()) * np.linalg.norm(vec2.toarray()) + 1e-8)
    
    def _fallback_keyword_match(self, article, options):
        """回退的关键词匹配方法"""
        article_lower = article.lower()
        article_words = set(re.findall(r'\b\w+\b', article_lower))
        
        scores = []
        for option in options:
            option_lower = option.lower()
            option_words = set(re.findall(r'\b\w+\b', option_lower))
            
            intersection = len(article_words.intersection(option_words))
            union = len(article_words.union(option_words))
            similarity = intersection / union if union > 0 else 0
            
            scores.append(similarity)
        
        return scores

class BaseAIClient:
    """AI客户端的基类，提供通用功能"""
    
    def __init__(self):
        self.answer = ""
        self.answer_received = False
    
    def build_prompt(self, article: str, question: str, options: List[str]) -> str:
        """构建统一的提示词"""
        truncated_article = article[:3000]
        
        return f"""请仔细阅读以下文章并回答问题。请严格基于文章内容选择最准确的答案。

【文章内容】
{truncated_article}

【问题】
{question}

【选项】
{chr(10).join([f'{chr(65+i)}. {option}' for i, option in enumerate(options)])}

请仔细分析文章内容，选择最符合文章意思的选项。只返回选项字母（A, B, C, D, 或E），不要包含其他任何文字。"""
    
    def parse_answer(self, answer: str, options_count: int) -> int:
        """解析AI返回的答案"""
        for i in range(options_count):
            if chr(65 + i) in answer.upper():
                return i
        return -1

class SparkAI(BaseAIClient):
    """讯飞星火AI客户端"""
    
    def __init__(self, appid: str, api_key: str, api_secret: str):
        super().__init__()
        self.appid = appid
        self.api_key = api_key
        self.api_secret = api_secret
        self.url = "wss://spark-api.xf-yun.com/v3.5/chat"
        
    def create_url(self):
        """生成鉴权URL"""
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        
        signature_origin = "host: " + "spark-api.xf-yun.com" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v3.5/chat " + "HTTP/1.1"
        
        signature_sha = hmac.new(self.api_secret.encode('utf-8'), 
                                signature_origin.encode('utf-8'), 
                                digestmod=hashlib.sha256).digest()
        
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')
        
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        v = {
            "authorization": authorization,
            "date": date,
            "host": "spark-api.xf-yun.com"
        }
        return self.url + '?' + urlencode(v)

    def on_message(self, ws, message):
        """WebSocket消息接收处理"""
        data = json.loads(message)
        code = data['header']['code']
        
        if code != 0:
            print(f'请求错误: {code}, {data}')
            ws.close()
        else:
            choices = data["payload"]["choices"]
            status = choices["status"]
            content = choices["text"][0]["content"]
            self.answer += content
            print(f"星火AI回复: {content}")
            
            if status == 2:
                self.answer_received = True
                ws.close()

    def on_error(self, ws, error):
        """WebSocket错误处理"""
        print(f"WebSocket错误: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket关闭处理"""
        print("WebSocket连接关闭")

    def on_open(self, ws):
        """WebSocket连接打开处理"""
        def run(*args):
            data = {
                "header": {
                    "app_id": self.appid,
                    "uid": "readtheory_bot"
                },
                "parameter": {
                    "chat": {
                        "domain": "generalv3.5",
                        "temperature": 0.1,
                        "max_tokens": 1024
                    }
                },
                "payload": {
                    "message": {
                        "text": self.messages
                    }
                }
            }
            ws.send(json.dumps(data))
            print("已发送请求到星火AI")

        thread.start_new_thread(run, ())

    def chat_completion(self, messages: List[dict]) -> str:
        """发送聊天请求"""
        self.messages = messages
        self.answer = ""
        self.answer_received = False
        
        print("连接讯飞星火AI...")
        websocket.enableTrace(False)
        ws_url = self.create_url()
        ws = websocket.WebSocketApp(ws_url,
                                  on_message=self.on_message,
                                  on_error=self.on_error,
                                  on_close=self.on_close)
        ws.on_open = self.on_open
        
        def run_websocket():
            ws.run_forever()
        
        websocket_thread = threading.Thread(target=run_websocket)
        websocket_thread.daemon = True
        websocket_thread.start()
        
        timeout = 30
        start_time = time.time()
        while not self.answer_received and (time.time() - start_time) < timeout:
            time.sleep(0.1)
            
        if not self.answer_received:
            print("星火AI响应超时")
            
        return self.answer.strip()

class TextAnalyzer:
    """文本分析器，整合各种分析方法"""
    
    def __init__(self, huggingface_token: str = None):
        self.huggingface_token = huggingface_token
        self.tfidf_analyzer = TFIDFAnalyzer()
    
    def analyze_with_huggingface(self, article: str, question: str, options: List[str]) -> int:
        """使用Hugging Face API进行分析"""
        try:
            API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-xl"
            headers = {"Authorization": f"Bearer {self.huggingface_token}"} if self.huggingface_token else {}
            
            prompt = f"""
阅读以下文章并回答问题：

文章: {article[:800]}

问题: {question}

选项:
{chr(10).join([f'{chr(65+i)}. {opt}' for i, opt in enumerate(options)])}

基于文章内容，正确答案是选项:
"""
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 50,
                    "temperature": 0.1,
                    "do_sample": False
                }
            }
            
            print("调用Hugging Face API...")
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                answer_text = result[0]['generated_text']
                print(f"Hugging Face 分析结果: {answer_text}")
                
                return self._parse_simple_answer(answer_text, len(options))
            else:
                print(f"Hugging Face API 错误: {response.status_code}")
                
        except Exception as e:
            print(f"Hugging Face API 调用失败: {e}")
        
        return -1
    
    def analyze_with_tfidf(self, article: str, question: str, options: List[str]) -> int:
        """使用TF-IDF分析文章和选项的相似度"""
        print("使用TF-IDF分析...")
        
        try:
            similarities = self.tfidf_analyzer.calculate_similarity(article, options)
            
            for i, similarity in enumerate(similarities):
                print(f"  选项 {chr(65+i)} TF-IDF相似度: {similarity:.4f}")
            
            best_index = np.argmax(similarities)
            print(f"TF-IDF分析选择: 选项 {chr(65+best_index)}")
            return best_index
            
        except Exception as e:
            print(f"TF-IDF分析失败: {e}")
            return self.analyze_with_enhanced_keywords(article, question, options)
    
    def analyze_with_enhanced_keywords(self, article: str, question: str, options: List[str]) -> int:
        """增强的关键词分析方法"""
        print("使用增强关键词分析...")
        article_lower = article.lower()
        question_lower = question.lower()
        
        # 提取关键词，考虑词频和重要性
        words = re.findall(r'\b\w+\b', article_lower)
        word_freq = Counter([word for word in words if len(word) > 2])
        
        # 计算TF-IDF风格的权重
        total_words = len(words)
        important_words = {}
        for word, freq in word_freq.most_common(50):
            tf = freq / total_words
            important_words[word] = tf * math.log(total_words / (freq + 1))
        
        scores = []
        
        for i, option in enumerate(options):
            score = 0
            option_lower = option.lower()
            option_words = set(re.findall(r'\b\w+\b', option_lower))
            
            # 基于TF-IDF权重的关键词匹配
            for word in option_words:
                if word in important_words:
                    score += important_words[word] * 10
            
            # 考虑问题类型
            question_type = self._analyze_question_type(question_lower)
            if question_type == "detail":
                # 细节题：检查具体信息匹配
                for sentence in article_lower.split('.'):
                    sentence_words = set(re.findall(r'\b\w+\b', sentence))
                    common_words = option_words.intersection(sentence_words)
                    if len(common_words) >= 2:
                        score += len(common_words) * 3
            elif question_type == "main_idea":
                # 主旨题：关注高频词汇
                for word in option_words:
                    if word in [w for w, _ in word_freq.most_common(10)]:
                        score += 5
            
            scores.append(score)
            print(f"  选项 {chr(65+i)} 增强关键词得分: {score:.2f}")
        
        best_index = scores.index(max(scores))
        print(f"增强关键词分析选择: 选项 {chr(65+best_index)}")
        return best_index
    
    def _analyze_question_type(self, question_lower: str) -> str:
        """分析问题类型"""
        if any(word in question_lower for word in ['main idea', 'main purpose', 'primarily about', 'mainly']):
            return "main_idea"
        elif any(word in question_lower for word in ['according to', 'the passage states', 'the author says', 'based on the passage']):
            return "detail"
        elif any(word in question_lower for word in ['infer', 'suggest', 'implies', 'probably']):
            return "inference"
        else:
            return "general"
    
    def _parse_simple_answer(self, answer_text: str, options_count: int) -> int:
        """解析简单答案"""
        for i in range(options_count):
            if chr(65 + i) in answer_text.upper():
                return i
        return -1

class BrowserManager:
    """浏览器管理器，处理浏览器相关操作"""
    
    def __init__(self):
        self.driver = None
        self.element_finder = None
    
    def setup_driver(self):
        """设置Chrome浏览器驱动"""
        options = webdriver.ChromeOptions()
        
        # 优化Chrome选项
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--window-size=1200,800')
        
        # 自动查找Chrome路径
        self._find_chrome_path(options)
        
        print("启动Chrome浏览器...")
        try:
            from selenium.webdriver.chrome.service import Service
            service = Service()
            service.creationflags = 0x08000000
            
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.element_finder = EnhancedElementFinder(self.driver, timeout=30)
            print("Chrome浏览器启动成功")
            
        except WebDriverException as e:
            print(f"ChromeDriver启动失败: {e}")
            print("请检查：")
            print("   1. Chrome浏览器是否已安装")
            print("   2. ChromeDriver版本是否与Chrome匹配")
            print("   3. 是否已正确安装ChromeDriver")
            raise
    
    def _find_chrome_path(self, options):
        """查找Chrome浏览器路径"""
        import platform
        system = platform.system()
        
        if system == "Darwin":
            possible_paths = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    options.binary_location = path
                    break
        elif system == "Windows":
            possible_paths = [
                'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    options.binary_location = path
                    break
    
    def quit(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()

class ReadTheoryBot:
    """ReadTheory自动化机器人主类"""
    
    # 统一的元素选择器配置
    SELECTORS = {
        'username': [
            (By.XPATH, '//*[@id="username"]'),
            (By.CSS_SELECTOR, '#username'),
            (By.NAME, 'username'),
            (By.CSS_SELECTOR, 'input[type="text"]')
        ],
        'password': [
            (By.XPATH, '//*[@id="password"]'),
            (By.CSS_SELECTOR, '#password'),
            (By.NAME, 'password'),
            (By.CSS_SELECTOR, 'input[type="password"]')
        ],
        'login_button': [
            (By.XPATH, '//*[@id="ajaxLogin"]'),
            (By.CSS_SELECTOR, '#ajaxLogin'),
            (By.CSS_SELECTOR, 'input[type="submit"]'),
            (By.CSS_SELECTOR, 'button[type="submit"]')
        ],
        'ready_button': [
            "//button[contains(text(), 'I am Ready')]",
            "//button[contains(text(), \"I'm Ready\")]",
            "//button[contains(text(), 'Ready')]",
            (By.CSS_SELECTOR, "button:contains('Ready')"),
            (By.CSS_SELECTOR, "input[value*='Ready']"),
            (By.CSS_SELECTOR, "a:contains('Ready')")
        ],
        'article': [
            (By.XPATH, '//div[contains(@class, "passage")]'),
            (By.CSS_SELECTOR, '.passage'),
            (By.CSS_SELECTOR, '[class*="passage"]'),
            (By.CSS_SELECTOR, '.reading-passage')
        ],
        'question': [
            (By.XPATH, '//div[contains(@class, "question")]'),
            (By.CSS_SELECTOR, '.question'),
            (By.CSS_SELECTOR, '[class*="question"]')
        ],
        'options': [
            (By.XPATH, '//div[contains(@class, "answer-card")]'),
            (By.CSS_SELECTOR, '.answer-card'),
            (By.CSS_SELECTOR, '[class*="answer"]'),
            (By.CSS_SELECTOR, '.choice')
        ],
        'submit_button': [
            '/html/body/div[3]/div[3]/div/div[2]/div[2]/div[2]/div[3]/div[2]',
            (By.XPATH, "//button[contains(text(), 'Submit')]"),
            (By.CSS_SELECTOR, "button:contains('Submit')"),
            (By.CSS_SELECTOR, "input[type='submit']")
        ],
        'next_button': [
            '/html/body/div[3]/div[3]/div/div[2]/div[2]/div[2]/div[3]/div[1]',
            (By.XPATH, "//button[contains(text(), 'Next')]"),
            (By.CSS_SELECTOR, "button:contains('Next')"),
            (By.CSS_SELECTOR, "a:contains('Next')")
        ]
    }
    
    def __init__(self, spark_appid: str = None, spark_api_key: str = None, spark_api_secret: str = None, huggingface_token: str = None):
        self.browser_manager = BrowserManager()
        self.browser_manager.setup_driver()
        
        self.spark_appid = spark_appid
        self.spark_api_key = spark_api_key
        self.spark_api_secret = spark_api_secret
        self.text_analyzer = TextAnalyzer(huggingface_token)
        
        if all([spark_appid, spark_api_key, spark_api_secret]):
            self.spark_client = SparkAI(spark_appid, spark_api_key, spark_api_secret)
            print("讯飞星火AI客户端初始化成功")
        else:
            self.spark_client = None
            print("讯飞星火AI客户端未配置")
            
        self.article_content = ""
        self.questions_answered = 0
        self.correct_answers = 0
        self.analysis_methods_used = []
    
    @property
    def driver(self):
        return self.browser_manager.driver
    
    @property
    def element_finder(self):
        return self.browser_manager.element_finder
    
    def handle_pretest_screen(self):
        """处理预测试界面"""
        print("检查预测试界面...")
        try:
            time.sleep(5)
            
            ready_button = self.element_finder.find_clickable_with_retry(
                self.SELECTORS['ready_button'], "I'm Ready按钮"
            )
            if ready_button:
                print("找到'I'm Ready'按钮，点击开始测试...")
                ready_button.click()
                time.sleep(5)
                return True
            
            print("未找到预测试界面，继续正常流程...")
            return False
            
        except Exception as e:
            print(f"处理预测试界面时出错: {e}")
            return False

    def login(self, username: str, password: str):
        """登录ReadTheory"""
        print("正在登录ReadTheory...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.driver.get('https://readtheory.org/auth/login')
                time.sleep(5)
                
                # 使用统一的选择器配置
                username_field = self.element_finder.find_element_with_retry(
                    self.SELECTORS['username'], "用户名输入框"
                )
                if not username_field:
                    continue
                    
                username_field.clear()
                username_field.send_keys(username)
                
                password_field = self.element_finder.find_element_with_retry(
                    self.SELECTORS['password'], "密码输入框"
                )
                if not password_field:
                    continue
                    
                password_field.clear()
                password_field.send_keys(password)
                
                login_button = self.element_finder.find_clickable_with_retry(
                    self.SELECTORS['login_button'], "登录按钮"
                )
                if not login_button:
                    continue
                    
                login_button.click()
                
                time.sleep(8)
                
                if self._check_login_success():
                    print("登录成功")
                    self.handle_pretest_screen()
                    return True
                else:
                    if self._check_login_error():
                        print("登录失败：用户名或密码错误")
                        return False
                    else:
                        print(f"登录状态不确定，当前页面: {self.driver.current_url}")
                        continue
                            
            except Exception as e:
                print(f"登录尝试 {attempt + 1} 失败: {e}")
                if attempt < max_retries - 1:
                    print("重新尝试登录...")
                    time.sleep(5)
                else:
                    print("所有登录尝试都失败了")
                    return False
        
        return False
    
    def _check_login_success(self):
        """检查登录是否成功"""
        current_url = self.driver.current_url
        return any(keyword in current_url for keyword in ["dashboard", "app", "quiz"])
    
    def _check_login_error(self):
        """检查登录错误"""
        error_elements = self.driver.find_elements(By.XPATH, '//*[contains(text(), "error") or contains(text(), "invalid") or contains(text(), "incorrect")]')
        return len(error_elements) > 0

    def extract_content(self) -> Tuple[Optional[str], Optional[str], Optional[List[str]]]:
        """提取文章、问题和选项"""
        try:
            time.sleep(5)
            
            if self._check_if_pretest_screen():
                print("检测到预测试题目，开始答题...")
            
            # 使用统一的选择器配置
            article_element = self.element_finder.find_element_with_retry(
                self.SELECTORS['article'], "文章内容"
            )
            if not article_element:
                return None, None, None
                
            self.article_content = article_element.text
            print(f"文章长度: {len(self.article_content)} 字符")

            question_element = self.element_finder.find_element_with_retry(
                self.SELECTORS['question'], "问题"
            )
            if not question_element:
                return None, None, None
                
            question_text = question_element.text
            print(f"问题: {question_text}")

            # 查找选项
            options = self.driver.find_elements(*self.SELECTORS['options'][0])  # 使用第一个选择器
            option_texts = [option.text.strip() for option in options if option.text.strip()]
            
            if len(option_texts) > 5:
                option_texts = option_texts[:5]
                print("检测到超过5个选项，只取前5个选项")
            
            for i, option in enumerate(option_texts):
                print(f"  {chr(65+i)}. {option}")

            return self.article_content, question_text, option_texts
            
        except Exception as e:
            print(f"内容提取失败: {e}")
            return None, None, None

    def _check_if_pretest_screen(self):
        """检查是否在预测试界面"""
        try:
            pretest_indicators = [
                "//*[contains(text(), 'pretest')]",
                "//*[contains(text(), '8 questions')]",
                "//*[contains(text(), '20 minutes')]",
                "//*[contains(text(), 'difficulty based on your answers')]"
            ]
            
            for indicator in pretest_indicators:
                elements = self.driver.find_elements(By.XPATH, indicator)
                if elements:
                    return True
            return False
        except:
            return False

    def analyze_with_spark(self, article: str, question: str, options: List[str]) -> int:
        """使用讯飞星火AI分析文章和问题"""
        if not self.spark_client:
            return -1
            
        try:
            prompt = self.spark_client.build_prompt(article, question, options)
            
            messages = [{"role": "user", "content": prompt}]
            
            print("调用讯飞星火API...")
            answer = self.spark_client.chat_completion(messages)
            print(f"星火AI最终分析结果: {answer}")
            
            return self.spark_client.parse_answer(answer, len(options))
            
        except Exception as e:
            print(f"星火AI分析失败: {e}")
            return -1

    def smart_analysis(self, article: str, question: str, options: List[str]) -> int:
        """智能分析策略"""
        print("开始智能分析...")
        
        if self.spark_client:
            print("尝试使用讯飞星火AI分析...")
            spark_result = self.analyze_with_spark(article, question, options)
            if spark_result != -1:
                self.analysis_methods_used.append("SparkAI")
                return spark_result
            else:
                print("星火AI分析失败，尝试备用方案...")
        
        print("尝试使用TF-IDF分析...")
        free_api_result = self.text_analyzer.analyze_with_tfidf(article, question, options)
        if free_api_result != -1:
            self.analysis_methods_used.append("TFIDF")
            return free_api_result
        
        print("使用增强关键词分析...")
        keyword_result = self.text_analyzer.analyze_with_enhanced_keywords(article, question, options)
        self.analysis_methods_used.append("EnhancedKeyword")
        return keyword_result

    def answer_question(self) -> bool:
        """回答单个问题"""
        try:
            article, question, options = self.extract_content()
            if not all([article, question, options]) or len(options) < 2:
                print("内容提取不完整")
                return False

            best_option_index = self.smart_analysis(article, question, options)
            method_used = self.analysis_methods_used[-1] if self.analysis_methods_used else "Unknown"
            
            print(f"使用{method_used}分析，选择: 选项 {chr(65+best_option_index)}")

            option_elements = self.driver.find_elements(*self.SELECTORS['options'][0])
            if best_option_index < len(option_elements):
                option_elements[best_option_index].click()
                time.sleep(2)

                if self.submit_answer():
                    self.questions_answered += 1
                    return True

            return False

        except Exception as e:
            print(f"答题过程出错: {e}")
            return False

    def submit_answer(self) -> bool:
        """提交答案"""
        try:
            submit_button = self.element_finder.find_clickable_with_retry(
                self.SELECTORS['submit_button'], "提交按钮"
            )
            if submit_button:
                submit_button.click()
                print("答案已提交")
                time.sleep(3)
                return True
            
            print("未找到提交按钮")
            return False
            
        except Exception as e:
            print(f"提交答案失败: {e}")
            return False

    def check_answer_correctness(self) -> bool:
        """检查答案是否正确"""
        try:
            correct_elements = self.driver.find_elements(By.XPATH, '//*[contains(text(), "correct") or contains(text(), "正确")]')
            if correct_elements:
                print("回答正确!")
                return True
                
            incorrect_elements = self.driver.find_elements(By.XPATH, '//*[contains(text(), "incorrect") or contains(text(), "错误")]')
            if incorrect_elements:
                print("回答错误")
                return False
                
            correct_styled = self.driver.find_elements(By.XPATH, '//*[contains(@class, "correct")]')
            if correct_styled:
                print("回答正确!")
                return True
                
        except:
            pass
            
        print("无法确定答案正确性")
        return False

    def click_next(self):
        """点击下一题"""
        try:
            next_button = self.element_finder.find_clickable_with_retry(
                self.SELECTORS['next_button'], "下一题按钮"
            )
            if next_button:
                next_button.click()
                print("进入下一题")
                time.sleep(3)
                return True
            
            print("未找到下一题按钮")
            return False
            
        except Exception as e:
            print(f"点击下一题失败: {e}")
            return False

    def get_statistics(self) -> dict:
        """获取统计信息"""
        total = self.questions_answered
        correct = self.correct_answers
        accuracy = (correct / total * 100) if total > 0 else 0
        
        method_count = {}
        for method in self.analysis_methods_used:
            method_count[method] = method_count.get(method, 0) + 1
        
        return {
            "total_questions": total,
            "correct_answers": correct,
            "accuracy": round(accuracy, 2),
            "methods_used": method_count
        }

    def run(self, username: str, password: str, num_quizzes: int = 20):
        """运行主程序"""
        print("启动混合模式ReadTheory自动化程序")
        print("=" * 50)
        print(f"目标: 完成 {num_quizzes} 个测验")
        print(f"讯飞星火AI: {'已配置' if self.spark_client else '未配置'}")
        print(f"Hugging Face: {'已配置' if self.text_analyzer.huggingface_token else '未配置'}")
        print("=" * 50)
        
        try:
            login_success = self.login(username, password)
            if not login_success:
                print("登录失败，程序退出")
                return
            
            for quiz_num in range(1, num_quizzes + 1):
                print(f"\n进度: {quiz_num}/{num_quizzes}")
                print("-" * 30)
                
                if self.answer_question():
                    stats = self.get_statistics()
                    print(f"当前准确率: {stats['accuracy']}%")
                    print(f"分析方法: {stats['methods_used']}")
                    
                    if not self.click_next():
                        print("刷新页面...")
                        self.driver.refresh()
                        
                    delay = random.uniform(5, 10)
                    print(f"等待 {delay:.1f} 秒...")
                    time.sleep(delay)
                    
                else:
                    print("答题失败，刷新页面重试...")
                    self.driver.refresh()
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            print("\n用户中断程序")
        except Exception as e:
            print(f"程序运行出错: {e}")
        finally:
            final_stats = self.get_statistics()
            print("\n" + "=" * 50)
            print("程序完成统计:")
            print(f"   总答题数: {final_stats['total_questions']}")
            print(f"   正确答题: {final_stats['correct_answers']}")
            print(f"   准确率: {final_stats['accuracy']}%")
            print(f"   分析方法使用情况: {final_stats['methods_used']}")
            print("=" * 50)
            
            self.browser_manager.quit()

# 工具函数保持不变
def get_user_credentials():
    """获取用户输入的凭据"""
    print("\n请输入ReadTheory登录信息")
    print("-" * 30)
    
    username = input("请输入用户名: ").strip()
    if not username:
        print("用户名不能为空")
        return None, None
        
    password = getpass.getpass("请输入密码: ").strip()
    if not password:
        print("密码不能为空")
        return None, None
        
    return username, password

def check_chromedriver():
    """检查ChromeDriver是否可用"""
    try:
        print("检查ChromeDriver...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        driver.quit()
        print("ChromeDriver检查通过")
        return True
    except Exception as e:
        print(f"ChromeDriver检查失败: {e}")
        print("请运行: pip install --upgrade selenium")
        print("或下载匹配的ChromeDriver: https://chromedriver.chromium.org/")
        return False

def main():
    """主函数"""
    print("ReadTheory混合模式自动化机器人")
    print("=" * 50)
    
    if not check_chromedriver():
        return
    
    username, password = get_user_credentials()
    if not username or not password:
        return
    
    try:
        num_quizzes = input("要完成的测验数量 (默认20): ").strip()
        num_quizzes = int(num_quizzes) if num_quizzes.isdigit() else 20
    except:
        num_quizzes = 20
    
    CONFIG = {
        "spark_appid": "",
        "spark_api_key": "
        "spark_api_secret": "",
        "huggingface_token": ""
    }
    
    print("\n初始化机器人...")
    
    try:
        bot = ReadTheoryBot(
            spark_appid=CONFIG["spark_appid"],
            spark_api_key=CONFIG["spark_api_key"],
            spark_api_secret=CONFIG["spark_api_secret"],
            huggingface_token=CONFIG["huggingface_token"]
        )
        
        bot.run(username, password, num_quizzes)
    except Exception as e:
        print(f"程序执行失败: {e}")
        print("可能的解决方案:")
        print("   1. 检查网络连接")
        print("   2. 确保Chrome浏览器已安装")
        print("   3. 重新安装ChromeDriver")
        print("   4. 运行: pip install --upgrade selenium")

if __name__ == "__main__":
    main()
