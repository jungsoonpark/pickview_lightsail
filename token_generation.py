import os
import json
import time
import logging
import requests
import sys
import hashlib
import hmac
from github import Github
import urllib.parse



# 현재 파일의 디렉토리 경로
sys.path.append('/home/runner/work/pickview_lightsail/pickview_lightsail/aliexpress_sdk/iop')

print(sys.path)


from iop.base import IopClient, IopRequest



# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def generate_signature(params, secret_key, api_name):
    """요청 파라미터와 비밀 키를 사용하여 서명을 생성합니다."""
    # sign 파라미터 제외하고 정렬
    params_to_sign = {k: v for k, v in sorted(params.items()) if k != 'sign'}

    # 파라미터 문자열 생성 (URL 인코딩 없이)
    param_pairs = [f"{key}{value}" for key, value in params_to_sign.items() if value]
    param_string = ''.join(param_pairs)

    # API 경로 앞에 추가
    string_to_sign = f"{api_name}{param_string}{secret_key}"

    # MD5 해시 생성
    signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()

    # 디버깅 정보 출력
    logger.debug("\n=== 서명 생성 정보 ===")
    logger.debug(f"파라미터 문자열: {param_string}")
    logger.debug(f"서명할 문자열: {string_to_sign}")
    logger.debug(f"생성된 서명: {signature}")
    logger.debug("===================\n")

    return signature


def request_access_token(api_key, api_secret, authorization_code):
    """새로운 액세스 토큰을 발급받습니다."""
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"

    # 요청 파라미터 설정
    params = {
        "app_key": api_key,
        "timestamp": str(int(time.time() * 1000)),  # UTC 타임스탬프 (밀리초)
        "sign_method": "md5",
        "code": authorization_code,
        "grant_type": "authorization_code",
    }

    # 서명 생성
    params["sign"] = generate_signature(params, api_secret, "/rest/auth/token/create")

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
                with open('token_info.json', 'w') as f:
                    json.dump(response_data, f, indent=2)
                logger.debug("New token information saved to token_info.json")
                return response_data.get('access_token')
        else:
            logger.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error during token request: {str(e)}")
        return None


if __name__ == "__main__":
    # GitHub Actions에서 설정한 환경 변수에서 직접 가져오기
    api_key = os.environ.get('API_KEY')
    api_secret = os.environ.get('API_SECRET')
   

    if api_key is None or api_secret is None :
        logger.error("api_key, api_secret is missing in GitHub Secrets!")
        sys.exit(1)  # 오류 발생 시 프로그램 종료

    # 사용자 인증 후 받은 실제 'authorization_code'를 여기에 입력
    authorization_code = "3_513774_ghfazA1uInhLE24BaB0Op2fg3694"  # 사용자가 인증 후 받은 실제 코드로 교체

    # 토큰 요청
    access_token = request_access_token(api_key, api_secret, authorization_code)  # 환경 변수를 사용하여 토큰 요청
