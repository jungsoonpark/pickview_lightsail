import os
import json
import sys
import time
import hashlib
import hmac
import logging
import requests
from github import Github

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

# SDK 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'aliexpress_sdk'))  # aliexpress_sdk 경로 추가

# SDK에서 IopClient 및 IopRequest 클래스를 가져옵니다.
from iop import IopClient, IopRequest  # 'iop' 모듈에서 IopClient 및 IopRequest 클래스 가져오기

def get_github_secrets():
    """GitHub Secrets에서 값을 가져옵니다 (이제는 환경 변수에서 직접 가져옴)."""
    api_key = os.environ.get("ALIEXPRESS_API_KEY")  # 환경 변수에서 API 키 값을 가져오기
    api_secret = os.environ.get("ALIEXPRESS_API_SECRET")  # 환경 변수에서 API Secret 값을 가져오기
    logger.debug(f"API Key: {api_key}")  # 디버깅 출력
    logger.debug(f"API Secret: {api_secret}")  # 디버깅 출력

    return {
        "api_key": api_key,
        "api_secret": api_secret
    }



def generate_signature(params, secret_key, api_name):
    """요청 파라미터와 비밀 키를 사용하여 서명을 생성합니다."""
    # sign 파라미터 제외하고 정렬
    params_to_sign = {k: v for k, v in params.items() if k != 'sign'}

    # 키만 정렬
    sorted_keys = sorted(params_to_sign.keys())

    # 파라미터 문자열 생성 (URL 인코딩 없이)
    param_pairs = []
    for key in sorted_keys:
        value = params_to_sign[key]
        if value is not None and value != "":
            param_pairs.append(f"{key}{value}")

    param_string = ''.join(param_pairs)

    # app_secret을 앞뒤에 추가
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




def request_access_token(secrets, authorization_code):
    """새로운 액세스 토큰을 발급받습니다."""
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"

    # 요청 파라미터 설정
    params = {
        "app_key": secrets['api_key'],
        "timestamp": str(int(time.time() * 1000)),  # UTC 타임스탬프
        "sign_method": "md5",
        "code": authorization_code,  # 필수: OAuth 인증 코드
        "grant_type": "authorization_code",
        "v": "2.0",  # 버전 추가
        "method": "aliexpress.auth.token.create"  # method 파라미터 추가
    }

    # uuid는 선택적 파라미터이므로 추가하지 않거나 필요 시 추가하세요
    # params["uuid"] = "your_uuid"  # 필요시 추가

    # 서명 생성
    api_name = "/rest/auth/token/create"  # API 경로
    params["sign"] = generate_signature(params, secrets['api_secret'], api_name)  # 서명 생성

    try:
        # POST 요청 보내기
        response = requests.post(url, data=params)
        
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
    secrets = get_github_secrets()

    # 사용자 인증 후 받은 실제 'authorization_code'를 여기에 입력
    authorization_code = "3_513774_ghfazA1uInhLE24BaB0Op2fg3694"  # 사용자가 인증 후 받은 실제 코드로 교체

    # 토큰 요청
    request_access_token(secrets, authorization_code)

 

