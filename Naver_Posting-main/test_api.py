import streamlit as st

st.set_page_config(
    page_title="API 테스트",
    page_icon="🔑",
    layout="wide"
)

st.title("🔑 Gemini API 인증 테스트")

# 사이드바 테스트
with st.sidebar:
    st.header("사이드바 테스트")
    
    # API 키 입력
    api_key = st.text_input(
        "Gemini API KEY", 
        type="password",
        help="Google AI Studio에서 발급받은 API 키",
        placeholder="AIzaSy..."
    )
    
    if api_key:
        st.success(f"API 키 입력됨: {api_key[:8]}...")
    else:
        st.warning("API 키를 입력해주세요")
    
    # 인증 버튼
    if st.button("🔍 API 인증 테스트"):
        if api_key:
            st.success("✅ 테스트 인증 성공!")
        else:
            st.error("❌ API 키를 먼저 입력하세요")

# 메인 영역
st.write("메인 영역입니다.")
st.write("사이드바에서 API 키를 입력하고 인증을 테스트해보세요.")

if api_key:
    st.info(f"현재 입력된 API 키: {api_key[:8]}{'*' * (len(api_key) - 8)}")
else:
    st.warning("사이드바에서 API 키를 입력해주세요.")