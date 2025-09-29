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
    """用来和讯飞星火AI对话的客户端"""
    
    def __init__(self, app_id: str, key: str, secret: str):
        self.app_id = app_id
        self.key = key
        self.secret = secret
        self.endpoint = "wss://spark-api.xf-yun.com/v3.5/chat"
        self.response_text = ""
        self.got_answer = False
        
    def build_auth_url(self):
        """生成带认证的URL地址"""
        current_time = datetime.now()
        date_str = format_date_time(mktime(current_time.timetuple()))
        
        sign_source = "host: " + "spark-api.xf-yun.com" + "\n"
        sign_source += "date: " + date_str + "\n"
        sign_source += "GET " + "/v3.5/chat " + "HTTP/1.1"
        
        signature_hash = hmac.new(self.secret.encode('utf-8'), 
                                sign_source.encode('utf-8'), 
                                digestmod=hashlib.sha256).digest()
        
        signature_b64 = base64.b64encode(signature_hash).decode(encoding='utf-8')
        
        auth_source = f'api_key="{self.key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_b64}"'
        auth_header = base64.b64encode(auth_source.encode('utf-8')).decode(encoding='utf-8')
        
        params = {
            "authorization": auth_header,
            "date": date_str,
            "host": "spark-api.xf-yun.com"
        }
        full_url = self.endpoint + '?' + urlencode(params)
        return full_url

    def handle_message(self, ws, msg):
        """收到WebSocket消息时处理"""
        response_data = json.loads(msg)
        status_code = response_data['header']['code']
        
        if status_code != 0:
            print(f'API返回错误: {status_code}, 详情: {response_data}')
            ws.close()
        else:
            choices_part = response_data["payload"]["choices"]
            completion_status = choices_part["status"]
            text_content = choices_part["text"][0]["content"]
            self.response_text += text_content
            print(f"AI回复内容: {text_content}")
            
            if completion_status == 2:
                self.got_answer = True
                ws.close()

    def handle_error(self, ws, err):
        """WebSocket出错时处理"""
        print(f"连接异常: {err}")

    def handle_close(self, ws, close_code, close_reason):
        """WebSocket关闭时处理"""
        print("WebSocket连接已断开")

    def handle_open(self, ws):
        """WebSocket连接成功时处理"""
        def send_request(*args):
            request_payload = {
                "header": {
                    "app_id": self.app_id,
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
                        "text": self.conversation
                    }
                }
            }
            ws.send(json.dumps(request_payload))
            print("请求已发送到星火AI")

        thread.start_new_thread(send_request, ())

    def get_completion(self, conversation_history: List[dict]) -> str:
        """发送聊天请求并等待回复"""
        self.conversation = conversation_history
        self.response_text = ""
        self.got_answer = False
        
        print("正在连接讯飞星火AI服务...")
        websocket.enableTrace(False)
        ws_url = self.build_auth_url()
        ws_app = websocket.WebSocketApp(ws_url,
                                      on_message=self.handle_message,
                                      on_error=self.handle_error,
                                      on_close=self.handle_close)
        ws_app.on_open = self.handle_open
        
        def run_ws():
            ws_app.run_forever()
        
        ws_thread = threading.Thread(target=run_ws)
        ws_thread.daemon = True
        ws_thread.start()
        
        max_wait = 30
        begin_time = time.time()
        while not self.got_answer and (time.time() - begin_time) < max_wait:
            time.sleep(0.1)
            
        if not self.got_answer:
            print("等待AI响应超时")
            
        return self.response_text.strip()

