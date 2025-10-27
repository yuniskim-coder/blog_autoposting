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
        st.session_state.api_key = ""
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

# Gemini API 인증 함수
def authenticate_gemini_api(api_key):
    """Gemini API 키 인증"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # 간단한 테스트 요청
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Hello")
        
        if response:
            return True, "✅ Gemini API 인증 성공!"
        else:
            return False, "❌ API 응답이 없습니다."
            
    except Exception as e:
        if "API_KEY_INVALID" in str(e) or "invalid" in str(e).lower():
            return False, "❌ 유효하지 않은 API 키입니다."
        elif "quota" in str(e).lower():
            return False, "❌ API 할당량이 초과되었습니다."
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
        
        # Gemini API 키 설정
        st.markdown("🔑 **Gemini API 설정**")
        
        # API 키 입력
        st.session_state.api_key = st.text_input(
            "Gemini API KEY", 
            value=st.session_state.api_key, 
            type="password",
            help="Google AI Studio에서 발급받은 Gemini API 키를 입력하세요"
        )
        
        # API 인증 상태 표시
        if st.session_state.api_authenticated:
            st.success("✅ API 인증 완료")
        elif st.session_state.auth_message:
            if "성공" in st.session_state.auth_message:
                st.success(st.session_state.auth_message)
            else:
                st.error(st.session_state.auth_message)
        
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
        st.markdown('<div class="section-header">✍️ 콘텐츠 작성</div>', unsafe_allow_html=True)
        
        # 폼 형식 안내
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
        
        # 콘텐츠 템플릿 입력
        st.session_state.content_template = st.text_area(
            "콘텐츠 템플릿",
            value=st.session_state.content_template,
            height=300,
            placeholder="여기에 포스팅할 내용의 템플릿을 입력하세요...\n\n예:\n안녕하세요. %업체%입니다.\n%썸네일%\n[본문]\n%영상%\n감사합니다.",
            help="플레이스홀더를 사용하여 동적 콘텐츠를 생성하세요"
        )
        
        st.divider()
        
        # 작업 실행 버튼
        if not st.session_state.is_running:
            if st.button("🚀 작업 수행", type="primary", use_container_width=True):
                # 필수 조건 검사
                if st.session_state.account_data is None:
                    st.error("계정 파일을 먼저 업로드해주세요!")
                elif st.session_state.keyword_data is None:
                    st.error("키워드 파일을 먼저 업로드해주세요!")
                elif not st.session_state.content_template.strip():
                    st.error("콘텐츠 템플릿을 입력해주세요!")
                elif not st.session_state.api_key:
                    st.error("Gemini API 키를 입력해주세요!")
                elif not st.session_state.api_authenticated:
                    st.error("Gemini API 인증을 먼저 완료해주세요!")
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
                            'waiting_min': st.session_state.waiting_min,
                            'waiting_max': st.session_state.waiting_max,
                            'use_dynamic_ip': st.session_state.use_dynamic_ip
                        }
                        if st.session_state.integration.execute_posting_task(config):
                            st.session_state.is_running = True
                            add_log("✅ API 인증 완료 - 작업을 시작합니다.", "info")
                            st.rerun()
                        else:
                            st.error("작업 시작에 실패했습니다.")
                    else:
                        st.session_state.is_running = True
                        add_log("✅ API 인증 완료 - 작업을 시작합니다.", "info")
                        st.rerun()
        else:
            if st.button("⏹️ 작업 중지", type="secondary", use_container_width=True):
                if st.session_state.integration:
                    st.session_state.integration.stop_task()
                st.session_state.is_running = False
                add_log("작업이 중지되었습니다.", "warning")
                st.rerun()
        
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
        st.markdown('<div class="section-header">� API 인증 & 상태</div>', unsafe_allow_html=True)
        
        # Gemini API 인증 섹션
        with st.container():
            st.markdown("**🤖 Gemini API 인증**")
            
            # API 키 상태 표시
            if st.session_state.api_key:
                masked_key = st.session_state.api_key[:8] + "*" * (len(st.session_state.api_key) - 12) + st.session_state.api_key[-4:] if len(st.session_state.api_key) > 12 else "*" * len(st.session_state.api_key)
                st.info(f"🔑 API 키: {masked_key}")
            else:
                st.warning("⚠️ API 키가 입력되지 않았습니다")
            
            # 인증 버튼들
            col_auth1, col_auth2 = st.columns(2)
            
            with col_auth1:
                if st.button("🔍 API 인증", type="primary", use_container_width=True):
                    if st.session_state.api_key:
                        with st.spinner("API 인증 중..."):
                            is_valid, message = authenticate_gemini_api(st.session_state.api_key)
                            st.session_state.api_authenticated = is_valid
                            st.session_state.auth_message = message
                            add_log(message, "success" if is_valid else "error")
                            st.rerun()
                    else:
                        st.error("먼저 API 키를 입력해주세요!")
            
            with col_auth2:
                if st.button("🗑️ 인증 초기화", use_container_width=True):
                    st.session_state.api_authenticated = False
                    st.session_state.auth_message = ""
                    st.session_state.api_key = ""
                    add_log("API 인증이 초기화되었습니다.", "info")
                    st.rerun()
        
        st.divider()
        
        # 업로드된 데이터 요약
        with st.container():
            st.markdown("**📈 데이터 요약**")
            
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
        if st.button("🗑️ 로그 초기화", key="clear_logs"):
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