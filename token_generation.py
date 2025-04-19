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
    # 필요한 파라미터를 하나로 합침
    param_string = f"app_key{app_key}code{authorization_code}grant_typeauthorization_codesign_method{sign_method}timestamp{timestamp}"

    # 서명할 문자열 구성 (app_secret 양 끝에 추가)
    string_to_sign = f"{app_secret}{param_string}{app_secret}"

    # 디버깅: 서명할 문자열 출력
    print(f"서명할 문자열: {string_to_sign}")

    # MD5 해시로 서명 생성
    signature = hashlib.md5(f"{app_secret}{string_to_sign}{app_secret}".encode('utf-8')).hexdigest().upper()

    # 디버깅: 생성된 서명 출력
    print(f"생성된 서명: {signature}")

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