class FreeAPIAnalysis:
    """用免费API来分析文章和问题"""
    
    def __init__(self, hf_token: str = None):
        self.hf_token = hf_token
    
    def hf_analysis(self, passage: str, query: str, choices: List[str]) -> int:
        """用Hugging Face的AI模型来分析"""
        try:
            API_ENDPOINT = "https://api-inference.huggingface.co/models/google/flan-t5-xl"
            headers = {"Authorization": f"Bearer {self.hf_token}"} if self.hf_token else {}
            
            question_prompt = f"""
阅读下面的文章并回答问题：

文章内容: {passage[:800]}

问题: {query}

选项:
{chr(10).join([f'{idx+1}. {choice}' for idx, choice in enumerate(choices)])}

根据文章，正确答案应该是选项:
"""
            
            request_data = {
                "inputs": question_prompt,
                "parameters": {
                    "max_length": 50,
                    "temperature": 0.1,
                    "do_sample": False
                }
            }
            
            print("调用Hugging Face API中...")
            api_response = requests.post(API_ENDPOINT, headers=headers, json=request_data, timeout=30)
            
            if api_response.status_code == 200:
                result_data = api_response.json()
                generated_text = result_data[0]['generated_text']
                print(f"Hugging Face分析结果: {generated_text}")
                
                for choice_idx in range(len(choices)):
                    if str(choice_idx+1) in generated_text:
                        return choice_idx
            else:
                print(f"Hugging Face API错误码: {api_response.status_code}")
                
        except Exception as error:
            print(f"Hugging Face API调用异常: {error}")
        
        return -1
    
    def keyword_based_analysis(self, text: str, problem: str, answers: List[str]) -> int:
        """用关键词匹配的方法来分析"""
        print("开始关键词分析...")
        text_lower = text.lower()
        problem_lower = problem.lower()
        
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        tokens = re.findall(r'\b\w+\b', text_lower)
        word_counts = Counter([token for token in tokens if token not in common_words and len(token) > 2])
        key_terms = set([term for term, count in word_counts.most_common(20)])
        
        option_scores = []
        
        for idx, answer in enumerate(answers):
            points = 0
            answer_lower = answer.lower()
            answer_words = set(re.findall(r'\b\w+\b', answer_lower))
            
            shared_words = answer_words.intersection(key_terms)
            points += len(shared_words) * 2
            
            if answer_lower in text_lower:
                points += 10
            
            if any(term in problem_lower for term in ['according to', 'the passage states', 'the author says']):
                for sentence in text_lower.split('.'):
                    if any(word in sentence for word in answer_words):
                        points += 3
            
            option_scores.append(points)
            print(f"  选项 {idx+1} 关键词得分: {points}")
        
        best_choice = option_scores.index(max(option_scores))
        print(f"关键词分析选择: 选项 {best_choice + 1}")
        return best_choice
    
    def free_analysis(self, passage: str, query: str, choices: List[str]) -> int:
        """先用Hugging Face，不行就用关键词分析"""
        if self.hf_token:
            hf_result = self.hf_analysis(passage, query, choices)
            if hf_result != -1:
                return hf_result
        
        return self.keyword_based_analysis(passage, query, choices)

