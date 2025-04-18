import requests
import time
import hashlib
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

def generate_signature(params, secret_key):
    """서명 생성 함수"""
    # sign 파라미터 제외하고 정렬
    params_to_sign = {k: v for k, v in params.items() if k != 'sign'}

    # 파라미터를 ASCII 순으로 정렬
    sorted_keys = sorted(params_to_sign.keys())
    
    # 정렬된 파라미터들을 하나의 문자열로 결합
    param_pairs = []
    for key in sorted_keys:
        value = params_to_sign[key]
        if value:
            param_pairs.append(f"{key}{value}")
    
    # 파라미터 문자열 생성
    param_string = ''.join(param_pairs)

    # 서명할 문자열 생성
    string_to_sign = f"{param_string}{secret_key}"

    # MD5 해시로 서명 생성
    signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()

    # 디버깅 정보 출력
    logger.debug(f"서명할 문자열: {string_to_sign}")
    logger.debug(f"생성된 서명: {signature}")
    return signature

def request_access_token(app_key, app_secret, authorization_code):
    """새로운 액세스 토큰을 발급받습니다."""
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"
    
    # 요청 파라미터 설정
    params = {
        "app_key": app_key,  # app_key 추가
        "timestamp": str(int(time.time() * 1000)),  # UTC 타임스탬프
        "sign_method": "md5",
        "code": authorization_code,
        "grant_type": "authorization_code",
    }

    # 서명 생성
    params["sign"] = generate_signature(params, app_secret)

    try:
        # POST 요청 보내기
        response = requests.post(url, data=params)

        # 디버깅: 요청 URL 및 응답 정보 출력
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Response Status Code: {response.status_code}")
        logger.debug(f"Response Body: {response.text}")

        if response.status_code == 200:
            response_data = response.json()
            if "error_response" in response_data:
                logger.error(f"Token request failed: {response_data['error_response']['code']} - {response_data['error_response']['msg']}")
                return None
            else:
                logger.debug("Token request succeeded!")
                return response_data.get('access_token')
        else:
            logger.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error during token request: {str(e)}")
        return None

if __name__ == "__main__":
    # GitHub Secrets에서 정확한 키 값 가져오기
    APP_KEY = os.environ.get('ALIEXPRESS_API_KEY')  # GitHub Secrets에서 ALIEXPRESS_API_KEY 가져오기
    APP_SECRET = os.environ.get('ALIEXPRESS_API_SECRET')  # GitHub Secrets에서 ALIEXPRESS_API_SECRET 가져오기
    authorization_code = "3_513774_ghfazA1uInhLE24BaB0Op2fg3694"  # 사용자 인증 후 받은 실제 코드로 교체

    # 토큰 요청
    token = request_access_token(APP_KEY, APP_SECRET, authorization_code)
    if token:
        print(f"Access Token: {token}")
    else:
        print("Failed to obtain access token.")
