"""
Streamlit용 백엔드 처리 모듈
기존 wxPython 프로그램의 핵심 기능들을 Streamlit에서 사용할 수 있도록 변환
"""

import pandas as pd
import json
import os
import threading
import time
import random
from typing import Dict, List, Any, Optional
from datetime import datetime

class StreamlitTaskManager:
    """Streamlit 애플리케이션용 작업 관리자"""
    
    def __init__(self):
        self.is_running = False
        self.progress = 0
        self.current_task = ""
        self.logs = []
        
    def add_log(self, message: str, log_type: str = "info"):
        """로그 추가"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        self.logs.append({
            "timestamp": timestamp,
            "message": message,
            "type": log_type
        })
    
    def start_task(self, platform: str, account_data: pd.DataFrame, 
                   keyword_data: pd.DataFrame, content_template: str,
                   title_data: Optional[pd.DataFrame] = None,
                   api_key: str = "", phone_number: str = "",
                   waiting_min: int = 1, waiting_max: int = 3,
                   use_dynamic_ip: bool = False):
        """작업 시작"""
        if self.is_running:
            return False
            
        self.is_running = True
        self.progress = 0
        
        # 백그라운드에서 작업 실행
        thread = threading.Thread(
            target=self._execute_task,
            args=(platform, account_data, keyword_data, content_template,
                  title_data, api_key, phone_number, waiting_min, waiting_max, use_dynamic_ip)
        )
        thread.daemon = True
        thread.start()
        
        return True
    
    def _execute_task(self, platform: str, account_data: pd.DataFrame,
                     keyword_data: pd.DataFrame, content_template: str,
                     title_data: Optional[pd.DataFrame] = None,
                     api_key: str = "", phone_number: str = "",
                     waiting_min: int = 1, waiting_max: int = 3,
                     use_dynamic_ip: bool = False):
        """실제 작업 실행 (백그라운드)"""
        try:
            self.add_log("작업을 시작합니다.", "info")
            
            # 1. 데이터 검증
            self.current_task = "데이터 검증 중..."
            self.progress = 10
            self.add_log("데이터 검증을 시작합니다.", "info")
            
            if account_data.empty:
                raise ValueError("계정 데이터가 비어있습니다.")
            if keyword_data.empty:
                raise ValueError("키워드 데이터가 비어있습니다.")
            
            self.add_log(f"계정 {len(account_data)}개, 키워드 {len(keyword_data)}개 확인", "success")
            
            # 2. 웹드라이버 초기화 (시뮬레이션)
            self.current_task = "웹드라이버 초기화 중..."
            self.progress = 20
            self.add_log("웹드라이버를 초기화합니다.", "info")
            time.sleep(2)  # 시뮬레이션
            self.add_log("웹드라이버 초기화 완료", "success")
            
            # 3. 계정별 작업 수행
            total_accounts = len(account_data)
            for idx, account in account_data.iterrows():
                if not self.is_running:
                    break
                    
                self.current_task = f"계정 {idx+1}/{total_accounts} 처리 중..."
                self.progress = 30 + (idx / total_accounts) * 50
                
                account_name = account.iloc[0] if len(account) > 0 else f"계정_{idx+1}"
                self.add_log(f"계정 '{account_name}' 로그인 시도", "info")
                
                # 키워드별 포스팅 (시뮬레이션)
                for kidx, keyword in keyword_data.iterrows():
                    if not self.is_running:
                        break
                        
                    address = keyword.iloc[0] if len(keyword) > 0 else "주소"
                    company = keyword.iloc[1] if len(keyword) > 1 else "업체"
                    
                    # 콘텐츠 생성
                    content = self._generate_content(content_template, address, company, title_data)
                    
                    # 플랫폼별 포스팅
                    if platform in ["블로그", "둘 다"]:
                        self.add_log(f"블로그 포스팅: {address} - {company}", "info")
                        time.sleep(1)  # 시뮬레이션
                        
                    if platform in ["카페", "둘 다"]:
                        self.add_log(f"카페 포스팅: {address} - {company}", "info")
                        time.sleep(1)  # 시뮬레이션
                    
                    # 대기시간
                    if use_dynamic_ip and random.choice([True, False]):
                        self.add_log("IP 변경 중...", "info")
                        time.sleep(1)
                        
                    wait_time = random.randint(waiting_min, waiting_max)
                    self.add_log(f"{wait_time}분 대기", "info")
                    time.sleep(wait_time * 0.1)  # 시뮬레이션용으로 단축
            
            # 4. 작업 완료
            self.current_task = "작업 완료"
            self.progress = 100
            self.add_log("모든 작업이 완료되었습니다.", "success")
            
        except Exception as e:
            self.add_log(f"작업 중 오류 발생: {str(e)}", "error")
            
        finally:
            self.is_running = False
    
    def _generate_content(self, template: str, address: str, company: str, 
                         title_data: Optional[pd.DataFrame] = None) -> str:
        """콘텐츠 생성"""
        content = template
        
        # 기본 치환
        content = content.replace("%주소%", address)
        content = content.replace("%업체%", company)
        content = content.replace("%썸네일%", "[썸네일 이미지]")
        content = content.replace("%영상%", "[영상 콘텐츠]")
        
        # [본문] 치환 (AI 생성 시뮬레이션)
        if "[본문]" in content:
            ai_content = self._generate_ai_content(address, company)
            content = content.replace("[본문]", ai_content)
        
        return content
    
    def _generate_ai_content(self, address: str, company: str) -> str:
        """AI 콘텐츠 생성 (새로운 Genai 클라이언트 사용)"""
        try:
            # 새로운 Google Genai 클라이언트 사용
            from google import genai
            import streamlit as st
            
            # 세션에서 API 키 가져오기
            api_key = st.session_state.get('api_key', '')
            if not api_key:
                return self._get_fallback_content(address, company)
            
            client = genai.Client(api_key=api_key)
            
            prompt = f"""
            {address}에 위치한 {company}에 대한 블로그 포스팅용 본문을 작성해주세요.
            
            요구사항:
            - 1500자 내외로 작성
            - 전문적이고 신뢰감 있는 톤
            - 고객 입장에서 도움이 되는 정보 포함
            - 자연스러운 한국어로 작성
            
            주제: {company} 서비스 소개 및 특장점
            """
            
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt,
            )
            
            if response and response.text:
                return response.text.strip()
            else:
                return self._get_fallback_content(address, company)
                
        except Exception as e:
            # 오류 발생 시 기본 템플릿 사용
            return self._get_fallback_content(address, company)
    
    def _get_fallback_content(self, address: str, company: str) -> str:
        """AI 생성 실패 시 사용할 기본 콘텐츠"""
        templates = [
            f"{address}에 위치한 {company}는 고객만족을 최우선으로 하는 전문 업체입니다. "
            f"오랜 경험과 노하우를 바탕으로 최상의 서비스를 제공하고 있으며, "
            f"고객의 다양한 요구사항에 맞춤형 솔루션을 제공합니다. "
            f"전문적인 기술력과 체계적인 관리 시스템으로 신뢰할 수 있는 서비스를 약속드립니다.",
            
            f"{company}는 {address} 지역에서 전문성을 인정받고 있는 업체입니다. "
            f"고품질의 서비스와 합리적인 가격으로 많은 고객들의 만족을 얻고 있으며, "
            f"신속하고 정확한 업무 처리로 고객의 시간과 비용을 절약해드립니다. "
            f"언제든지 문의 주시면 친절하고 전문적인 상담을 제공해드리겠습니다.",
            
            f"{address} 지역의 {company}는 축적된 기술력과 풍부한 경험을 바탕으로 "
            f"고객에게 최고의 만족을 드리기 위해 노력하고 있습니다. "
            f"체계적인 품질관리 시스템과 전문 인력을 통해 안전하고 확실한 서비스를 제공하며, "
            f"고객의 입장에서 생각하는 맞춤형 서비스로 신뢰를 쌓아가고 있습니다."
        ]
        return random.choice(templates)
    
    def stop_task(self):
        """작업 중지"""
        self.is_running = False
        self.add_log("사용자에 의해 작업이 중지되었습니다.", "warning")

class StreamlitDataManager:
    """Streamlit 애플리케이션용 데이터 관리자"""
    
    @staticmethod
    def validate_csv_format(df: pd.DataFrame, file_type: str) -> tuple[bool, str]:
        """CSV 파일 형식 검증"""
        if df is None or df.empty:
            return False, "파일이 비어있습니다."
        
        if file_type == "account":
            expected_columns = ["계정명", "비밀번호", "게시판", "장소"]
            if len(df.columns) < 3:
                return False, f"계정 파일은 최소 3개 열이 필요합니다. (계정명, 비밀번호, 게시판)"
                
        elif file_type == "keyword":
            expected_columns = ["주소", "업체", "파일경로", "해시태그"]
            if len(df.columns) < 2:
                return False, f"키워드 파일은 최소 2개 열이 필요합니다. (주소, 업체)"
                
        elif file_type == "title":
            if len(df.columns) < 1:
                return False, f"제목 파일은 최소 1개 열이 필요합니다. (제목)"
        
        return True, "형식이 올바릅니다."
    
    @staticmethod
    def save_cache(data: Dict[str, Any], cache_file: str = "cache/.streamlit_cache"):
        """캐시 저장"""
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    @staticmethod
    def load_cache(cache_file: str = "cache/.streamlit_cache") -> Dict[str, Any]:
        """캐시 로드"""
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

class StreamlitIntegration:
    """기존 모듈들과의 통합을 위한 클래스"""
    
    def __init__(self):
        self.task_manager = StreamlitTaskManager()
        self.data_manager = StreamlitDataManager()
    
    def execute_posting_task(self, config: Dict[str, Any]) -> bool:
        """포스팅 작업 실행"""
        return self.task_manager.start_task(
            platform=config.get('platform', '블로그'),
            account_data=config.get('account_data'),
            keyword_data=config.get('keyword_data'),
            content_template=config.get('content_template', ''),
            title_data=config.get('title_data'),
            api_key=config.get('api_key', ''),
            phone_number=config.get('phone_number', ''),
            waiting_min=config.get('waiting_min', 1),
            waiting_max=config.get('waiting_max', 3),
            use_dynamic_ip=config.get('use_dynamic_ip', False)
        )
    
    def get_task_status(self) -> Dict[str, Any]:
        """작업 상태 조회"""
        return {
            'is_running': self.task_manager.is_running,
            'progress': self.task_manager.progress,
            'current_task': self.task_manager.current_task,
            'logs': self.task_manager.logs[-10:]  # 최근 10개 로그
        }
    
    def stop_task(self):
        """작업 중지"""
        self.task_manager.stop_task()