class HybridReadTheoryBot:
    """自动做ReadTheory题目的机器人"""
    
    def __init__(self, spark_id: str = None, spark_key: str = None, spark_secret: str = None, hf_token: str = None):
        self.init_browser()
        self.spark_id = spark_id
        self.spark_key = spark_key
        self.spark_secret = spark_secret
        self.api_analyzer = FreeAPIAnalysis(hf_token)
        
        if all([spark_id, spark_key, spark_secret]):
            self.spark_ai = SparkAI(spark_id, spark_key, spark_secret)
            print("讯飞星火AI客户端初始化完成")
        else:
            self.spark_ai = None
            print("未配置讯飞星火AI")
            
        self.current_article = ""
        self.total_attempted = 0
        self.right_count = 0
        self.used_methods = []
        
    def init_browser(self):
        """设置Chrome浏览器"""
        chrome_options = webdriver.ChromeOptions()
        
        import platform
        if platform.system() == "Darwin":
            chrome_options.binary_location = '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'
        else:
            chrome_options.binary_location = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
        
        chrome_options.add_argument('window-size=1200x800')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.browser = webdriver.Chrome(options=chrome_options)
        self.browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.page_wait = WebDriverWait(self.browser, 15)

    def do_login(self, user: str, pwd: str):
        """登录ReadTheory网站"""
        print("正在登录ReadTheory账户...")
        self.browser.get('https://readtheory.org/auth/login')
        time.sleep(3)
        
        try:
            username_input = self.page_wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="username"]'))
            )
            username_input.clear()
            username_input.send_keys(user)
            
            password_input = self.browser.find_element(By.XPATH, '//*[@id="password"]')
            password_input.clear()
            password_input.send_keys(pwd)
            
            login_btn = self.browser.find_element(By.XPATH, '//*[@id="ajaxLogin"]')
            login_btn.click()
            
            time.sleep(5)
            
            if "dashboard" in self.browser.current_url or "quiz" in self.browser.current_url:
                print("登录成功")
                return True
            else:
                error_msgs = self.browser.find_elements(By.XPATH, '//*[contains(text(), "error") or contains(text(), "invalid") or contains(text(), "incorrect")]')
                if error_msgs:
                    print("登录失败：账号或密码错误")
                    return False
                else:
                    print("登录成功")
                    return True
                
        except Exception as login_error:
            print(f"登录过程出错: {login_error}")
            return False

    def get_page_content(self) -> Tuple[Optional[str], Optional[str], Optional[List[str]]]:
        """从网页上抓取文章、问题和选项"""
        try:
            time.sleep(4)
            
            article_elem = self.page_wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "passage")]'))
            )
            self.current_article = article_elem.text
            print(f"📖 文章内容长度: {len(self.current_article)} 字符")

            question_elem = self.browser.find_element(By.XPATH, '//div[contains(@class, "question")]')
            question_text = question_elem.text
            print(f"❓ 问题: {question_text}")

            choice_elems = self.browser.find_elements(By.XPATH, '//div[contains(@class, "answer-card")]')
            choice_texts = [elem.text.strip() for elem in choice_elems if elem.text.strip()]
            
            for idx, choice in enumerate(choice_texts):
                print(f"   {idx+1}. {choice}")

            return self.current_article, question_text, choice_texts
            
        except Exception as extract_error:
            print(f"提取页面内容失败: {extract_error}")
            return None, None, None

    def spark_analysis(self, content: str, q: str, opts: List[str]) -> int:
        """用讯飞星火AI来分析"""
        if not self.spark_ai:
            return -1
            
        try:
            short_content = content[:3000]
            
            system_prompt = f"""请阅读以下文章并回答问题。严格基于文章内容选择最准确的答案。

【文章】
{short_content}

【问题】
{q}

【选项】
{chr(10).join([f'{opt_idx+1}. {opt_text}' for opt_idx, opt_text in enumerate(opts)])}

请仔细分析文章，选择最符合文章意思的选项。只返回选项数字（1, 2, 3, 或4），不要包含其他文字。"""
            
            msg_history = [
                {
                    "role": "user",
                    "content": system_prompt
                }
            ]
            
            print("调用讯飞星火AI分析中...")
            ai_response = self.spark_ai.get_completion(msg_history)
            print(f"星火AI分析结果: {ai_response}")
            
            for opt_index in range(len(opts)):
                if str(opt_index+1) in ai_response:
                    return opt_index
                    
            return -1
            
        except Exception as ai_error:
            print(f"星火AI分析异常: {ai_error}")
            return -1

    def decide_answer(self, article_text: str, question_text: str, options_list: List[str]) -> int:
        """用多种方法分析，选最好的答案"""
        print("开始综合分析题目...")
        
        if self.spark_ai:
            print("尝试使用讯飞星火AI...")
            spark_choice = self.spark_analysis(article_text, question_text, options_list)
            if spark_choice != -1:
                self.used_methods.append("SparkAI")
                return spark_choice
            else:
                print("星火AI分析无效，尝试其他方法...")
        
        print("尝试Hugging Face分析...")
        api_choice = self.api_analyzer.free_analysis(article_text, question_text, options_list)
        if api_choice != -1:
            self.used_methods.append("HuggingFace")
            return api_choice
        
        print("使用关键词分析作为备选...")
        keyword_choice = self.api_analyzer.keyword_based_analysis(article_text, question_text, options_list)
        self.used_methods.append("Keyword")
        return keyword_choice

    def process_question(self) -> bool:
        """处理并回答一个问题"""
        try:
            article_content, question_content, option_list = self.get_page_content()
            if not all([article_content, question_content, option_list]) or len(option_list) < 2:
                print("页面内容提取不完整")
                return False

            selected_index = self.decide_answer(article_content, question_content, option_list)
            method_name = self.used_methods[-1] if self.used_methods else "未知方法"
            
            print(f"使用{method_name}分析，最终选择: 选项 {selected_index + 1}")

            option_elements = self.browser.find_elements(By.XPATH, '//div[contains(@class, "answer-card")]')
            if selected_index < len(option_elements):
                option_elements[selected_index].click()
                time.sleep(2)

                if self.send_answer():
                    self.total_attempted += 1
                    return True

            return False

        except Exception as process_error:
            print(f"答题过程异常: {process_error}")
            return False

    def send_answer(self) -> bool:
        """提交答案"""
        try:
            submit_elem = self.page_wait.until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div[3]/div/div[2]/div[2]/div[2]/div[3]/div[2]'))
            )
            submit_elem.click()
            print("答案已提交")
            time.sleep(3)
            
            if self.check_result():
                self.right_count += 1
                
            return True
            
        except Exception as submit_error:
            print(f"提交答案失败: {submit_error}")
            return False

    def check_result(self) -> bool:
        """检查答案是否正确"""
        try:
            correct_indicators = self.browser.find_elements(By.XPATH, '//*[contains(text(), "correct") or contains(text(), "正确")]')
            if correct_indicators:
                print("回答正确!")
                return True
                
            wrong_indicators = self.browser.find_elements(By.XPATH, '//*[contains(text(), "incorrect") or contains(text(), "错误")]')
            if wrong_indicators:
                print("回答错误")
                return False
                
            correct_styles = self.browser.find_elements(By.XPATH, '//*[contains(@class, "correct")]')
            if correct_styles:
                print("回答正确!")
                return True
                
        except:
            pass
            
        print("无法判断答案正确性")
        return False

    def go_next(self):
        """点击下一题"""
        try:
            next_elem = self.page_wait.until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div[3]/div/div[2]/div[2]/div[2]/div[3]/div[1]'))
            )
            next_elem.click()
            print("进入下一题")
            time.sleep(3)
            return True
        except Exception as next_error:
            print(f"点击下一题失败: {next_error}")
            return False

    def collect_stats(self) -> dict:
        """收集答题统计信息"""
        attempted = self.total_attempted
        correct = self.right_count
        success_rate = (correct / attempted * 100) if attempted > 0 else 0
        
        method_stats = {}
        for method in self.used_methods:
            method_stats[method] = method_stats.get(method, 0) + 1
        
        return {
            "attempted_count": attempted,
            "correct_count": correct,
            "success_rate": round(success_rate, 2),
            "method_usage": method_stats
        }

    def start_automation(self, username: str, password: str, quiz_count: int = 20):
        """启动自动化答题流程"""
        print("开始ReadTheory自动化答题")
        print("=" * 50)
        print(f"目标完成测验数: {quiz_count}")
        print(f"讯飞星火AI: {'已启用' if self.spark_ai else '未配置'}")
        print(f"Hugging Face: {'已启用' if self.api_analyzer.hf_token else '未配置'}")
        print("=" * 50)
        
        try:
            login_ok = self.do_login(username, password)
            if not login_ok:
                print("登录失败，程序终止")
                return
            
            for current_quiz in range(1, quiz_count + 1):
                print(f"\n正在进行第 {current_quiz}/{quiz_count} 个测验")
                print("-" * 30)
                
                if self.process_question():
                    current_stats = self.collect_stats()
                    print(f"当前准确率: {current_stats['success_rate']}%")
                    print(f"分析方法统计: {current_stats['method_usage']}")
                    
                    if not self.go_next():
                        print("刷新页面重试...")
                        self.browser.refresh()
                        
                    pause_time = random.uniform(5, 10)
                    print(f"等待 {pause_time:.1f} 秒后继续...")
                    time.sleep(pause_time)
                    
                else:
                    print("当前题目处理失败，刷新页面...")
                    self.browser.refresh()
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            print("\n用户主动停止程序")
        except Exception as run_error:
            print(f"程序运行出错: {run_error}")
        finally:
            final_stats = self.collect_stats()
            print("\n" + "=" * 50)
            print("自动化答题完成统计:")
            print(f"总答题数: {final_stats['attempted_count']}")
            print(f"正确答题: {final_stats['correct_count']}")
            print(f"准确率: {final_stats['success_rate']}%")
            print(f"分析方法使用情况: {final_stats['method_usage']}")
            print("=" * 50)
            
            self.browser.quit()

