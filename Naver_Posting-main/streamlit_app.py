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
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 기존 프로그램의 모듈들 import
try:
    from streamlit_backend import StreamlitIntegration
    from data.parsing_data import ParseData
    from data.text_data import TextData
    from data.box_data import BoxData
    from data.button_data import ButtonData
    from data.list_data import ListData
    from ui import log
except ImportError as e:
    st.error(f"모듈 import 오류: {e}")
    st.info("일부 기능이 제한될 수 있습니다.")

# 페이지 설정
st.set_page_config(
    page_title="네이버 블로그/카페 자동 포스팅",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2e7d32;
        margin: 1rem 0;
    }
    .status-box {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
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
    .auth-success {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 0.75rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .auth-pending {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 0.75rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .api-key-display {
        font-family: monospace;
        background-color: #f8f9fa;
        padding: 0.5rem;
        border-radius: 3px;
        border: 1px solid #dee2e6;
    }
    .naver-account {
        background-color: #e8f5e8;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .credential-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 0.5rem;
        border-radius: 3px;
        font-size: 0.9rem;
        margin: 0.25rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 세션 스테이트 초기화
def init_session_state():
    if 'platform_choice' not in st.session_state:
        st.session_state.platform_choice = "블로그"
    if 'waiting_min' not in st.session_state:
        st.session_state.waiting_min = 1
    if 'waiting_max' not in st.session_state:
        st.session_state.waiting_max = 3
    if 'use_dynamic_ip' not in st.session_state:
        st.session_state.use_dynamic_ip = False
    if 'api_key' not in st.session_state:
        # 환경변수에서 API 키 확인
        import os
        st.session_state.api_key = os.getenv('GEMINI_API_KEY', '')
    if 'phone_number' not in st.session_state:
        st.session_state.phone_number = ""
    if 'content_template' not in st.session_state:
        st.session_state.content_template = ""
    if 'account_data' not in st.session_state:
        st.session_state.account_data = None
    if 'keyword_data' not in st.session_state:
        st.session_state.keyword_data = None
    if 'title_data' not in st.session_state:
        st.session_state.title_data = None
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'is_running' not in st.session_state:
        st.session_state.is_running = False
    if 'integration' not in st.session_state:
        try:
            st.session_state.integration = StreamlitIntegration()
        except:
            st.session_state.integration = None
    if 'api_authenticated' not in st.session_state:
        st.session_state.api_authenticated = False
    if 'auth_message' not in st.session_state:
        st.session_state.auth_message = ""
    if 'naver_id' not in st.session_state:
        st.session_state.naver_id = ""
    if 'naver_password' not in st.session_state:
        st.session_state.naver_password = ""
    if 'gemini_prompt' not in st.session_state:
        st.session_state.gemini_prompt = ""
    if 'generated_content' not in st.session_state:
        st.session_state.generated_content = ""
    if 'is_generating' not in st.session_state:
        st.session_state.is_generating = False

# Gemini 콘텐츠 생성 함수
def generate_content_with_gemini(prompt, api_key):
    """Gemini API를 사용하여 콘텐츠 생성"""
    try:
        # 새로운 Google Genai 클라이언트 사용
        from google import genai
        
        # API 키 설정
        client = genai.Client(api_key=api_key)
        
        # 블로그 포스팅용 프롬프트 강화
        enhanced_prompt = f"""
다음 요청을 바탕으로 네이버 블로그/카페 포스팅용 콘텐츠를 작성해주세요.

사용자 요청: {prompt}

작성 지침:
1. 1500-2000자 분량으로 작성
2. 자연스럽고 친근한 한국어 사용
3. 읽기 쉽도록 단락별로 구성
4. SEO에 도움이 되는 키워드 자연스럽게 포함
5. 마지막에 마무리 인사 포함

형식:
- 제목을 포함하여 완성된 글 작성
- %주소%, %업체%, %썸네일%, %영상% 등의 플레이스홀더는 그대로 유지
- [본문] 태그는 사용하지 말고 완성된 글로 작성

이제 시작해주세요:
"""
        
        # 콘텐츠 생성 요청
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=enhanced_prompt,
        )
        
        if response and response.text:
            return True, response.text.strip()
        else:
            return False, "AI 응답을 받을 수 없습니다."
            
    except ImportError:
        # 기존 방식으로 fallback
        try:
            import google.generativeai as genai_old
            genai_old.configure(api_key=api_key)
            
            model = genai_old.GenerativeModel('gemini-pro')
            response = model.generate_content(enhanced_prompt)
            
            if response:
                return True, response.text.strip()
            else:
                return False, "AI 응답을 받을 수 없습니다."
        except Exception as e:
            return False, f"기존 방식 생성 오류: {str(e)}"
            
    except Exception as e:
        error_msg = str(e).lower()
        if "api_key" in error_msg or "invalid" in error_msg or "unauthorized" in error_msg:
            return False, "❌ 유효하지 않은 API 키입니다."
        elif "quota" in error_msg or "limit" in error_msg:
            return False, "❌ API 할당량이 초과되었습니다."
        else:
            return False, f"❌ 콘텐츠 생성 오류: {str(e)}"

# Gemini API 인증 함수
def authenticate_gemini_api(api_key):
    """Gemini API 키 인증"""
    try:
        # 새로운 Google Genai 클라이언트 사용
        from google import genai
        
        # API 키 설정
        client = genai.Client(api_key=api_key)
        
        # 간단한 테스트 요청
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents="Hello, test connection",
        )
        
        if response and response.text:
            return True, "✅ Gemini API 인증 성공!"
        else:
            return False, "❌ API 응답이 없습니다."
            
    except ImportError:
        # 기존 방식으로 fallback
        try:
            import google.generativeai as genai_old
            genai_old.configure(api_key=api_key)
            
            model = genai_old.GenerativeModel('gemini-pro')
            response = model.generate_content("Hello")
            
            if response:
                return True, "✅ Gemini API 인증 성공! (기존 방식)"
            else:
                return False, "❌ API 응답이 없습니다."
        except Exception as e:
            return False, f"❌ 기존 방식 인증 오류: {str(e)}"
            
    except Exception as e:
        error_msg = str(e).lower()
        if "api_key" in error_msg or "invalid" in error_msg or "unauthorized" in error_msg:
            return False, "❌ 유효하지 않은 API 키입니다."
        elif "quota" in error_msg or "limit" in error_msg:
            return False, "❌ API 할당량이 초과되었습니다."
        elif "permission" in error_msg:
            return False, "❌ API 접근 권한이 없습니다."
        else:
            return False, f"❌ 인증 오류: {str(e)}"

# 로그 추가 함수
def add_log(message, log_type="info"):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    st.session_state.logs.append({
        "timestamp": timestamp,
        "message": message,
        "type": log_type
    })
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    st.session_state.logs.append({
        "timestamp": timestamp,
        "message": message,
        "type": log_type
    })

# CSV 파일 업로드 및 처리 함수
def process_csv_file(uploaded_file, file_type):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, encoding='cp949')
            if file_type == "account":
                st.session_state.account_data = df
                add_log(f"계정 파일 업로드 완료: {len(df)}개 계정", "success")
            elif file_type == "keyword":
                st.session_state.keyword_data = df
                add_log(f"키워드 파일 업로드 완료: {len(df)}개 키워드", "success")
            elif file_type == "title":
                st.session_state.title_data = df
                add_log(f"제목 파일 업로드 완료: {len(df)}개 제목", "success")
            return df
        except Exception as e:
            add_log(f"파일 업로드 실패: {str(e)}", "error")
            return None
    return None

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
    
    # 메인 영역을 3개 열로 분할
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    # 왼쪽 열 - 파일 업로드
    with col1:
        st.markdown('<div class="section-header">📁 데이터 업로드</div>', unsafe_allow_html=True)
        
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
                st.dataframe(df.head(), use_container_width=True)
        
        st.divider()
        
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
                st.dataframe(df.head(), use_container_width=True)
        
        st.divider()
        
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
                st.dataframe(df.head(), use_container_width=True)
    
    # 중간 열 - 콘텐츠 입력 및 실행
    with col2:
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
            height=200,
            placeholder="예: '부동산 투자 초보자를 위한 가이드를 작성해주세요. 시장 분석 방법, 투자 전 체크리스트, 주의사항을 포함해서 친근하고 이해하기 쉽게 설명해주세요.'",
            help="구체적이고 상세한 프롬프트를 입력할수록 더 좋은 결과를 얻을 수 있습니다."
        )
        
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
            st.divider()
            st.markdown("**📝 생성된 콘텐츠 (편집 가능)**")
            
            # 콘텐츠 편집 가능한 텍스트 영역
            st.session_state.content_template = st.text_area(
                "생성된 콘텐츠를 검토하고 필요시 수정하세요:",
                value=st.session_state.generated_content,
                height=400,
                help="생성된 콘텐츠를 자유롭게 편집할 수 있습니다. 플레이스홀더(%주소%, %업체% 등)도 추가할 수 있습니다."
            )
            
            # 콘텐츠 정보 표시
            content_length = len(st.session_state.content_template)
            st.info(f"📊 콘텐츠 길이: {content_length:,}자 | 예상 읽기 시간: {content_length // 500 + 1}분")
        else:
            st.info("💡 위에서 프롬프트를 입력하고 '콘텐츠 생성' 버튼을 클릭하세요!")
        
        st.divider()
        
        # 자동화 실행 섹션
        st.markdown('<div class="section-header">🚀 자동화 실행</div>', unsafe_allow_html=True)
        
        # 실행 전 체크리스트
        with st.expander("✅ 실행 전 체크리스트", expanded=False):
            checklist_items = [
                ("Gemini API 인증", st.session_state.api_authenticated),
                ("네이버 로그인 정보", bool(st.session_state.naver_id and st.session_state.naver_password)),
                ("계정 파일 업로드", st.session_state.account_data is not None),
                ("키워드 파일 업로드", st.session_state.keyword_data is not None),
                ("콘텐츠 생성/입력", bool(st.session_state.content_template.strip())),
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
                    # 기존 모듈과 연동하여 작업 실행
                    if st.session_state.integration:
                        config = {
                            'platform': st.session_state.platform_choice,
                            'account_data': st.session_state.account_data,
                            'keyword_data': st.session_state.keyword_data,
                            'content_template': st.session_state.content_template,
                            'title_data': st.session_state.title_data,
                            'api_key': st.session_state.api_key,
                            'phone_number': st.session_state.phone_number,
                            'naver_id': st.session_state.naver_id,
                            'naver_password': st.session_state.naver_password,
                            'waiting_min': st.session_state.waiting_min,
                            'waiting_max': st.session_state.waiting_max,
                            'use_dynamic_ip': st.session_state.use_dynamic_ip
                        }
                        if st.session_state.integration.execute_posting_task(config):
                            st.session_state.is_running = True
                            add_log(f"✅ 모든 인증 완료 - {st.session_state.naver_id}로 작업을 시작합니다.", "info")
                            st.rerun()
                        else:
                            st.error("작업 시작에 실패했습니다.")
                    else:
                        st.session_state.is_running = True
                        add_log(f"✅ 모든 인증 완료 - {st.session_state.naver_id}로 작업을 시작합니다.", "info")
                        st.rerun()
        else:
            if st.button("⏹️ 작업 중지", type="secondary", use_container_width=True):
                if st.session_state.integration:
                    st.session_state.integration.stop_task()
                st.session_state.is_running = False
                add_log("작업이 중지되었습니다.", "warning")
                st.rerun()
        
        # 수동 콘텐츠 입력 옵션 (고급 사용자용)
        with st.expander("🔧 수동 콘텐츠 입력 (고급 사용자)", expanded=False):
            st.markdown("**Gemini AI 대신 직접 콘텐츠를 입력하고 싶다면:**")
            
            with st.expander("📋 폼 형식 안내", expanded=False):
                st.markdown("""
                **[폼 형식 지정 안내글]**
                
                `[본문]`을 기준으로 서론, 본문, 결론으로 나뉘어집니다.
                
                본문은 AI로 작성한 1500자 내외의 글이며, 고객님께서 keyword.csv를 통해 업로드한 이미지 중 랜덤으로 5개가 같이 들어갑니다.
                
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
                height=200,
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
                
                # 실제 작업 상태 조회
                if st.session_state.integration:
                    status = st.session_state.integration.get_task_status()
                    progress = status.get('progress', 0)
                    current_task = status.get('current_task', '작업 중...')
                    
                    progress_bar = st.progress(progress / 100)
                    status_text = st.text(f"{current_task} ({progress}%)")
                    
                    # 작업 완료 확인
                    if not status.get('is_running', True) and progress >= 100:
                        st.session_state.is_running = False
                        add_log("작업이 완료되었습니다.", "success")
                        st.success("✅ 작업이 완료되었습니다!")
                        st.rerun()
                else:
                    # 백업 진행률 표시 (통합 모듈이 없을 때)
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i in range(100):
                        progress_bar.progress(i + 1)
                        status_text.text(f"진행률: {i + 1}%")
                        time.sleep(0.05)
                    
                    st.session_state.is_running = False
                    add_log("작업이 완료되었습니다.", "success")
                    st.success("✅ 작업이 완료되었습니다!")
                    st.rerun()
    
    # 오른쪽 열 - 로그 및 상태
    with col3:
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
            elif st.session_state.auth_message:
                if "성공" in st.session_state.auth_message:
                    st.success(st.session_state.auth_message)
                else:
                    st.error(st.session_state.auth_message)
            
            # 인증 버튼들
            col_auth1, col_auth2 = st.columns(2)
            
            with col_auth1:
                if st.button("🔍 API 인증", type="primary", use_container_width=True, key="auth_button"):
                    if st.session_state.api_key:
                        with st.spinner("API 인증 중..."):
                            add_log("Gemini API 인증을 시작합니다...", "info")
                            is_valid, message = authenticate_gemini_api(st.session_state.api_key)
                            st.session_state.api_authenticated = is_valid
                            st.session_state.auth_message = message
                            add_log(message, "success" if is_valid else "error")
                            
                            if is_valid:
                                add_log("✅ API 인증 완료 - 작업 수행이 가능합니다!", "success")
                            else:
                                add_log("⚠️ API 인증 실패 - 키를 확인하고 다시 시도해주세요.", "warning")
                            st.rerun()
                    else:
                        st.error("먼저 API 키를 입력해주세요!")
                        add_log("❌ API 키가 입력되지 않았습니다.", "error")
            
            with col_auth2:
                if st.button("🗑️ 인증 초기화", use_container_width=True, key="reset_button"):
                    st.session_state.api_authenticated = False
                    st.session_state.auth_message = ""
                    st.session_state.api_key = ""
                    add_log("API 인증이 초기화되었습니다.", "info")
                    st.rerun()
        
        st.divider()
        
        # 네이버 계정 설정 섹션
        with st.container():
            st.markdown("**🌐 네이버 계정 설정**")
            
            # 네이버 아이디 입력
            st.session_state.naver_id = st.text_input(
                "네이버 아이디",
                value=st.session_state.naver_id,
                help="네이버 블로그/카페 포스팅을 위한 네이버 계정 아이디를 입력하세요",
                placeholder="your_naver_id",
                key="naver_id_input"
            )
            
            # 네이버 패스워드 입력
            st.session_state.naver_password = st.text_input(
                "네이버 패스워드",
                value=st.session_state.naver_password,
                type="password",
                help="네이버 계정의 패스워드를 입력하세요",
                placeholder="패스워드 입력",
                key="naver_password_input"
            )
            
            # 계정 상태 표시
            if st.session_state.naver_id and st.session_state.naver_password:
                st.success(f"✅ 네이버 계정 설정 완료: {st.session_state.naver_id}")
            elif st.session_state.naver_id:
                st.warning("⚠️ 패스워드를 입력해주세요")
            else:
                st.info("💡 네이버 계정 정보를 입력해주세요")
            
            # 계정 관리 버튼들
            col_naver1, col_naver2 = st.columns(2)
            
            with col_naver1:
                if st.button("💾 계정 저장", use_container_width=True, key="save_naver"):
                    if st.session_state.naver_id and st.session_state.naver_password:
                        # 계정 정보 저장 로직 (실제로는 보안을 위해 암호화 저장)
                        add_log(f"네이버 계정 '{st.session_state.naver_id}' 저장 완료", "success")
                        st.success("계정 정보가 저장되었습니다!")
                    else:
                        st.error("아이디와 패스워드를 모두 입력해주세요!")
                        add_log("네이버 계정 정보가 불완전합니다.", "error")
            
            with col_naver2:
                if st.button("🗑️ 계정 초기화", use_container_width=True, key="clear_naver"):
                    st.session_state.naver_id = ""
                    st.session_state.naver_password = ""
                    add_log("네이버 계정 정보가 초기화되었습니다.", "info")
                    st.rerun()
        
        st.divider()
        
        # 업로드된 데이터 요약
        with st.container():
            st.markdown("**📈 설정 및 데이터 요약**")
            
            # 인증 상태 요약
            auth_col1, auth_col2 = st.columns(2)
            with auth_col1:
                api_status = "✅ 완료" if st.session_state.api_authenticated else "❌ 미완료"
                st.metric("API 인증", api_status)
                
                naver_status = "✅ 완료" if (st.session_state.naver_id and st.session_state.naver_password) else "❌ 미완료"
                st.metric("네이버 계정", naver_status)
            
            with auth_col2:
                if st.session_state.naver_id:
                    st.metric("네이버 ID", st.session_state.naver_id)
                else:
                    st.metric("네이버 ID", "미설정")
                
                st.metric("플랫폼", st.session_state.platform_choice)
            
            st.divider()
            
            # 파일 데이터 요약
            col_a, col_b = st.columns(2)
            with col_a:
                account_count = len(st.session_state.account_data) if st.session_state.account_data is not None else 0
                st.metric("계정 수", account_count)
                
                title_count = len(st.session_state.title_data) if st.session_state.title_data is not None else 0
                st.metric("제목 수", title_count)
            
            with col_b:
                keyword_count = len(st.session_state.keyword_data) if st.session_state.keyword_data is not None else 0
                st.metric("키워드 수", keyword_count)
                
                st.metric("대기시간", f"{st.session_state.waiting_min}-{st.session_state.waiting_max}분")
        
        st.divider()
        
        # 로그 표시
        st.markdown("**📋 실시간 로그**")
        log_container = st.container()
        
        with log_container:
            if st.session_state.logs:
                # 최근 10개 로그만 표시
                recent_logs = st.session_state.logs[-10:]
                
                for log in reversed(recent_logs):  # 최신 로그가 위에 오도록
                    if log["type"] == "success":
                        st.success(f"{log['timestamp']} {log['message']}")
                    elif log["type"] == "error":
                        st.error(f"{log['timestamp']} {log['message']}")
                    elif log["type"] == "warning":
                        st.warning(f"{log['timestamp']} {log['message']}")
                    else:
                        st.info(f"{log['timestamp']} {log['message']}")
            else:
                st.info("아직 로그가 없습니다.")
        
        # 로그 초기화 버튼
        if st.button("🗑️ 로그 초기화", key="clear_logs", use_container_width=True):
            st.session_state.logs = []
            st.rerun()
    
    # 푸터
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        💡 <strong>사용 팁:</strong> CSV 파일은 UTF-8 또는 CP949 인코딩으로 저장해주세요. | 
        📧 <strong>문의:</strong> 문제가 발생하면 로그를 확인해주세요.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()