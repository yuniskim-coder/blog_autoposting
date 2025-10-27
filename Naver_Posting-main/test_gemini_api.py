#!/usr/bin/env python3
"""
Gemini API 테스트 스크립트
제공해주신 예제 코드로 API 연결을 테스트합니다.
"""

def test_gemini_api_simple():
    """제공해주신 예제 코드로 테스트"""
    try:
        from google import genai
        
        print("🔍 google-genai 패키지 로드 성공")
        
        # API 키 입력 받기
        api_key = input("Gemini API 키를 입력하세요: ")
        
        # 클라이언트 생성
        client = genai.Client(api_key=api_key)
        print("✅ 클라이언트 생성 완료")
        
        # 콘텐츠 생성 테스트
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents="Explain how AI works in a few words",
        )
        
        print("✅ API 호출 성공!")
        print(f"📝 응답: {response.text}")
        
        return True
    except ImportError as e:
        print(f"❌ google-genai 패키지를 찾을 수 없습니다: {e}")
        return False
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        return False

def test_fallback_api():
    """기존 google-generativeai로 테스트"""
    try:
        import google.generativeai as genai
        
        print("🔍 google-generativeai 패키지 로드 성공")
        
        # API 키 입력 받기
        api_key = input("Gemini API 키를 입력하세요 (fallback): ")
        
        # API 키 설정
        genai.configure(api_key=api_key)
        print("✅ API 키 설정 완료")
        
        # 모델 생성
        model = genai.GenerativeModel('gemini-pro')
        print("✅ 모델 생성 완료")
        
        # 콘텐츠 생성 테스트
        response = model.generate_content("Explain how AI works in a few words")
        
        print("✅ API 호출 성공!")
        print(f"📝 응답: {response.text}")
        
        return True
    except ImportError as e:
        print(f"❌ google-generativeai 패키지를 찾을 수 없습니다: {e}")
        return False
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Gemini API 테스트 시작")
    print("=" * 50)
    
    # 먼저 새로운 방식 테스트
    print("\n1️⃣ 새로운 google-genai 패키지 테스트:")
    success = test_gemini_api_simple()
    
    if not success:
        print("\n2️⃣ 기존 google-generativeai 패키지 테스트:")
        test_fallback_api()
    
    print("\n🏁 테스트 완료")