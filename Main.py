from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementNotVisibleException, NoSuchElementException, TimeoutException
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

class SparkAI:
    """讯飞星火AI客户端"""
    
    def __init__(self, appid: str, api_key: str, api_secret: str):
        self.appid = appid
        self.api_key = api_key
        self.api_secret = api_secret
        self.url = "wss://spark-api.xf-yun.com/v3.5/chat"
        self.answer = ""
        self.answer_received = False
        
    def create_url(self):
        """生成鉴权URL"""
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        
        # 拼接字符串
        signature_origin = "host: " + "spark-api.xf-yun.com" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v3.5/chat " + "HTTP/1.1"
        
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.api_secret.encode('utf-8'), 
                                signature_origin.encode('utf-8'), 
                                digestmod=hashlib.sha256).digest()
        
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')
        
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "spark-api.xf-yun.com"
        }
        # 拼接鉴权参数，生成url
        url = self.url + '?' + urlencode(v)
        return url

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
            # 构建请求数据
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
        
        # 在新线程中运行WebSocket
        def run_websocket():
            ws.run_forever()
        
        websocket_thread = threading.Thread(target=run_websocket)
        websocket_thread.daemon = True
        websocket_thread.start()
        
        # 等待回答完成
        timeout = 30  # 30秒超时
        start_time = time.time()
        while not self.answer_received and (time.time() - start_time) < timeout:
            time.sleep(0.1)
            
        if not self.answer_received:
            print("星火AI响应超时")
            
        return self.answer.strip()

