import os
import sys
import json
import time
import hashlib
import logging
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

def generate_signature(params, secret_key):
    sorted_params = sorted(params.items())
    param_string = ''.join(f"{key}{value}" for key, value in sorted_params)
    string_to_sign = f"{secret_key}{param_string}{secret_key}"
    signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()
    return signature

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
        client = IopClient(url, secrets['api_key'], secrets['api_secret'])
        request = IopRequest('/auth/token/create')
        request.add_api_param('code', authorization_code)  # Authorization code
        request.add_api_param('uuid', 'uuid')  # User-specific UUID (optional)

        # Execute the request and get the response
        response = client.execute(request)

        logger.debug(f"Response Type: {response.type}")
        logger.debug(f"Response Body: {response.body}")

        if response.type == "ISV" and "error_response" in response.body:
            logger.error(f"Error: {response.body['error_response']}")
            return None
        else:
            logger.debug("Token request succeeded!")
            # Save token information
            with open('token_info.json', 'w') as f:
                json.dump(response.body, f, indent=2)
            logger.debug("Token information saved to token_info.json")
            return response.body.get('access_token')

    except Exception as e:
        logger.error(f"Error during token request: {str(e)}")
        return None

if __name__ == "__main__":
    secrets = get_github_secrets()

    # The `authorization_code` needs to be obtained after user authorization
    authorization_code = "3_513774_ghfazA1uInhLE24BaB0Op2fg3694"  # 실제 authorization_code로 교체

    # Request Access Token
    request_access_token(secrets, authorization_code)
