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
    # 1. 파라미터 준비
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "sign_method": sign_method,
        "code": authorization_code,
        "grant_type": "authorization_code"
    }

    # 2. 파라미터 정렬
    sorted_params = sorted(params.items())  # ASCII 순으로 정렬
    param_string = ''.join(f"{k}{v}" for k, v in sorted_params)

    # 3. 서명할 문자열 구성
    api_path = "/rest/auth/token/create"  # 시스템 API 경로
    string_to_sign = f"{api_path}{param_string}"

    # 4. 서명 생성 (MD5 또는 HMAC_SHA256)
    if sign_method.lower() == "md5":
        signature = hashlib.md5(f"{app_secret}{string_to_sign}{app_secret}".encode('utf-8')).hexdigest().upper()
    else:
        # HMAC-SHA256 처리
        import hmac
        import hashlib
        signature = hmac.new(app_secret.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest().upper()

    return signature

def get_access_token():
    app_key, app_secret, authorization_code = initialize_variables()
    timestamp = str(int(time.time() * 1000))  # 밀리초 단위로 타임스탬프 생성
    sign_method = "md5"  # 서명 방식 (md5 또는 sha256)

    # 5. 서명 생성
    signature = generate_signature(app_key, app_secret, authorization_code, timestamp, sign_method)

    # 6. 요청 파라미터 추가
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "sign_method": sign_method,
        "code": authorization_code,
        "grant_type": "authorization_code",
        "sign": signature
    }

    # 7. 요청 URL 생성
    base_url = "https://api-sg.aliexpress.com/rest"
    query_string = urlencode(params)  # 파라미터를 URL 인코딩
    url = f"{base_url}/auth/token/create?{query_string}"

    # 8. 요청 보내기
    logger.debug(f"Request URL: {url}")
    response = requests.post(url)

    # 9. 응답 확인
    if response.status_code == 200:
        logger.info("Access Token: %s", response.json().get('access_token'))
        return response.json().get('access_token')
    else:
        logger.error("Failed to obtain access token. Response: %s", response.text)
        return None

if __name__ == "__main__":
    token = get_access_token()
    if token:
        logger.info(f"Successfully obtained access token: {token}")
    else:
        logger.error("Unable to obtain access token")