def get_login_info():
    """获取用户登录凭证"""
    print("\n请输入ReadTheory账户信息")
    print("-" * 30)
    
    user_name = input("请输入用户名: ").strip()
    if not user_name:
        print("用户名不能为空")
        return None, None
        
    pass_word = getpass.getpass("请输入密码: ").strip()
    if not pass_word:
        print("密码不能为空")
        return None, None
        
    return user_name, pass_word

def main_function():
    """程序主入口"""
    print("ReadTheory智能答题助手")
    print("=" * 50)
    
    user, pwd = get_login_info()
    if not user or not pwd:
        return
    
    try:
        quiz_num = input("计划完成的测验数量 (默认20): ").strip()
        quiz_num = int(quiz_num) if quiz_num.isdigit() else 20
    except:
        quiz_num = 20
    
    API_CONFIG = {
        "spark_appid": "",
        "spark_api_key": "", 
        "spark_api_secret": "",
        "huggingface_token": ""
    }
    
    print("\n初始化答题助手...")
    
    assistant = HybridReadTheoryBot(
        spark_id=API_CONFIG["spark_appid"],
        spark_key=API_CONFIG["spark_api_key"],
        spark_secret=API_CONFIG["spark_api_secret"],
        hf_token=API_CONFIG["huggingface_token"]
    )
    
    try:
        assistant.start_automation(user, pwd, quiz_num)
    except Exception as main_error:
        print(f"程序执行失败: {main_error}")

if __name__ == "__main__":
    main_function()