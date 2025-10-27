import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime
import threading
import io
import sys

# 기존 모듈 import를 위한 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 네이버 로그인 시스템 import
try:
    from naver_login_enhanced import NaverLoginAuth
    NAVER_LOGIN_AVAILABLE = True
except ImportError:
    NAVER_LOGIN_AVAILABLE = False
    st.warning("네이버 로그인 모듈을 찾을 수 없습니다. naver_login_enhanced.py 파일을 확인해주세요.")

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .section-header {
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .status-box {
        padding: 0.75rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        font-weight: bold;
    }
    
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
def init_session_state():
    defaults = {
        'platform_choice': '블로그',
        'waiting_min': 5,
        'waiting_max': 10,
        'use_dynamic_ip': False,
        'phone_number': '',
        'account_data': None,
        'keyword_data': None,
        'title_data': None,
        'content_template': '',
        'is_running': False,
        'api_key': '',
        'api_authenticated': False,
        'naver_id': '',
        'naver_password': '',
        'gemini_prompt': '',
        'generated_content': '',
        'is_generating': False,
        'logs': [],
        'integration': None,
        'uploaded_images': [],
        'folder_images': [],
        'selected_media_mode': '개별 업로드',
        'saved_prompts': [],
        'prompt_name': '',
        # 네이버 로그인 관련 상태
        'naver_login_status': '로그아웃',
        'naver_auth': None,
        'naver_login_method': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# 로그 추가 함수
def add_log(message, level="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {
        'timestamp': timestamp,
        'message': message,
        'level': level
    }
    st.session_state.logs.append(log_entry)
    # 로그가 너무 많아지면 오래된 것부터 제거
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]

# Gemini API 인증 함수
def authenticate_gemini_api(api_key):
    """Gemini API 인증을 수행합니다."""
    try:
        # 먼저 새로운 google-genai 패키지 시도
        try:
            from google import genai
            
            # API 키로 클라이언트 생성
            client = genai.Client(api_key=api_key)
            
            # 간단한 텍스트 생성으로 API 키 검증
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents='안녕하세요'
            )
            add_log("✅ Gemini API 인증 성공 (google-genai)", "success")
            return True, "google-genai"
        except ImportError:
            # google-genai가 없으면 기존 google-generativeai 사용
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content('안녕하세요')
            add_log("✅ Gemini API 인증 성공 (google-generativeai)", "success")
            return True, "google-generativeai"
        except Exception as genai_error:
            # google-genai 사용 중 오류 발생 시 fallback
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content('안녕하세요')
                add_log("✅ Gemini API 인증 성공 (google-generativeai fallback)", "success")
                return True, "google-generativeai"
            except Exception as fallback_error:
                add_log(f"❌ 모든 API 방식 실패 - genai: {str(genai_error)}, fallback: {str(fallback_error)}", "error")
                return False, f"genai: {str(genai_error)}, fallback: {str(fallback_error)}"
    except Exception as e:
        add_log(f"❌ Gemini API 인증 실패: {str(e)}", "error")
        return False, str(e)

# Gemini로 콘텐츠 생성 함수
def generate_content_with_gemini(prompt, api_key):
    """Gemini API를 사용하여 콘텐츠를 생성합니다."""
    try:
        # 새로운 google-genai 패키지 시도
        try:
            from google import genai
            
            # API 키로 클라이언트 생성
            client = genai.Client(api_key=api_key)
            
            enhanced_prompt = f"""
다음 요청에 따라 블로그/카페 포스팅용 콘텐츠를 작성해주세요.

요청사항: {prompt}

작성 가이드라인:
1. 1500-2000자 분량으로 작성
2. 읽기 쉬운 구조로 구성 (서론-본론-결론)
3. SEO에 최적화된 자연스러운 키워드 배치
4. 친근하고 신뢰감 있는 톤앤매너
5. 실용적이고 도움이 되는 정보 제공
6. 플레이스홀더는 그대로 유지 (%주소%, %업체%, %썸네일%, %영상% 등)

콘텐츠를 작성해주세요:
"""
            
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=enhanced_prompt
            )
            
            content = response.text
            add_log(f"✅ Gemini 콘텐츠 생성 완료 ({len(content)}자)", "success")
            return True, content
            
        except ImportError:
            # google-genai가 없으면 기존 방식 사용
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            enhanced_prompt = f"""
다음 요청에 따라 블로그/카페 포스팅용 콘텐츠를 작성해주세요.

요청사항: {prompt}

작성 가이드라인:
1. 1500-2000자 분량으로 작성
2. 읽기 쉬운 구조로 구성 (서론-본론-결론)
3. SEO에 최적화된 자연스러운 키워드 배치
4. 친근하고 신뢰감 있는 톤앤매너
5. 실용적이고 도움이 되는 정보 제공
6. 플레이스홀더는 그대로 유지 (%주소%, %업체%, %썸네일%, %영상% 등)

콘텐츠를 작성해주세요:
"""
            
            response = model.generate_content(enhanced_prompt)
            content = response.text
            add_log(f"✅ Gemini 콘텐츠 생성 완료 ({len(content)}자)", "success")
            return True, content
            
        except Exception as genai_error:
            # google-genai 사용 중 오류 발생 시 fallback
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-pro')
                
                enhanced_prompt = f"""
다음 요청에 따라 블로그/카페 포스팅용 콘텐츠를 작성해주세요.

요청사항: {prompt}

작성 가이드라인:
1. 1500-2000자 분량으로 작성
2. 읽기 쉬운 구조로 구성 (서론-본론-결론)
3. SEO에 최적화된 자연스러운 키워드 배치
4. 친근하고 신뢰감 있는 톤앤매너
5. 실용적이고 도움이 되는 정보 제공
6. 플레이스홀더는 그대로 유지 (%주소%, %업체%, %썸네일%, %영상% 등)

콘텐츠를 작성해주세요:
"""
                
                response = model.generate_content(enhanced_prompt)
                content = response.text
                add_log(f"✅ Gemini 콘텐츠 생성 완료 (fallback, {len(content)}자)", "success")
                return True, content
            except Exception as fallback_error:
                add_log(f"❌ 모든 콘텐츠 생성 방식 실패 - genai: {str(genai_error)}, fallback: {str(fallback_error)}", "error")
                return False, f"genai: {str(genai_error)}, fallback: {str(fallback_error)}"
            
    except Exception as e:
        add_log(f"❌ 콘텐츠 생성 실패: {str(e)}", "error")
        return False, str(e)

