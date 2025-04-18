import requests
import time
import logging
import os

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def request_access_token(app_key, app_secret, authorization_code):
    """새로운 액세스 토큰을 발급받습니다."""
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"
    
    # 요청 파라미터 설정 (app_key를 명시적으로 전달)
    params = {
        "app_key": app_key,  # GitHub Secrets에서 가져온 app_key 값
        "timestamp": str(int(time.time() * 1000)),  # 밀리초로 타임스탬프
        "sign_method": "md5",  # 서명 방법 md5
        "code": authorization_code,  # authorization_code
        "grant_type": "authorization_code",  # grant_type
    }

    # 디버깅: 파라미터 값 출력
    print(f"실제 파라미터들: {params}")  # params에서 `app_key` 값이 잘 전달되었는지 확인

    # 서명 생성
    params["sign"] = generate_signature(params, app_secret)

    try:
        # POST 요청 보내기
        response = requests.post(url, data=params)

        # 디버깅: 요청 URL 및 응답 정보 출력
        print(f"Request URL: {url}")
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            response_data = response.json()
            if "error_response" in response_data:
                print(f"Token request failed: {response_data['error_response']['code']} - {response_data['error_response']['msg']}")
                return None
            else:
                print("Token request succeeded!")
                return response_data.get('access_token')
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error during token request: {str(e)}")
        return None

# 서명 생성 함수
def generate_signature(params, secret_key):
    """서명 생성 함수"""
    params_to_sign = {k: v for k, v in params.items() if k != 'sign'}

    # 파라미터를 ASCII 순으로 정렬
    sorted_keys = sorted(params_to_sign.keys())
    param_string = ''.join(f"{key}{params_to_sign[key]}" for key in sorted_keys)

    # 서명할 문자열 구성: secret_key + 파라미터 문자열 + secret_key
    string_to_sign = f"{secret_key}{param_string}{secret_key}"

    # 디버깅: 서명할 문자열 출력
    print(f"서명할 문자열: {string_to_sign}")

    # MD5 해시로 서명 생성
    signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()

    # 디버깅: 서명 출력
    print(f"생성된 서명: {signature}")

    return signature