class FreeAPIAnalysis:
    """免费API分析类"""
    
    def __init__(self, huggingface_token: str = None):
        self.huggingface_token = huggingface_token
    
    def analyze_with_huggingface(self, article: str, question: str, options: List[str]) -> int:
        """使用Hugging Face API进行分析"""
        try:
            API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-xl"
            headers = {"Authorization": f"Bearer {self.huggingface_token}"} if self.huggingface_token else {}
            
            # 构建提示词
            prompt = f"""
阅读以下文章并回答问题：

文章: {article[:800]}

问题: {question}

选项:
{chr(10).join([f'{i+1}. {opt}' for i, opt in enumerate(options)])}

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
                
                # 解析答案
                for i in range(len(options)):
                    if str(i+1) in answer_text:
                        return i
            else:
                print(f"Hugging Face API 错误: {response.status_code}")
                
        except Exception as e:
            print(f"Hugging Face API 调用失败: {e}")
        
        return -1  # 表示分析失败
    
    def analyze_with_keywords(self, article: str, question: str, options: List[str]) -> int:
        """基于关键词的分析方法"""
        print("使用关键词分析...")
        article_lower = article.lower()
        question_lower = question.lower()
        
        # 提取文章中的关键词（去除常见停用词）
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = re.findall(r'\b\w+\b', article_lower)
        word_freq = Counter([word for word in words if word not in stop_words and len(word) > 2])
        important_words = set([word for word, freq in word_freq.most_common(20)])
        
        scores = []
        
        for i, option in enumerate(options):
            score = 0
            option_lower = option.lower()
            option_words = set(re.findall(r'\b\w+\b', option_lower))
            
            # 计算与重要词汇的重叠
            common_words = option_words.intersection(important_words)
            score += len(common_words) * 2
            
            # 检查选项是否在文章中直接出现
            if option_lower in article_lower:
                score += 10
            
            # 对于细节题，检查具体信息匹配
            if any(word in question_lower for word in ['according to', 'the passage states', 'the author says']):
                # 计算选项与文章的相似度
                for sentence in article_lower.split('.'):
                    if any(word in sentence for word in option_words):
                        score += 3
            
            scores.append(score)
            print(f"  选项 {i+1} 关键词得分: {score}")
        
        best_index = scores.index(max(scores))
        print(f"关键词分析选择: 选项 {best_index + 1}")
        return best_index
    
    def analyze_with_free_api(self, article: str, question: str, options: List[str]) -> int:
        """免费API分析主方法"""
        # 先尝试Hugging Face API
        if self.huggingface_token:
            result = self.analyze_with_huggingface(article, question, options)
            if result != -1:
                return result
        
        # 回退到关键词分析
        return self.analyze_with_keywords(article, question, options)

class HybridReadTheoryBot:
    """混合模式ReadTheory自动化机器人"""
    
    def __init__(self, spark_appid: str = None, spark_api_key: str = None, spark_api_secret: str = None, huggingface_token: str = None):
        self.setup_driver()
        self.spark_appid = spark_appid
        self.spark_api_key = spark_api_key
        self.spark_api_secret = spark_api_secret
        self.free_analyzer = FreeAPIAnalysis(huggingface_token)
        
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
        
    def setup_driver(self):
        """设置Chrome浏览器驱动"""
        options = webdriver.ChromeOptions()
        
        import platform
        if platform.system() == "Darwin":  # macOS
            options.binary_location = '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'
        else:  # Windows
            options.binary_location = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
        
        options.add_argument('window-size=1200x800')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.wait = WebDriverWait(self.driver, 15)

    def login(self, username: str, password: str):
        """登录ReadTheory"""
        print("正在登录ReadTheory...")
        self.driver.get('https://readtheory.org/auth/login')
        time.sleep(3)
        
        try:
            username_field = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="username"]'))
            )
            username_field.clear()
            username_field.send_keys(username)
            
            password_field = self.driver.find_element(By.XPATH, '//*[@id="password"]')
            password_field.clear()
            password_field.send_keys(password)
            
            login_button = self.driver.find_element(By.XPATH, '//*[@id="ajaxLogin"]')
            login_button.click()
            
            # 等待登录完成
            time.sleep(5)
            
            # 检查登录是否成功
            if "dashboard" in self.driver.current_url or "quiz" in self.driver.current_url:
                print("登录成功")
                return True
            else:
                # 检查是否有错误信息
                error_elements = self.driver.find_elements(By.XPATH, '//*[contains(text(), "error") or contains(text(), "invalid") or contains(text(), "incorrect")]')
                if error_elements:
                    print("登录失败：用户名或密码错误")
                    return False
                else:
                    print("登录成功（页面跳转验证）")
                    return True
                
        except Exception as e:
            print(f"登录过程中出错: {e}")
            return False

    def extract_content(self) -> Tuple[Optional[str], Optional[str], Optional[List[str]]]:
        """提取文章、问题和选项"""
        try:
            # 等待页面加载
            time.sleep(4)
            
            # 提取文章
            article_element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "passage")]'))
            )
            self.article_content = article_element.text
            print(f"📖 文章长度: {len(self.article_content)} 字符")

            # 提取问题
            question_element = self.driver.find_element(By.XPATH, '//div[contains(@class, "question")]')
            question_text = question_element.text
            print(f"❓ 问题: {question_text}")

            # 提取选项
            options = self.driver.find_elements(By.XPATH, '//div[contains(@class, "answer-card")]')
            option_texts = [option.text.strip() for option in options if option.text.strip()]
            
            for i, option in enumerate(option_texts):
                print(f"   {i+1}. {option}")

            return self.article_content, question_text, option_texts
            
        except Exception as e:
            print(f"内容提取失败: {e}")
            return None, None, None

    def analyze_with_spark(self, article: str, question: str, options: List[str]) -> int:
        """使用讯飞星火AI分析文章和问题"""
        if not self.spark_client:
            return -1
            
        try:
            # 构建提示词，限制文章长度以避免过长
            truncated_article = article[:3000]  # 限制文章长度
            
            prompt = f"""请仔细阅读以下文章并回答问题。请严格基于文章内容选择最准确的答案。

【文章内容】
{truncated_article}

【问题】
{question}

【选项】
{chr(10).join([f'{i+1}. {option}' for i, option in enumerate(options)])}