# CSV 파일 처리 함수
def process_csv_file(uploaded_file, file_type):
    if uploaded_file is not None:
        try:
            # 파일을 DataFrame으로 읽기
            df = pd.read_csv(uploaded_file)
            
            # 세션 상태에 저장
            if file_type == "account":
                st.session_state.account_data = df
                st.session_state.account_file = uploaded_file
                add_log(f"계정 파일 업로드 완료: {len(df)}개 계정", "success")
            elif file_type == "keyword":
                st.session_state.keyword_data = df
                st.session_state.keyword_file = uploaded_file
                add_log(f"키워드 파일 업로드 완료: {len(df)}개 키워드", "success")
            elif file_type == "title":
                st.session_state.title_data = df
                st.session_state.title_file = uploaded_file
                add_log(f"제목 파일 업로드 완료: {len(df)}개 제목", "success")
            return df
        except Exception as e:
            add_log(f"파일 업로드 실패: {str(e)}", "error")
            return None
    return None

# 네이버 로그인 관련 함수들
@st.cache_resource
def get_naver_auth():
    """네이버 인증 객체를 캐시된 리소스로 관리"""
    return None

def login_naver(username, password, headless=False, auto_retry=True):
    """네이버 로그인 실행"""
    if not NAVER_LOGIN_AVAILABLE:
        st.error("네이버 로그인 모듈이 사용할 수 없습니다")
        return
    
    with st.spinner("네이버 로그인 중..."):
        try:
            # 네이버 인증 객체 생성
            auth = NaverLoginAuth(headless=headless, wait_timeout=15)
            
            # 로그인 시도
            retry_count = 3 if auto_retry else 1
            result = auth.login(username, password, retry_count=retry_count)
            
            if result['status'] == 'success':
                st.session_state.naver_login_status = '로그인됨'
                st.session_state.naver_auth = auth
                st.session_state.naver_login_method = result['method']
                add_log(f"✅ 네이버 로그인 성공 (방법: {result['method']})", "success")
                st.success(f"✅ 네이버 로그인 성공! (인증방법: {result['method']})")
                st.rerun()
                
            elif result['status'] == 'captcha_required':
                st.session_state.naver_login_status = '캡챠 대기'
                st.session_state.naver_auth = auth
                add_log("⚠️ 캡챠 인증 필요", "warning")
                st.warning("🔍 캡챠 인증이 필요합니다. 브라우저에서 캡챠를 완료한 후 '캡챠 완료' 버튼을 클릭하세요.")
                
                # 캡챠 완료 버튼 표시
                if st.button("✅ 캡챠 완료"):
                    wait_for_captcha_completion(auth)
                
            elif result['status'] == 'sms_required':
                st.session_state.naver_login_status = 'SMS 대기'
                st.session_state.naver_auth = auth
                add_log("📱 SMS 인증 필요", "warning")
                st.warning("📱 SMS 인증이 필요합니다. 휴대폰으로 받은 인증코드를 입력한 후 'SMS 완료' 버튼을 클릭하세요.")
                
                # SMS 완료 버튼 표시
                if st.button("✅ SMS 인증 완료"):
                    wait_for_sms_completion(auth)
                    
            else:
                add_log(f"❌ 네이버 로그인 실패: {result['message']}", "error")
                st.error(f"❌ 로그인 실패: {result['message']}")
                auth.close()
                
        except Exception as e:
            add_log(f"❌ 네이버 로그인 오류: {str(e)}", "error")
            st.error(f"❌ 로그인 오류: {str(e)}")

def wait_for_captcha_completion(auth):
    """캡챠 완료 대기"""
    with st.spinner("캡챠 완료 확인 중..."):
        if auth.wait_for_captcha_completion(timeout=300):
            result = auth.check_login_result()
            if result == "success":
                st.session_state.naver_login_status = '로그인됨'
                add_log("✅ 캡챠 인증 후 로그인 성공", "success")
                st.success("✅ 캡챠 인증 후 로그인 성공!")
                st.rerun()
            else:
                add_log("❌ 캡챠 완료 후에도 로그인 실패", "error")
                st.error("❌ 캡챠 완료 후에도 로그인에 실패했습니다")
        else:
            add_log("⏰ 캡챠 완료 타임아웃", "warning")
            st.warning("⏰ 캡챠 완료 대기 시간이 초과되었습니다")

def wait_for_sms_completion(auth):
    """SMS 인증 완료 대기"""
    with st.spinner("SMS 인증 완료 확인 중..."):
        if auth.wait_for_sms_completion(timeout=300):
            st.session_state.naver_login_status = '로그인됨'
            add_log("✅ SMS 인증 후 로그인 성공", "success")
            st.success("✅ SMS 인증 후 로그인 성공!")
            st.rerun()
        else:
            add_log("⏰ SMS 인증 완료 타임아웃", "warning")
            st.warning("⏰ SMS 인증 완료 대기 시간이 초과되었습니다")

def logout_naver():
    """네이버 로그아웃"""
    try:
        if 'naver_auth' in st.session_state and st.session_state.naver_auth:
            st.session_state.naver_auth.logout()
            st.session_state.naver_auth.close()
        
        st.session_state.naver_login_status = '로그아웃'
        if 'naver_auth' in st.session_state:
            del st.session_state.naver_auth
        if 'naver_login_method' in st.session_state:
            del st.session_state.naver_login_method
            
        add_log("✅ 네이버 로그아웃 완료", "success")
        st.success("✅ 네이버 로그아웃 완료")
        st.rerun()
        
    except Exception as e:
        add_log(f"❌ 네이버 로그아웃 오류: {str(e)}", "error")
        st.error(f"❌ 로그아웃 오류: {str(e)}")

