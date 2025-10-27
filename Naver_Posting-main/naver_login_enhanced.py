"""
네이버 로그인 인증 시스템 (Selenium 기반)
data 폴더 분석 결과를 바탕으로 개선된 로그인 시스템
"""

import time
import random
import clipboard
from datetime import datetime
from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import platform

class NaverLoginAuth:
    """네이버 로그인 인증 클래스"""
    
    def __init__(self, headless=False, wait_timeout=10):
        self.driver = None
        self.wait = None
        self.actions = None
        self.headless = headless
        self.wait_timeout = wait_timeout
        self.main_window = None
        
        # 플랫폼별 컨트롤 키
        self.CONTROL_KEY = Keys.COMMAND if platform.system() == "Darwin" else Keys.CONTROL
        
        # 네이버 로그인 관련 상수
        self.NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
        self.NAVER_MAIN_URL = "https://www.naver.com"
        
        # 로그인 상태 플래그
        self.is_logged_in = False
        self.login_method = None  # 'normal', 'captcha', 'sms' 등
        
        self.init_driver()
    
    def init_driver(self):
        """Chrome WebDriver 초기화"""
        try:
            service = Service(ChromeDriverManager().install())
            chrome_options = Options()
            
            # 기본 옵션 설정
            if self.headless:
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920x1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 알림 허용
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 1
            })
            
            self.driver = webdriver.Chrome(options=chrome_options, service=service)
            self.wait = WebDriverWait(self.driver, self.wait_timeout)
            self.actions = ActionChains(self.driver)
            
            # WebDriver 탐지 방지
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                """
            })
            
            self.main_window = self.driver.current_window_handle
            print("[INFO] Chrome WebDriver 초기화 완료")
            
        except Exception as e:
            print(f"[ERROR] WebDriver 초기화 실패: {str(e)}")
            raise
    
    def human_like_delay(self, min_delay=0.5, max_delay=2.0):
        """사람처럼 보이는 랜덤 딜레이"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def safe_click(self, element):
        """안전한 클릭 (사람처럼)"""
        try:
            # 요소가 보일 때까지 대기
            self.wait.until(EC.element_to_be_clickable(element))
            
            # 마우스를 요소로 이동
            self.actions.move_to_element(element).perform()
            self.human_like_delay(0.3, 0.8)
            
            # 클릭
            element.click()
            self.human_like_delay(0.5, 1.0)
            
            return True
        except Exception as e:
            print(f"[ERROR] 클릭 실패: {str(e)}")
            return False
    
    def safe_input_text(self, element, text, use_clipboard=True):
        """안전한 텍스트 입력"""
        try:
            element.clear()
            self.human_like_delay(0.2, 0.5)
            
            if use_clipboard:
                # 클립보드를 이용한 입력 (캡챠 우회에 효과적)
                clipboard.copy(text)
                element.click()
                self.human_like_delay(0.3, 0.7)
                
                # Ctrl+V로 붙여넣기
                self.actions.key_down(self.CONTROL_KEY).send_keys('v').key_up(self.CONTROL_KEY).perform()
                self.human_like_delay(0.5, 1.0)
            else:
                # 타이핑 시뮬레이션
                for char in text:
                    element.send_keys(char)
                    self.human_like_delay(0.1, 0.3)
            
            return True
        except Exception as e:
            print(f"[ERROR] 텍스트 입력 실패: {str(e)}")
            return False
    
    def navigate_to_login_page(self):
        """네이버 로그인 페이지로 이동"""
        try:
            print("[INFO] 네이버 로그인 페이지로 이동 중...")
            self.driver.get(self.NAVER_LOGIN_URL)
            self.human_like_delay(2, 4)
            
            # 페이지 로드 확인
            self.wait.until(EC.presence_of_element_located((By.ID, "id")))
            print("[INFO] 로그인 페이지 로드 완료")
            return True
            
        except TimeoutException:
            print("[ERROR] 로그인 페이지 로드 타임아웃")
            return False
        except Exception as e:
            print(f"[ERROR] 로그인 페이지 이동 실패: {str(e)}")
            return False
    
    def input_credentials(self, username, password):
        """로그인 정보 입력"""
        try:
            print("[INFO] 로그인 정보 입력 중...")
            
            # 아이디 입력
            id_input = self.wait.until(EC.presence_of_element_located((By.ID, "id")))
            if not self.safe_input_text(id_input, username):
                return False
            
            # 패스워드 입력
            pw_input = self.wait.until(EC.presence_of_element_located((By.ID, "pw")))
            if not self.safe_input_text(pw_input, password):
                return False
            
            print("[INFO] 로그인 정보 입력 완료")
            return True
            
        except TimeoutException:
            print("[ERROR] 로그인 입력 필드를 찾을 수 없음")
            return False
        except Exception as e:
            print(f"[ERROR] 로그인 정보 입력 실패: {str(e)}")
            return False
    
    def click_login_button(self):
        """로그인 버튼 클릭"""
        try:
            print("[INFO] 로그인 버튼 클릭...")
            
            # 로그인 버튼 찾기 및 클릭
            login_button = self.wait.until(EC.element_to_be_clickable((By.ID, "log.login")))
            if not self.safe_click(login_button):
                return False
            
            print("[INFO] 로그인 버튼 클릭 완료")
            return True
            
        except TimeoutException:
            print("[ERROR] 로그인 버튼을 찾을 수 없음")
            return False
        except Exception as e:
            print(f"[ERROR] 로그인 버튼 클릭 실패: {str(e)}")
            return False
    
    def check_login_result(self):
        """로그인 결과 확인"""
        try:
            print("[INFO] 로그인 결과 확인 중...")
            
            # 여러 가지 상황 체크
            for attempt in range(30):  # 30초간 체크
                current_url = self.driver.current_url
                
                # 1. 성공적으로 로그인된 경우
                if "naver.com" in current_url and "login" not in current_url:
                    # 로그인 정보 저장 안함 버튼이 있는지 확인
                    try:
                        save_button = self.driver.find_element(By.XPATH, "//a[contains(@href, 'saveido=false')]")
                        if save_button:
                            self.safe_click(save_button)
                            print("[INFO] 로그인 정보 저장 안함 선택")
                    except:
                        pass
                    
                    self.is_logged_in = True
                    self.login_method = 'normal'
                    print("[SUCCESS] 로그인 성공!")
                    return "success"
                
                # 2. 캡챠가 나타난 경우
                try:
                    captcha_element = self.driver.find_element(By.CLASS_NAME, "captcha_input")
                    if captcha_element.is_displayed():
                        print("[INFO] 캡챠 감지됨 - 사용자 입력 대기")
                        self.login_method = 'captcha'
                        return "captcha"
                except:
                    pass
                
                # 3. SMS 인증이 필요한 경우
                try:
                    sms_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'SMS') or contains(text(), '인증')]")
                    if sms_element.is_displayed():
                        print("[INFO] SMS 인증 감지됨")
                        self.login_method = 'sms'
                        return "sms"
                except:
                    pass
                
                # 4. 로그인 오류 메시지 확인
                try:
                    error_element = self.driver.find_element(By.CLASS_NAME, "error_box")
                    if error_element.is_displayed():
                        error_text = error_element.text
                        print(f"[ERROR] 로그인 실패: {error_text}")
                        return "error"
                except:
                    pass
                
                # 5. 아이디/비밀번호 오류
                try:
                    id_pw_error = self.driver.find_element(By.XPATH, "//*[contains(text(), '아이디') and contains(text(), '비밀번호')]")
                    if id_pw_error.is_displayed():
                        print("[ERROR] 아이디 또는 비밀번호가 잘못되었습니다")
                        return "credential_error"
                except:
                    pass
                
                time.sleep(1)
            
            print("[WARNING] 로그인 결과를 확인할 수 없음")
            return "timeout"
            
        except Exception as e:
            print(f"[ERROR] 로그인 결과 확인 실패: {str(e)}")
            return "error"
    
    def wait_for_captcha_completion(self, timeout=300):
        """캡챠 완료 대기 (5분 타임아웃)"""
        print("[INFO] 캡챠 완료를 기다리는 중... (최대 5분)")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 캡챠가 사라졌는지 확인
                captcha_element = self.driver.find_element(By.CLASS_NAME, "captcha_input")
                if not captcha_element.is_displayed():
                    print("[INFO] 캡챠 완료됨")
                    return True
            except:
                # 캡챠 요소가 없으면 완료된 것
                print("[INFO] 캡챠 완료됨")
                return True
            
            time.sleep(2)
        
        print("[WARNING] 캡챠 완료 타임아웃")
        return False
    
    def wait_for_sms_completion(self, timeout=300):
        """SMS 인증 완료 대기 (5분 타임아웃)"""
        print("[INFO] SMS 인증 완료를 기다리는 중... (최대 5분)")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_url = self.driver.current_url
            if "naver.com" in current_url and "login" not in current_url:
                print("[INFO] SMS 인증 완료됨")
                return True
            time.sleep(2)
        
        print("[WARNING] SMS 인증 완료 타임아웃")
        return False
    
    def login(self, username, password, retry_count=3):
        """통합 로그인 메서드"""
        print(f"[INFO] 네이버 로그인 시작 - 사용자: {username}")
        
        for attempt in range(retry_count):
            print(f"[INFO] 로그인 시도 {attempt + 1}/{retry_count}")
            
            # 1. 로그인 페이지로 이동
            if not self.navigate_to_login_page():
                continue
            
            # 2. 로그인 정보 입력
            if not self.input_credentials(username, password):
                continue
            
            # 3. 로그인 버튼 클릭
            if not self.click_login_button():
                continue
            
            # 4. 로그인 결과 확인
            result = self.check_login_result()
            
            if result == "success":
                print("[SUCCESS] 로그인 성공!")
                return {
                    'status': 'success',
                    'method': self.login_method,
                    'message': '로그인 성공'
                }
            
            elif result == "captcha":
                print("[INFO] 캡챠 인증 필요 - 사용자가 캡챠를 완료해주세요")
                if self.wait_for_captcha_completion():
                    # 캡챠 완료 후 다시 로그인 결과 확인
                    final_result = self.check_login_result()
                    if final_result == "success":
                        return {
                            'status': 'success',
                            'method': 'captcha',
                            'message': '캡챠 인증 후 로그인 성공'
                        }
                
                return {
                    'status': 'captcha_required',
                    'method': 'captcha',
                    'message': '캡챠 인증이 필요합니다'
                }
            
            elif result == "sms":
                print("[INFO] SMS 인증 필요 - 사용자가 SMS 인증을 완료해주세요")
                if self.wait_for_sms_completion():
                    return {
                        'status': 'success',
                        'method': 'sms',
                        'message': 'SMS 인증 후 로그인 성공'
                    }
                
                return {
                    'status': 'sms_required',
                    'method': 'sms',
                    'message': 'SMS 인증이 필요합니다'
                }
            
            elif result == "credential_error":
                return {
                    'status': 'error',
                    'method': None,
                    'message': '아이디 또는 비밀번호가 잘못되었습니다'
                }
            
            else:
                print(f"[WARNING] 로그인 실패 (시도 {attempt + 1}): {result}")
                time.sleep(2)
        
        return {
            'status': 'error',
            'method': None,
            'message': f'{retry_count}번 시도 후 로그인 실패'
        }
    
    def logout(self):
        """로그아웃"""
        try:
            if not self.is_logged_in:
                print("[INFO] 이미 로그아웃 상태입니다")
                return True
            
            print("[INFO] 로그아웃 중...")
            self.driver.get(self.NAVER_MAIN_URL)
            time.sleep(2)
            
            # 로그아웃 버튼 찾기 및 클릭
            try:
                logout_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'logout')]")))
                self.safe_click(logout_button)
                
                self.is_logged_in = False
                self.login_method = None
                print("[INFO] 로그아웃 완료")
                return True
                
            except TimeoutException:
                print("[WARNING] 로그아웃 버튼을 찾을 수 없음")
                return False
                
        except Exception as e:
            print(f"[ERROR] 로그아웃 실패: {str(e)}")
            return False
    
    def check_login_status(self):
        """현재 로그인 상태 확인"""
        try:
            self.driver.get(self.NAVER_MAIN_URL)
            time.sleep(2)
            
            # 로그인 상태 확인 (로그아웃 버튼이 있는지 체크)
            try:
                self.driver.find_element(By.XPATH, "//a[contains(@href, 'logout')]")
                self.is_logged_in = True
                print("[INFO] 로그인 상태 확인됨")
                return True
            except:
                self.is_logged_in = False
                print("[INFO] 로그아웃 상태 확인됨")
                return False
                
        except Exception as e:
            print(f"[ERROR] 로그인 상태 확인 실패: {str(e)}")
            return False
    
    def get_driver(self):
        """WebDriver 인스턴스 반환"""
        return self.driver
    
    def close(self):
        """WebDriver 종료"""
        try:
            if self.driver:
                self.driver.quit()
                print("[INFO] WebDriver 종료 완료")
        except Exception as e:
            print(f"[ERROR] WebDriver 종료 실패: {str(e)}")

