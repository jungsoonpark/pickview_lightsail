import os
import json
import time
import logging
import requests
import sys
from github import Github

# 현재 파일의 디렉토리 경로
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'aliexpress_sdk'))  # iop 폴더의 상위 경로 추가

# iop 모듈 import 시도
try:
    from iop.base import IopClient, IopRequest
    print("iop module imported successfully.")
except ModuleNotFoundError as e:
    print(f"Error: {e}")


# 경로 추가 여부 확인
print("Current sys.path:", sys.path)


# 경로 확인
print("Updated sys.path:", sys.path)

# iop 모듈 import 시도
try:
    from iop import IopClient, IopRequest
    print("iop module imported successfully.")
except ModuleNotFoundError as e:
    print(f"Error: {e}")
    
    

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
    g = Github(os.environ.get("REPO_TOKEN"))  # REPO_TOKEN 사용
    repo = g.get_repo("jungsoonpark/pickview_lightsail")  # 리포지토리 이름 확인
    secrets = repo.get_secrets()

    # 비밀을 딕셔너리로 변환
    secrets_dict = {secret.name: secret for secret in secrets}

    # API 키 출력
    api_key = secrets_dict.get("ALIEXPRESS_API_KEY").get_secret_value()  # 실제 API 키 값 가져오기
    api_secret = secrets_dict.get("ALIEXPRESS_API_SECRET").get_secret_value()  # 실제 API Secret 값 가져오기
    
    # 디버깅: API Secret 출력
    logger.debug(f"API Key: {api_key}")
    logger.debug(f"API Secret: {api_secret}")
    
    return {
        "api_key": api_key,
        "api_secret": api_secret


        
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
        
        # None이 아닌 값만 처리
        if value is not None:
            param_pairs.append(f"{key}{value}")
        else:
            logger.warning(f"Warning: The parameter {key} has a None value!")
    
    param_string = ''.join(param_pairs)

    # app_secret을 앞뒤에 추가
    string_to_sign = f"{api_name}{param_string}{secret_key}"

    # MD5 해시 생성
    try:
        signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()
    except Exception as e:
        logger.error(f"Error during signature generation: {str(e)}")
        return None

    logger.debug(f"Generated Signature: {signature}")
    
    return signature




def request_access_token(secrets, authorization_code):
    """새로운 액세스 토큰을 발급받습니다."""
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"

    # 요청 파라미터 설정
    params = {
        "app_key": secrets['api_key'],
        "timestamp": str(int(time.time() * 1000)),  # UTC 타임스탬프
        "sign_method": "md5",
        "code": authorization_code,
        "grant_type": "authorization_code",
    }

    # 디버깅: API 키와 비밀키 확인
    logger.debug(f"API Key: {secrets['api_key']}")
    logger.debug(f"API Secret: {secrets['api_secret']}")

    # 서명 생성
    params["sign"] = generate_signature(params, secrets['api_secret'], "/rest/auth/token/create")  # 수정됨

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
