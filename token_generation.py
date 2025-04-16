import os
import json
import time
import logging
import requests
import sys
from github import Github

# SDK 경로 추가
sys.path.append('/home/runner/work/pickview_lightsail/pickview_lightsail/aliexpress_sdk/iop')

from iop import IopClient, IopRequest  # iop 모듈 import

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

def get_github_secrets():
    """GitHub Secrets에서 값을 가져옵니다."""
    api_key = os.environ.get("ALIEXPRESS_API_KEY")  # 환경 변수에서 API 키 값을 가져오기
    api_secret = os.environ.get("ALIEXPRESS_API_SECRET")  # 환경 변수에서 API Secret 값을 가져오기
    logger.debug(f"API Key: {api_key}")  # 디버깅 출력
    logger.debug(f"API Secret: {api_secret}")  # 디버깅 출력

    return {
        "api_key": api_key,
        "api_secret": api_secret
    }

def request_access_token(secrets, authorization_code):
    """새로운 액세스 토큰을 발급받습니다."""
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"
    
    # SDK 초기화
    client = IopClient(url, secrets['api_key'], secrets['api_secret'])
    request = IopRequest('/rest/auth/token/create')

    # 요청 파라미터 설정
    request.add_api_param('code', authorization_code)
    request.add_api_param('grant_type', 'authorization_code')
    request.add_api_param('v', '2.0')
    request.add_api_param('timestamp', str(int(time.time() * 1000)))  # UTC 타임스탬프 추가

    # 서명 및 요청 보내기
    try:
        response = client.execute(request)
        
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Response Status Code: {response.code}")
        logger.debug(f"Response Body: {json.dumps(response.body, indent=2)}")  # JSON 형식으로 출력

        if response.code == "0":
            # 응답이 성공적일 경우, 토큰 저장
            logger.debug("Token request succeeded!")
            with open('token_info.json', 'w') as f:
                json.dump(response.body, f, indent=2)
            return response.body.get('access_token')
        else:
            logger.error(f"Token request failed: {response.message}")
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
