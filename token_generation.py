import hashlib  # 여기에 반드시 추가해야 합니다.
import time
import requests
import logging
from urllib.parse import urlencode

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)




def initialize_variables():
    app_key = "513774"  # 자신의 app_key
    app_secret = "Uzy0PtFg3oqmIFZtXrrGEN9s0speXaXl"  # 자신의 app_secret
    authorization_code = "3_513774_fJdwqT8Zk7RsicAwXQj9qxGc4347"  # 사용자 인증 후 받은 실제 코드
    return app_key, app_secret, authorization_code




def generate_signature(app_key, app_secret, authorization_code, timestamp, sign_method):
    """
    서명을 생성하는 함수
    """
    # 파라미터 설정
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "sign_method": sign_method,
        "code": authorization_code,
        "grant_type": "authorization_code"
    }

    # 파라미터 정렬
    sorted_params = sorted(params.items())
    param_string = ''.join(f"{k}{v}" for k, v in sorted_params)

    # 서명할 문자열 구성 (app_secret을 양 끝에 추가)
    string_to_sign = f"{app_secret}{param_string}{app_secret}"

    # 디버깅: 서명할 문자열 출력
    logger.debug(f"서명할 문자열: {string_to_sign}")

    # MD5 해시로 서명 생성
    signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()

    # 디버깅: 생성된 서명 출력
    logger.debug(f"생성된 서명: {signature}")

    return signature




def get_access_token():
    app_key, app_secret, authorization_code = initialize_variables()
    timestamp = str(int(time.time() * 1000))
    sign_method = "md5"

    # 서명 생성
    signature = generate_signature(app_key, app_secret, authorization_code, timestamp, sign_method)

    # 요청 파라미터 설정
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "sign_method": sign_method,
        "code": authorization_code,
        "grant_type": "authorization_code",
        "sign": signature
    }

    # 디버깅: 요청 파라미터 출력
    logger.debug(f"요청 파라미터: {params}")

    # API 요청
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"
    response = requests.post(url, data=params)

    # 디버깅: API 응답 출력
    logger.debug(f"Response Status Code: {response.status_code}")
    logger.debug(f"Response Body: {response.text}")

    # 응답 처리
    if response.status_code == 200:
        logger.info("Access Token: %s", response.json().get('access_token'))
        return response.json().get('access_token')
    else:
        logger.error("Failed to get access token, Error: %s", response.text)
        return None
        

if __name__ == "__main__":
    access_token = get_access_token()
    if access_token:
        print(f"Access Token: {access_token}")
    else:
        print("Unable to obtain access token")