# 사용 예시 및 테스트 함수
def test_naver_login():
    """네이버 로그인 테스트"""
    
    # 테스트용 계정 정보 (실제 사용 시 변경 필요)
    test_username = "your_naver_id"
    test_password = "your_naver_password"
    
    # 로그인 인증 객체 생성
    auth = NaverLoginAuth(headless=False)  # headless=True로 설정하면 브라우저 창이 보이지 않음
    
    try:
        # 로그인 시도
        result = auth.login(test_username, test_password)
        
        print(f"로그인 결과: {result}")
        
        if result['status'] == 'success':
            print("로그인 성공! 5초 후 로그아웃합니다.")
            time.sleep(5)
            auth.logout()
        
        elif result['status'] == 'captcha_required':
            print("캡챠 인증이 필요합니다. 브라우저에서 캡챠를 완료해주세요.")
            input("캡챠 완료 후 Enter 키를 눌러주세요...")
            
        elif result['status'] == 'sms_required':
            print("SMS 인증이 필요합니다. 휴대폰으로 받은 인증코드를 입력해주세요.")
            input("SMS 인증 완료 후 Enter 키를 눌러주세요...")
        
        else:
            print(f"로그인 실패: {result['message']}")
    
    finally:
        # WebDriver 종료
        auth.close()

if __name__ == "__main__":
    test_naver_login()