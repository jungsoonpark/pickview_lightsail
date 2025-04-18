import requests
import hashlib
import time
import logging

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

def main():
    app_key, app_secret, authorization_code = initialize_variables()
    timestamp = str(int(time.time() * 1000))
    sign_method = "md5"
    grant_type = "authorization_code"

    # 요청 파라미터 설정
    params = {
        "app_key": app_key,
        "timestamp": timestamp,
        "sign_method": sign_method,
        "code": authorization_code,
        "grant_type": grant_type
    }

    # 파라미터 정렬
    sorted_params = sorted(params.items())
    param_string = ''.join(f"{k}{v}" for k, v in sorted_params)

    # 서명할 문자열 구성 (app_secret 양 끝에 추가)
    string_to_sign = f"{app_secret}{param_string}{app_secret}"

    # 디버깅: 서명할 문자열 출력
    logger.debug(f"서명할 문자열: {string_to_sign}")

    # MD5 해시로 서명 생성
    signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()

    # 디버깅: 생성된 서명 출력
    logger.debug(f"생성된 서명: {signature}")

    # 요청 파라미터에 서명 추가
    params['sign'] = signature

    # 디버깅: 요청 파라미터 출력
    logger.debug(f"요청 파라미터: {params}")

    # POST 요청 보내기
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"
    response = requests.post(url, data=params)

    # 디버깅: API 응답 출력
    logger.debug(f"Response Status Code: {response.status_code}")
    logger.debug(f"Response Body: {response.text}")

    # 응답 처리
    if response.status_code == 200:
        logger.info("Access Token: %s", response.json().get('access_token'))
    else:
        logger.error("Failed to get access token")

if __name__ == "__main__":
    main()
