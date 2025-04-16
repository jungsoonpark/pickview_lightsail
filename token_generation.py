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
    # Step 1: Sort parameters
    sorted_params = sorted(params.items())  # 파라미터를 알파벳 순으로 정렬
    param_string = ''.join(f"{key}{value}" for key, value in sorted_params)  # 파라미터 결합

    # Step 2: Add API name for system interfaces
    query_string = api_name + param_string  # 시스템 인터페이스의 경우 API 이름 추가

    # Step 3: Generate HMAC-SHA256 signature
    signature = hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest().upper()

    return signature

# Example usage
params = {
    "app_key": "your_app_key",
    "method": "aliexpress.auth.token.create",
    "timestamp": "2025-04-16 10:00:00",
    "code": "your_authorization_code",
    "grant_type": "authorization_code",
    "v": "2.0"
}

api_name = "/auth/token/create"  # API 이름 추가
secret_key = "your_app_secret"  # 앱 시크릿

signature = generate_signature(params, secret_key, api_name)
print(f"Generated Signature: {signature}")


def request_access_token(secrets, authorization_code):
    """새로운 액세스 토큰을 발급받습니다."""
    # AliExpress 인증 URL 설정
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"  # 올바른 API 경로 설정

    # Params to send in the request
    params = {
        "app_key": secrets['api_key'],
        "format": "json",
        "method": "aliexpress.auth.token.create",
        "sign_method": "md5",
        "timestamp": str(int(time.time() * 1000)),
        "v": "2.0",
        "code": authorization_code,  # Temporary code obtained from user authorization
        "grant_type": "authorization_code",  # Correct grant type
    }

    # Generate the signature
    params["sign"] = generate_signature(params, secrets['api_secret'])

    try:
        # Send POST request
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

    # The `authorization_code` needs to be obtained after user authorization
    authorization_code = "3_513774_ghfazA1uInhLE24BaB0Op2fg3694"  # 실제 authorization_code로 교체

    # Request Access Token
    request_access_token(secrets, authorization_code)
