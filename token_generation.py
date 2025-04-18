import requests
import time
import hashlib
import logging

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
    param_string = ''.join(f"{key}{params_to_sign[key]}" for key in sorted_keys)

    # 서명할 문자열 구성: secret_key + 파라미터 문자열 + secret_key
    string_to_sign = f"{secret_key}{param_string}{secret_key}"
    
    # 서명할 문자열 출력 (디버깅용)
    logger.debug(f"서명할 문자열: {string_to_sign}")

    # MD5 해시로 서명 생성
    signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()
    
    # 서명 값 출력 (디버깅용)
    logger.debug(f"생성된 서명: {signature}")

    return signature

def request_access_token():
    """새로운 액세스 토큰을 발급받습니다."""
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"

    
    # 하드코딩된 app_key와 app_secret
    app_key = "513774"  # 실제 app_key를 여기에 하드코딩
    app_secret = "L2SMzWXVw58POzLojjQALzHqXRX4Bg2U"  # 실제 app_secret을 여기에 하드코딩
    authorization_code = "3_513774_fZF0biL3vtaoirRHEis6ek4i777"  # 사용자 인증 후 받은 실제 코드로 교체

    # 요청 파라미터 설정
    params = {
        "app_key": app_key,  # 하드코딩된 app_key
        "timestamp": str(int(time.time() * 1000)),  # 밀리초로 타임스탬프
        "sign_method": "MD5",  # 서명 방법 md5
        "code": authorization_code,  # authorization_code
        "grant_type": "authorization_code",  # grant_type
    }

    # 디버깅: 파라미터 값 출력 (디버깅용)
    logger.debug(f"실제 파라미터들: {params}")

    # 서명 생성
    params["sign"] = generate_signature(params, app_secret)

    # 디버깅: 서명 파라미터 값 출력 (디버깅용)
    logger.debug(f"서명 값이 params['sign']에 할당된 값: {params['sign']}")

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

# 실제 실행 코드
if __name__ == "__main__":
    # 토큰 요청
    token = request_access_token()
    if token:
        logger.debug(f"Access Token: {token}")
    else:
        logger.debug("Failed to obtain access token.")