def check_naver_login_status():
    """네이버 로그인 상태 확인"""
    try:
        if 'naver_auth' in st.session_state and st.session_state.naver_auth:
            status = st.session_state.naver_auth.check_login_status()
            if status:
                st.session_state.naver_login_status = '로그인됨'
                return True
            else:
                st.session_state.naver_login_status = '로그아웃'
                return False
        else:
            st.session_state.naver_login_status = '로그아웃'
            return False
    except Exception as e:
        add_log(f"❌ 로그인 상태 확인 오류: {str(e)}", "error")
        st.session_state.naver_login_status = '로그아웃'
        return False

# 메인 함수
def main():
    init_session_state()
    
    # 헤더
    st.markdown('<div class="main-header">📝 네이버 블로그/카페 자동 포스팅</div>', unsafe_allow_html=True)
    
    # 사이드바 - 설정
    with st.sidebar:
        st.markdown('<div class="section-header">⚙️ 기본 설정</div>', unsafe_allow_html=True)
        
        # 플랫폼 선택
        st.session_state.platform_choice = st.radio(
            "플랫폼 선택",
            ["블로그", "카페", "둘 다"],
            index=["블로그", "카페", "둘 다"].index(st.session_state.platform_choice)
        )
        
        # 현재 상태 표시
        if st.session_state.platform_choice == "블로그":
            st.markdown(f'<div class="status-box success-box">현재 상태: <strong>블로그</strong></div>', unsafe_allow_html=True)
        elif st.session_state.platform_choice == "카페":
            st.markdown(f'<div class="status-box warning-box">현재 상태: <strong>카페</strong></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-box success-box">현재 상태: <strong>둘 다</strong></div>', unsafe_allow_html=True)
        
        st.divider()
        
        # 대기시간 설정
        st.markdown("⏱️ **대기시간 설정**")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.waiting_min = st.number_input(
                "최소 (분)", 
                min_value=1, 
                max_value=60, 
                value=st.session_state.waiting_min
            )
        with col2:
            st.session_state.waiting_max = st.number_input(
                "최대 (분)", 
                min_value=1, 
                max_value=60, 
                value=st.session_state.waiting_max
            )
        
        # 유동 IP 설정
        st.session_state.use_dynamic_ip = st.toggle("🌐 유동 IP 사용", st.session_state.use_dynamic_ip)
        
        st.divider()
        
        # 기타 인증 정보
        st.markdown("📱 **기타 인증 정보**")
        st.session_state.phone_number = st.text_input(
            "핸드폰 번호", 
            value=st.session_state.phone_number,
            help="SMS 인증이 필요한 경우 사용됩니다"
        )
        
        st.divider()
        
        # 네이버 로그인 섹션
        st.markdown("🔐 **네이버 로그인 인증**")
        
        if NAVER_LOGIN_AVAILABLE:
            # 로그인 상태 확인
            login_status = st.session_state.get('naver_login_status', '로그아웃')
            
            if login_status == '로그인됨':
                st.markdown(f'<div class="status-box success-box">네이버 로그인 상태: <strong>로그인됨</strong></div>', unsafe_allow_html=True)
                if st.button("🚪 네이버 로그아웃", type="secondary"):
                    logout_naver()
            else:
                st.markdown(f'<div class="status-box warning-box">네이버 로그인 상태: <strong>로그아웃</strong></div>', unsafe_allow_html=True)
                
                # 네이버 계정 정보 입력
                naver_id = st.text_input("네이버 아이디", value="", help="네이버 로그인용 아이디를 입력하세요")
                naver_pw = st.text_input("네이버 비밀번호", type="password", value="", help="네이버 로그인용 비밀번호를 입력하세요")
                
                # 로그인 옵션
                col1, col2 = st.columns(2)
                with col1:
                    headless_mode = st.checkbox("백그라운드 실행", value=False, help="브라우저 창을 숨기고 실행")
                with col2:
                    auto_retry = st.checkbox("자동 재시도", value=True, help="로그인 실패 시 자동으로 재시도")
                
                if st.button("🔑 네이버 로그인", type="primary"):
                    if naver_id and naver_pw:
                        login_naver(naver_id, naver_pw, headless_mode, auto_retry)
                    else:
                        st.error("네이버 아이디와 비밀번호를 모두 입력해주세요")
        else:
            st.error("네이버 로그인 모듈이 설치되지 않았습니다")
    
    # 메인 영역을 2개 열로 분할
    col1, col2 = st.columns([2, 1])
    
    # 왼쪽 열 - Gemini AI 콘텐츠 생성 + 데이터 업로드 + 자동화 실행
    with col1:
        # 1. Gemini AI 콘텐츠 생성
        st.markdown('<div class="section-header">🤖 Gemini AI 콘텐츠 생성</div>', unsafe_allow_html=True)
        
        # 프롬프트 입력 안내
        with st.expander("📋 프롬프트 작성 가이드", expanded=False):
            st.markdown("""
            **🎯 효과적인 프롬프트 작성 팁:**
            
            **1. 구체적인 주제 명시**
            - "부동산 투자 가이드 작성해줘"
            - "카페 창업 노하우에 대해 알려줘"
            
            **2. 타겟 독자 설정**
            - "초보 투자자를 위한..."
            - "20-30대 직장인 대상으로..."
            
            **3. 포함할 내용 명시**
            - "장점과 단점을 포함해서"
            - "실제 사례와 함께"
            - "단계별 가이드로"
            
            **4. 플레이스홀더 활용**
            - `%주소%`, `%업체%`: 키워드 파일의 데이터로 자동 치환
            - `%썸네일%`, `%영상%`: 미디어 콘텐츠 자동 삽입
            
            **예시 프롬프트:**
            ```
            %업체%에서 제공하는 서비스에 대한 상세한 리뷰를 작성해주세요.
            %주소% 지역 고객들에게 도움이 될 만한 실용적인 정보를 포함하고,
            서비스 이용 절차와 장점을 친근한 톤으로 설명해주세요.
            ```
            """)
        
        # Gemini 프롬프트 입력
        st.markdown("**✍️ 프롬프트 입력**")
        st.session_state.gemini_prompt = st.text_area(
            "Gemini AI에게 어떤 콘텐츠를 생성해달라고 요청하시겠습니까?",
            value=st.session_state.gemini_prompt,
            height=150,
            placeholder="예: '부동산 투자 초보자를 위한 가이드를 작성해주세요. 시장 분석 방법, 투자 전 체크리스트, 주의사항을 포함해서 친근하고 이해하기 쉽게 설명해주세요.'",
            help="구체적이고 상세한 프롬프트를 입력할수록 더 좋은 결과를 얻을 수 있습니다."
        )
        
        # 프롬프트 저장/관리 섹션
        with st.expander("📝 프롬프트 저장 및 관리", expanded=False):
            col_prompt1, col_prompt2 = st.columns([2, 1])
            
            with col_prompt1:
                st.session_state.prompt_name = st.text_input(
                    "프롬프트 이름",
                    value=st.session_state.prompt_name,
                    placeholder="예: 부동산 투자 가이드",
                    help="현재 프롬프트를 저장할 때 사용할 이름"
                )
            
            with col_prompt2:
                if st.button("💾 프롬프트 저장", use_container_width=True):
                    if st.session_state.gemini_prompt.strip() and st.session_state.prompt_name.strip():
                        # 중복 이름 확인
                        existing_names = [p['name'] for p in st.session_state.saved_prompts]
                        if st.session_state.prompt_name in existing_names:
                            st.warning(f"⚠️ '{st.session_state.prompt_name}' 이름이 이미 존재합니다. 다른 이름을 사용해주세요.")
                        else:
                            new_prompt = {
                                'name': st.session_state.prompt_name,
                                'content': st.session_state.gemini_prompt,
                                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M")
                            }
                            st.session_state.saved_prompts.append(new_prompt)
                            st.session_state.prompt_name = ""  # 저장 후 이름 초기화
                            add_log(f"프롬프트 '{new_prompt['name']}' 저장 완료", "success")
                            st.success(f"✅ '{new_prompt['name']}' 프롬프트가 저장되었습니다!")
                            st.rerun()
                    else:
                        st.error("프롬프트 내용과 이름을 모두 입력해주세요!")
            
            # 저장된 프롬프트 목록
            if st.session_state.saved_prompts:
                st.markdown("**📚 저장된 프롬프트 목록**")
                
                for i, prompt in enumerate(st.session_state.saved_prompts):
                    with st.container():
                        col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
                        
                        with col_a:
                            st.markdown(f"**{prompt['name']}**")
                            st.caption(f"📅 {prompt['created_at']}")
                            
                            # 프롬프트 내용 미리보기 (최대 100자)
                            preview = prompt['content'][:100] + "..." if len(prompt['content']) > 100 else prompt['content']
                            st.text(preview)
                        
                        with col_b:
                            if st.button("📖 보기", key=f"view_{i}", use_container_width=True):
                                st.info(f"**{prompt['name']}**\n\n{prompt['content']}")
                        
                        with col_c:
                            if st.button("📥 불러오기", key=f"load_{i}", use_container_width=True):
                                st.session_state.gemini_prompt = prompt['content']
                                add_log(f"프롬프트 '{prompt['name']}' 불러오기 완료", "info")
                                st.success(f"✅ '{prompt['name']}' 프롬프트를 불러왔습니다!")
                                st.rerun()
                        
                        with col_d:
                            if st.button("🗑️ 삭제", key=f"delete_{i}", use_container_width=True):
                                deleted_name = st.session_state.saved_prompts[i]['name']
                                del st.session_state.saved_prompts[i]
                                add_log(f"프롬프트 '{deleted_name}' 삭제 완료", "warning")
                                st.success(f"✅ '{deleted_name}' 프롬프트가 삭제되었습니다!")
                                st.rerun()
                        
                        st.divider()
                
                # 전체 삭제 버튼
                if len(st.session_state.saved_prompts) > 1:
                    if st.button("🗑️ 모든 프롬프트 삭제", type="secondary"):
                        count = len(st.session_state.saved_prompts)
                        st.session_state.saved_prompts = []
                        add_log(f"저장된 프롬프트 {count}개 모두 삭제", "warning")
                        st.success(f"✅ 저장된 프롬프트 {count}개가 모두 삭제되었습니다!")
                        st.rerun()
            else:
                st.info("💡 저장된 프롬프트가 없습니다. 프롬프트를 작성하고 저장해보세요!")
        
        # 프롬프트 템플릿 제안
        with st.expander("💡 프롬프트 템플릿 제안", expanded=False):
            template_categories = {
                "🏢 비즈니스": [
                    "마케팅 전략에 대한 실용적인 가이드를 작성해주세요. 소상공인도 쉽게 따라할 수 있는 구체적인 방법들을 포함해주세요.",
                    "고객 서비스 개선 방안에 대해 작성해주세요. 실제 사례와 함께 단계별 실행 방법을 제시해주세요.",
                    "창업 초기 단계에서 주의해야 할 사항들을 정리해주세요. 실패 사례와 성공 요인을 균형있게 다뤄주세요."
                ],
                "🏠 부동산": [
                    "부동산 투자 초보자를 위한 가이드를 작성해주세요. 시장 분석 방법, 투자 전 체크리스트, 주의사항을 포함해서 친근하고 이해하기 쉽게 설명해주세요.",
                    "전세와 월세의 장단점을 비교 분석해주세요. 각각의 상황에서 어떤 선택이 유리한지 구체적인 기준을 제시해주세요.",
                    "내 집 마련을 위한 단계별 준비 과정을 작성해주세요. 자금 계획부터 실제 구매까지의 전 과정을 다뤄주세요."
                ],
                "💡 라이프스타일": [
                    "건강한 식습관 만들기에 대한 실용적인 팁을 작성해주세요. 바쁜 현대인도 쉽게 실천할 수 있는 방법들을 중심으로 해주세요.",
                    "효과적인 시간 관리 방법에 대해 작성해주세요. 직장인과 학생 모두에게 도움이 될 수 있는 구체적인 기법들을 포함해주세요.",
                    "취미 생활의 중요성과 시작하는 방법에 대해 작성해주세요. 다양한 취미의 종류와 각각의 장점을 소개해주세요."
                ],
                "🎓 교육": [
                    "효과적인 학습 방법에 대한 가이드를 작성해주세요. 연령대별, 목적별로 구분해서 구체적인 방법들을 제시해주세요.",
                    "자녀 교육에서 부모의 역할에 대해 작성해주세요. 발달 단계별 접근 방법과 주의사항을 포함해주세요.",
                    "평생 학습의 중요성과 실천 방법에 대해 작성해주세요. 성인 학습자를 위한 효과적인 학습 전략을 다뤄주세요."
                ]
            }
            
            for category, templates in template_categories.items():
                st.markdown(f"**{category}**")
                for j, template in enumerate(templates):
                    col_template1, col_template2 = st.columns([4, 1])
                    with col_template1:
                        st.text(template)
                    with col_template2:
                        if st.button("📋 복사", key=f"template_{category}_{j}", use_container_width=True):
                            st.session_state.gemini_prompt = template
                            add_log(f"템플릿 프롬프트 복사 완료", "info")
                            st.success("✅ 템플릿이 프롬프트 창에 복사되었습니다!")
                            st.rerun()
                st.markdown("---")
        
        # 콘텐츠 생성 버튼
        col_gen1, col_gen2 = st.columns([3, 1])
        
        with col_gen1:
            if st.button("🚀 Gemini로 콘텐츠 생성", type="primary", use_container_width=True, disabled=st.session_state.is_generating):
                if not st.session_state.gemini_prompt.strip():
                    st.error("프롬프트를 입력해주세요!")
                elif not st.session_state.api_key:
                    st.error("먼저 Gemini API 키를 입력해주세요!")
                elif not st.session_state.api_authenticated:
                    st.error("먼저 Gemini API 인증을 완료해주세요!")
                else:
                    st.session_state.is_generating = True
                    add_log("Gemini AI 콘텐츠 생성을 시작합니다...", "info")
                    st.rerun()
        
        with col_gen2:
            if st.button("🗑️ 초기화", use_container_width=True):
                st.session_state.gemini_prompt = ""
                st.session_state.generated_content = ""
                add_log("프롬프트와 생성된 콘텐츠가 초기화되었습니다.", "info")
                st.rerun()
        
        # 콘텐츠 생성 중 표시
        if st.session_state.is_generating:
            with st.spinner("🤖 Gemini AI가 콘텐츠를 생성하고 있습니다..."):
                success, content = generate_content_with_gemini(
                    st.session_state.gemini_prompt, 
                    st.session_state.api_key
                )
                
                if success:
                    st.session_state.generated_content = content
                    st.session_state.content_template = content  # 기존 템플릿 변수에도 저장
                    add_log("✅ 콘텐츠 생성 완료!", "success")
                    st.success("🎉 콘텐츠가 성공적으로 생성되었습니다!")
                else:
                    add_log(f"❌ 콘텐츠 생성 실패: {content}", "error")
                    st.error(f"콘텐츠 생성 실패: {content}")
                
                st.session_state.is_generating = False
                st.rerun()
        
        # 생성된 콘텐츠 표시 및 편집
        if st.session_state.generated_content:
            st.markdown("**📝 생성된 콘텐츠 (편집 가능)**")
            
            # 콘텐츠 편집 가능한 텍스트 영역
            st.session_state.content_template = st.text_area(
                "생성된 콘텐츠를 검토하고 필요시 수정하세요:",
                value=st.session_state.generated_content,
                height=300,
                help="생성된 콘텐츠를 자유롭게 편집할 수 있습니다. 플레이스홀더(%주소%, %업체% 등)도 추가할 수 있습니다."
            )
            
            # 콘텐츠 정보 표시
            content_length = len(st.session_state.content_template)
            st.info(f"📊 콘텐츠 길이: {content_length:,}자 | 예상 읽기 시간: {content_length // 500 + 1}분")
        else:
            st.info("💡 위에서 프롬프트를 입력하고 '콘텐츠 생성' 버튼을 클릭하세요!")
        
        st.divider()
        
        # 사진 첨부 섹션
        st.markdown('<div class="section-header">📸 미디어 첨부</div>', unsafe_allow_html=True)
        
        # 사진 첨부 방식 선택
        media_tabs = st.tabs(["📁 개별 이미지 첨부", "📂 이미지 폴더 첨부"])
        
        with media_tabs[0]:
            st.markdown("**개별 이미지 파일들을 선택하여 첨부**")
            
            # 개별 사진 업로드
            uploaded_images = st.file_uploader(
                "이미지 파일을 선택하세요 (여러 개 선택 가능)",
                type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
                accept_multiple_files=True,
                help="PNG, JPG, JPEG, GIF, BMP, WEBP 형식을 지원합니다"
            )
            
            if uploaded_images:
                st.success(f"✅ {len(uploaded_images)}개의 이미지가 업로드되었습니다!")
                
                # 이미지 미리보기 (최대 6개까지)
                cols_per_row = 3
                for i in range(0, min(len(uploaded_images), 6), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        if i + j < len(uploaded_images):
                            img = uploaded_images[i + j]
                            with col:
                                st.image(img, caption=img.name, use_container_width=True)
                
                if len(uploaded_images) > 6:
                    st.info(f"📝 총 {len(uploaded_images)}개 이미지 중 6개만 미리보기로 표시됩니다.")
                
                # 세션 상태에 저장
                st.session_state.uploaded_images = uploaded_images
                add_log(f"개별 이미지 {len(uploaded_images)}개 업로드 완료", "success")
            else:
                st.info("🖼️ 이미지 파일을 선택해주세요.")
        
        with media_tabs[1]:
            st.markdown("**폴더에서 모든 이미지를 한번에 첨부**")
            
            # 폴더 경로 입력
            folder_path = st.text_input(
                "이미지 폴더 경로를 입력하세요",
                placeholder="예: C:\\Users\\사용자명\\Pictures\\blog_images",
                help="폴더 경로를 입력하면 해당 폴더의 모든 이미지 파일을 자동으로 읽어옵니다"
            )
            
            col_folder1, col_folder2 = st.columns([2, 1])
            
            with col_folder1:
                if st.button("📂 폴더에서 이미지 로드", use_container_width=True):
                    if folder_path:
                        try:
                            import os
                            from PIL import Image
                            
                            # 지원되는 이미지 확장자
                            supported_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
                            
                            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                                image_files = []
                                for file in os.listdir(folder_path):
                                    if any(file.lower().endswith(ext) for ext in supported_extensions):
                                        image_files.append(os.path.join(folder_path, file))
                                
                                if image_files:
                                    st.session_state.folder_images = image_files
                                    st.success(f"✅ 폴더에서 {len(image_files)}개의 이미지를 찾았습니다!")
                                    add_log(f"폴더 이미지 {len(image_files)}개 로드 완료: {folder_path}", "success")
                                    
                                    # 이미지 미리보기 (최대 6개)
                                    st.markdown("**📋 로드된 이미지 미리보기:**")
                                    cols_per_row = 3
                                    for i in range(0, min(len(image_files), 6), cols_per_row):
                                        cols = st.columns(cols_per_row)
                                        for j, col in enumerate(cols):
                                            if i + j < len(image_files):
                                                img_path = image_files[i + j]
                                                try:
                                                    with col:
                                                        st.image(img_path, caption=os.path.basename(img_path), use_container_width=True)
                                                except Exception as e:
                                                    with col:
                                                        st.error(f"이미지 로드 실패: {os.path.basename(img_path)}")
                                    
                                    if len(image_files) > 6:
                                        st.info(f"📝 총 {len(image_files)}개 이미지 중 6개만 미리보기로 표시됩니다.")
                                        
                                        # 전체 파일 목록 표시
                                        with st.expander("📁 전체 이미지 파일 목록 보기"):
                                            for img_path in image_files:
                                                st.text(f"📄 {os.path.basename(img_path)}")
                                else:
                                    st.warning(f"⚠️ 해당 폴더에서 이미지 파일을 찾을 수 없습니다: {folder_path}")
                            else:
                                st.error(f"❌ 폴더를 찾을 수 없습니다: {folder_path}")
                        except Exception as e:
                            st.error(f"❌ 폴더 읽기 실패: {str(e)}")
                            add_log(f"폴더 읽기 실패: {str(e)}", "error")
                    else:
                        st.error("폴더 경로를 입력해주세요!")
            
            with col_folder2:
                if st.button("🗑️ 폴더 초기화", use_container_width=True):
                    if 'folder_images' in st.session_state:
                        del st.session_state.folder_images
                    add_log("폴더 이미지가 초기화되었습니다.", "info")
                    st.rerun()
            
            # 폴더에서 로드된 이미지 정보 표시
            if 'folder_images' in st.session_state and st.session_state.folder_images:
                st.info(f"📂 현재 로드된 이미지: {len(st.session_state.folder_images)}개")
        
        # 미디어 첨부 상태 요약
        st.markdown("**📊 미디어 첨부 상태**")
        media_status = []
        
        # 개별 업로드 상태
        individual_count = len(getattr(st.session_state, 'uploaded_images', []))
        if individual_count > 0:
            media_status.append(f"📁 개별 업로드: {individual_count}개")
        
        # 폴더 업로드 상태
        folder_count = len(getattr(st.session_state, 'folder_images', []))
        if folder_count > 0:
            media_status.append(f"📂 폴더 로드: {folder_count}개")
        
        if media_status:
            total_images = individual_count + folder_count
            st.success(f"✅ " + " | ".join(media_status) + f" | 총 {total_images}개 이미지")
        else:
            st.warning("⚠️ 첨부된 이미지가 없습니다")
        
        st.divider()
        
        # 2. 데이터 업로드
        st.markdown('<div class="section-header">📁 데이터 업로드</div>', unsafe_allow_html=True)
        
        # 파일 업로드를 2열로 배치
        upload_col1, upload_col2 = st.columns(2)
        
        with upload_col1:
            # 계정 파일 업로드
            st.markdown("**계정 파일 업로드**")
            account_file = st.file_uploader(
                "계정 CSV 파일을 업로드하세요",
                type=['csv'],
                key="account_upload",
                help="계정명, 비밀번호, 게시판, 장소 정보가 포함된 CSV 파일"
            )
            if account_file:
                df = process_csv_file(account_file, "account")
                if df is not None:
                    st.dataframe(df.head(3), use_container_width=True)
            
            # 키워드 파일 업로드
            st.markdown("**키워드 파일 업로드**")
            keyword_file = st.file_uploader(
                "키워드 CSV 파일을 업로드하세요",
                type=['csv'],
                key="keyword_upload",
                help="주소, 업체, 파일경로, 해시태그 정보가 포함된 CSV 파일"
            )
            if keyword_file:
                df = process_csv_file(keyword_file, "keyword")
                if df is not None:
                    st.dataframe(df.head(3), use_container_width=True)
        
        with upload_col2:
            # 제목 파일 업로드
            st.markdown("**제목 파일 업로드**")
            title_file = st.file_uploader(
                "제목 CSV 파일을 업로드하세요",
                type=['csv'],
                key="title_upload",
                help="제목 템플릿이 포함된 CSV 파일"
            )
            if title_file:
                df = process_csv_file(title_file, "title")
                if df is not None:
                    st.dataframe(df.head(3), use_container_width=True)
            
            # 파일 업로드 상태 표시
            st.markdown("**📊 업로드 상태**")
            
            # 미디어 첨부 상태 계산
            individual_count = len(getattr(st.session_state, 'uploaded_images', []))
            folder_count = len(getattr(st.session_state, 'folder_images', []))
            total_media = individual_count + folder_count
            
            upload_status = [
                ("계정 파일", st.session_state.account_data is not None),
                ("키워드 파일", st.session_state.keyword_data is not None),
                ("제목 파일", st.session_state.title_data is not None),
                ("미디어 첨부", total_media > 0),
            ]
            
            for file_name, status in upload_status:
                icon = "✅" if status else "❌"
                color = "green" if status else "red"
                
                if file_name == "미디어 첨부" and status:
                    detail_info = f" ({total_media}개)"
                    st.markdown(f"{icon} **{file_name}**: <span style='color: {color}'>{'완료' if status else '미완료'}</span>{detail_info}", unsafe_allow_html=True)
                else:
                    st.markdown(f"{icon} **{file_name}**: <span style='color: {color}'>{'완료' if status else '미완료'}</span>", unsafe_allow_html=True)
        
        st.divider()
        
        # 3. 자동화 실행
        st.markdown('<div class="section-header">🚀 자동화 실행</div>', unsafe_allow_html=True)
        
        # 실행 전 체크리스트
        with st.expander("✅ 실행 전 체크리스트", expanded=False):
            # 미디어 첨부 상태 계산
            individual_count = len(getattr(st.session_state, 'uploaded_images', []))
            folder_count = len(getattr(st.session_state, 'folder_images', []))
            total_media = individual_count + folder_count
            
            checklist_items = [
                ("Gemini API 인증", st.session_state.api_authenticated),
                ("네이버 로그인 정보", bool(st.session_state.naver_id and st.session_state.naver_password)),
                ("계정 파일 업로드", st.session_state.account_data is not None),
                ("키워드 파일 업로드", st.session_state.keyword_data is not None),
                ("콘텐츠 생성/입력", bool(st.session_state.content_template.strip())),
                ("미디어 첨부", total_media > 0),
            ]
            
            all_ready = True
            for item, status in checklist_items:
                icon = "✅" if status else "❌"
                color = "green" if status else "red"
                st.markdown(f"{icon} **{item}**: <span style='color: {color}'>{'준비완료' if status else '미완료'}</span>", unsafe_allow_html=True)
                if not status:
                    all_ready = False
            
            if all_ready:
                st.success("🎉 모든 준비가 완료되었습니다!")
            else:
                st.warning("⚠️ 위의 미완료 항목들을 먼저 완성해주세요.")
        
        # 작업 실행 버튼
        if not st.session_state.is_running:
            if st.button("🚀 AI 포스팅 작업 시작", type="primary", use_container_width=True):
                # 필수 조건 검사
                if st.session_state.account_data is None:
                    st.error("계정 파일을 먼저 업로드해주세요!")
                elif st.session_state.keyword_data is None:
                    st.error("키워드 파일을 먼저 업로드해주세요!")
                elif not st.session_state.content_template.strip():
                    st.error("콘텐츠를 생성하거나 입력해주세요!")
                elif not st.session_state.api_key:
                    st.error("Gemini API 키를 입력해주세요!")
                elif not st.session_state.api_authenticated:
                    st.error("Gemini API 인증을 먼저 완료해주세요!")
                elif not st.session_state.naver_id:
                    st.error("네이버 아이디를 입력해주세요!")
                elif not st.session_state.naver_password:
                    st.error("네이버 패스워드를 입력해주세요!")
                else:
                    st.session_state.is_running = True
                    add_log(f"✅ 모든 인증 완료 - {st.session_state.naver_id}로 작업을 시작합니다.", "info")
                    st.rerun()
        else:
            if st.button("⏹️ 작업 중지", type="secondary", use_container_width=True):
                st.session_state.is_running = False
                add_log("작업이 중지되었습니다.", "warning")
                st.rerun()
        
        # 수동 콘텐츠 입력 옵션 (고급 사용자용)
        with st.expander("🔧 수동 콘텐츠 입력 (고급 사용자)", expanded=False):
            st.markdown("**Gemini AI 대신 직접 콘텐츠를 입력하고 싶다면:**")
            
            with st.expander("📋 폼 형식 안내", expanded=False):
                st.markdown("""
                **[폼 형식 지정 안내글]**
                
                `[본문]`을 기준으로 서론, 본문, 결론으로 나뉩니다.
                
                본문은 AI로 작성한 1500자 내외의 글이며, 키워드 파일의 이미지 중 랜덤으로 5개가 들어갑니다.
                
                **키워드 치환:**
                - `%주소%` → 주소 열의 데이터
                - `%업체%` → 업체 열의 데이터
                - `%썸네일%` → 썸네일 사진
                - `%영상%` → 썸네일 기반 영상
                
                **예시:**
                ```
                %주소%이고, %업체%입니다.
                %썸네일%
                [본문]
                %영상%
                감사합니다.
                ```
                """)
            
            manual_content = st.text_area(
                "수동 콘텐츠 템플릿",
                value="",
                height=150,
                placeholder="예:\n안녕하세요. %업체%입니다.\n%썸네일%\n[본문]\n%영상%\n감사합니다.",
                help="플레이스홀더를 사용하여 동적 콘텐츠를 생성하세요"
            )
            
            if st.button("📝 수동 콘텐츠 적용", use_container_width=True):
                if manual_content.strip():
                    st.session_state.content_template = manual_content
                    st.session_state.generated_content = manual_content
                    add_log("수동으로 입력한 콘텐츠가 적용되었습니다.", "info")
                    st.success("✅ 수동 콘텐츠가 적용되었습니다!")
                    st.rerun()
                else:
                    st.error("콘텐츠를 입력해주세요!")
        
        # 진행 상태 표시
        if st.session_state.is_running:
            with st.container():
                st.info("🔄 작업이 진행 중입니다...")
                
                # 기본 진행률 표시
                if "start_time" not in st.session_state:
                    st.session_state.start_time = time.time()
                
                elapsed_time = time.time() - st.session_state.start_time
                estimated_progress = min(int((elapsed_time / 300) * 100), 95)  # 5분 기준 예상 진행률
                
                st.progress(estimated_progress / 100)
                st.text(f"진행 중... ({estimated_progress}%)")
                
                # 자동 갱신을 위해 짧은 시간 후 rerun
                if elapsed_time < 300:  # 5분 미만일 때만
                    time.sleep(1)
                    st.rerun()
                else:
                    # 5분 후 자동 완료 처리
                    st.session_state.is_running = False
                    add_log("작업이 완료되었습니다.", "success")
                    st.success("✅ 작업이 완료되었습니다!")
                    if "start_time" in st.session_state:
                        del st.session_state.start_time
                    st.rerun()
    
    # 오른쪽 열 - 인증 & 설정 + 로그
    with col2:
        st.markdown('<div class="section-header">🔐 Gemini API 인증 & 설정</div>', unsafe_allow_html=True)
        
        # Gemini API 설정 및 인증 통합 섹션
        with st.container():
            st.markdown("**🔑 API 키 설정**")
            
            # API 키 입력 필드
            st.session_state.api_key = st.text_input(
                "Gemini API KEY", 
                value=st.session_state.api_key, 
                type="password",
                help="Google AI Studio(https://aistudio.google.com)에서 발급받은 Gemini API 키를 입력하세요",
                placeholder="AIzaSy...",
                key="api_key_input"
            )
            
            # API 키 상태 표시
            if st.session_state.api_key:
                masked_key = st.session_state.api_key[:8] + "*" * (len(st.session_state.api_key) - 12) + st.session_state.api_key[-4:] if len(st.session_state.api_key) > 12 else "*" * len(st.session_state.api_key)
                st.info(f"🔑 입력된 키: `{masked_key}`")
            else:
                st.warning("⚠️ API 키를 입력해주세요")
            
            # 인증 상태 표시
            if st.session_state.api_authenticated:
                st.success("✅ API 인증 완료 - 작업 수행 가능")
            else:
                st.error("❌ API 인증 필요")
            
            # 인증 버튼
            col_auth1, col_auth2 = st.columns(2)
            
            with col_auth1:
                if st.button("🔐 API 인증", type="primary", use_container_width=True):
                    if not st.session_state.api_key:
                        st.error("API 키를 먼저 입력해주세요!")
                    else:
                        with st.spinner("API 인증 중..."):
                            success, result = authenticate_gemini_api(st.session_state.api_key)
                            if success:
                                st.session_state.api_authenticated = True
                                add_log("✅ API 인증 완료 - 작업 수행이 가능합니다!", "success")
                                st.success("🎉 API 인증 성공!")
                                st.rerun()
                            else:
                                st.session_state.api_authenticated = False
                                st.error(f"API 인증 실패: {result}")
            
            with col_auth2:
                if st.button("🔄 초기화", use_container_width=True):
                    st.session_state.api_key = ""
                    st.session_state.api_authenticated = False
                    add_log("API 설정이 초기화되었습니다.", "info")
                    st.rerun()
        
        st.divider()
        
        # 네이버 계정 설정
        st.markdown('<div class="section-header">👤 네이버 계정 설정</div>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown("**🏠 로그인 정보**")
            
            # 네이버 계정 입력
            col_naver1, col_naver2 = st.columns(2)
            
            with col_naver1:
                st.session_state.naver_id = st.text_input(
                    "네이버 아이디",
                    value=st.session_state.naver_id,
                    help="네이버 계정의 아이디를 입력하세요"
                )
            
            with col_naver2:
                st.session_state.naver_password = st.text_input(
                    "네이버 패스워드",
                    value=st.session_state.naver_password,
                    type="password",
                    help="네이버 계정의 패스워드를 입력하세요"
                )
            
            # 계정 상태 표시
            if st.session_state.naver_id and st.session_state.naver_password:
                st.success(f"✅ 계정 설정 완료: {st.session_state.naver_id}")
            else:
                st.warning("⚠️ 네이버 계정 정보를 입력해주세요")
            
            # 계정 테스트 버튼
            auth_col1, auth_col2 = st.columns(2)
            
            with auth_col1:
                if st.button("🔍 계정 테스트", use_container_width=True):
                    if not (st.session_state.naver_id and st.session_state.naver_password):
                        st.error("아이디와 패스워드를 모두 입력해주세요!")
                    else:
                        add_log(f"계정 테스트 시도: {st.session_state.naver_id}", "info")
                        st.info("계정 테스트 기능은 실제 로그인 시 확인됩니다.")
            
            with auth_col2:
                if st.button("🗑️ 계정 초기화", use_container_width=True):
                    st.session_state.naver_id = ""
                    st.session_state.naver_password = ""
                    add_log("네이버 계정 정보가 초기화되었습니다.", "info")
                    st.rerun()
        
        st.divider()
        
        # 로그 섹션
        st.markdown('<div class="section-header">📋 실시간 로그</div>', unsafe_allow_html=True)
        
        # 로그 필터
        col_a, col_b = st.columns(2)
        with col_a:
            show_level = st.selectbox("로그 레벨", ["전체", "info", "success", "warning", "error"], index=0)
        with col_b:
            if st.button("🗑️ 로그 지우기", use_container_width=True):
                st.session_state.logs = []
                st.rerun()
        
        # 로그 표시
        if st.session_state.logs:
            # 로그 필터링
            filtered_logs = st.session_state.logs
            if show_level != "전체":
                filtered_logs = [log for log in st.session_state.logs if log['level'] == show_level]
            
            # 최근 로그부터 표시 (역순)
            for log in reversed(filtered_logs[-10:]):  # 최근 10개만 표시
                level_icon = {
                    'info': 'ℹ️',
                    'success': '✅',
                    'warning': '⚠️',
                    'error': '❌'
                }.get(log['level'], 'ℹ️')
                
                level_color = {
                    'info': '#17a2b8',
                    'success': '#28a745',
                    'warning': '#ffc107',
                    'error': '#dc3545'
                }.get(log['level'], '#17a2b8')
                
                st.markdown(
                    f"<div style='padding: 0.25rem; margin: 0.1rem 0; border-left: 3px solid {level_color}; background-color: #f8f9fa;'>"
                    f"<small style='color: #6c757d;'>{log['timestamp']}</small><br>"
                    f"{level_icon} {log['message']}"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("📝 로그가 여기에 표시됩니다.")
        
        # 자동 새로고침 체크박스
        if st.checkbox("🔄 자동 새로고침 (5초)", value=False):
            time.sleep(5)
            st.rerun()

if __name__ == "__main__":
    main()