请仔细分析文章内容，选择最符合文章意思的选项。只返回选项数字（1, 2, 3, 或4），不要包含其他任何文字。"""
            
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            print("调用讯飞星火API...")
            answer = self.spark_client.chat_completion(messages)
            print(f"星火AI最终分析结果: {answer}")
            
            # 解析答案
            for i in range(len(options)):
                if str(i+1) in answer:
                    return i
                    
            return -1
            
        except Exception as e:
            print(f"星火AI分析失败: {e}")
            return -1

    def smart_analysis(self, article: str, question: str, options: List[str]) -> int:
        """智能分析策略"""
        print("开始智能分析...")
        
        # 策略1: 优先使用讯飞星火AI分析（如果可用）
        if self.spark_client:
            print("尝试使用讯飞星火AI分析...")
            spark_result = self.analyze_with_spark(article, question, options)
            if spark_result != -1:
                self.analysis_methods_used.append("SparkAI")
                return spark_result
            else:
                print("星火AI分析失败，尝试备用方案...")
        
        # 策略2: 使用Hugging Face API分析
        print("尝试使用Hugging Face分析...")
        free_api_result = self.free_analyzer.analyze_with_free_api(article, question, options)
        if free_api_result != -1:
            self.analysis_methods_used.append("HuggingFace")
            return free_api_result
        
        # 策略3: 关键词分析作为最终回退
        print("使用关键词分析...")
        keyword_result = self.free_analyzer.analyze_with_keywords(article, question, options)
        self.analysis_methods_used.append("Keyword")
        return keyword_result

    def answer_question(self) -> bool:
        """回答单个问题"""
        try:
            # 提取内容
            article, question, options = self.extract_content()
            if not all([article, question, options]) or len(options) < 2:
                print("内容提取不完整")
                return False

            # 智能分析选择最佳答案
            best_option_index = self.smart_analysis(article, question, options)
            method_used = self.analysis_methods_used[-1] if self.analysis_methods_used else "Unknown"
            
            print(f"使用{method_used}分析，选择: 选项 {best_option_index + 1}")

            # 点击选择答案
            option_elements = self.driver.find_elements(By.XPATH, '//div[contains(@class, "answer-card")]')
            if best_option_index < len(option_elements):
                option_elements[best_option_index].click()
                time.sleep(2)

                # 提交答案
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
            submit_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div[3]/div/div[2]/div[2]/div[2]/div[3]/div[2]'))
            )
            submit_button.click()
            print("答案已提交")
            time.sleep(3)
            
            # 检查答案是否正确
            if self.check_answer_correctness():
                self.correct_answers += 1
                
            return True
            
        except Exception as e:
            print(f"提交答案失败: {e}")
            return False

    def check_answer_correctness(self) -> bool:
        """检查答案是否正确"""
        try:
            # 查找正确提示
            correct_elements = self.driver.find_elements(By.XPATH, '//*[contains(text(), "correct") or contains(text(), "正确")]')
            if correct_elements:
                print("回答正确!")
                return True
                
            # 查找错误提示
            incorrect_elements = self.driver.find_elements(By.XPATH, '//*[contains(text(), "incorrect") or contains(text(), "错误")]')
            if incorrect_elements:
                print("回答错误")
                return False
                
            # 通过样式判断
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
            next_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div[3]/div/div[2]/div[2]/div[2]/div[3]/div[1]'))
            )
            next_button.click()
            print("进入下一题")
            time.sleep(3)
            return True
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
        print(f"Hugging Face: {'已配置' if self.free_analyzer.huggingface_token else '未配置'}")
        print("=" * 50)
        
        try:
            # 尝试登录
            login_success = self.login(username, password)
            if not login_success:
                print("登录失败，程序退出")
                return
            
            for quiz_num in range(1, num_quizzes + 1):
                print(f"\n进度: {quiz_num}/{num_quizzes}")
                print("-" * 30)
                
                if self.answer_question():
                    # 获取当前统计
                    stats = self.get_statistics()
                    print(f"当前准确率: {stats['accuracy']}%")
                    print(f"分析方法: {stats['methods_used']}")
                    
                    # 点击下一题
                    if not self.click_next():
                        print("刷新页面...")
                        self.driver.refresh()
                        
                    # 随机延迟，避免被检测
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
            # 输出最终统计
            final_stats = self.get_statistics()
            print("\n" + "=" * 50)
            print("程序完成统计:")
            print(f"总答题数: {final_stats['total_questions']}")
            print(f"正确答题: {final_stats['correct_answers']}")
            print(f"准确率: {final_stats['accuracy']}%")
            print(f"分析方法使用情况: {final_stats['methods_used']}")
            print("=" * 50)
            
            self.driver.quit()

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

def main():
    """主函数"""
    print("ReadTheory混合模式自动化机器人")
    print("=" * 50)
    
    # 获取用户登录信息
    username, password = get_user_credentials()
    if not username or not password:
        return
    
    # 询问要完成的测验数量
    try:
        num_quizzes = input("要完成的测验数量 (默认20): ").strip()
        num_quizzes = int(num_quizzes) if num_quizzes.isdigit() else 20
    except:
        num_quizzes = 20
    
    # 配置API密钥
    CONFIG = {
        "spark_appid": "",
        "spark_api_key": "",
        "spark_api_secret": "",
        "huggingface_token": ""
    }
    
    print("\n初始化机器人...")
    
    # 创建机器人实例
    bot = HybridReadTheoryBot(
        spark_appid=CONFIG["spark_appid"],
        spark_api_key=CONFIG["spark_api_key"],
        spark_api_secret=CONFIG["spark_api_secret"],
        huggingface_token=CONFIG["huggingface_token"]
    )
    
    # 运行程序
    try:
        bot.run(username, password, num_quizzes)
    except Exception as e:
        print(f"程序执行失败: {e}")

if __name__ == "__main__":
    main()
