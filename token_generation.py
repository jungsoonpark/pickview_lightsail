import os
import json
import time
import logging
from github import Github
from iop.base import IopClient, IopRequest  # SDK에서 제공하는 클래스 사용

# 현재 파일의 디렉토리 경로
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'aliexpress_sdk'))  # iop 폴더의 상위 경로 추가

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def get_github_secrets():
    """GitHub Secrets에서 값을 가져옵니다."""
    api_key = os.environ.get('API_KEY')  # GitHub Actions에서 설정한 API_KEY
    api_secret = os.environ.get('API_SECRET')  # GitHub Actions에서 설정한 API_SECRET

    logger.debug(f"API Key: {api_key}")
    logger.debug(f"API Secret: {api_secret}")

    if api_key is None or api_secret is None:
        logger.error("API Key or Secret is missing in GitHub Secrets!")
    
    return {
        "api_key": api_key,
        "api_secret": api_secret
    }

def request_access_token(secrets, authorization_code):
    """새로운 액세스 토큰을 발급받습니다."""
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"
    
    # IopClient 객체 생성 (SDK 방식)
    client = IopClient(app_key=secrets['api_key'], app_secret=secrets['api_secret'])
    
    # IopRequest 객체 생성 (API 요청을 위한 객체)
    request = IopRequest(api_name="/rest/auth/token/create", client=client)
    
    # 요청 파라미터 설정
    params = {
        "timestamp": str(int(time.time() * 1000)),  # UTC 타임스탬프
        "sign_method": "md5",
        "code": authorization_code,
        "grant_type": "authorization_code",
    }
    
    # 서명 자동 생성 및 요청 전송
    response = request.send_request(params)
    
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

if __name__ == "__main__":
    secrets = get_github_secrets()

    # 사용자 인증 후 받은 실제 'authorization_code'를 여기에 입력
    authorization_code = "3_513774_ghfazA1uInhLE24BaB0Op2fg3694"  # 사용자가 인증 후 받은 실제 코드로 교체

    # 토큰 요청
    request_access_token(secrets, authorization_code)
