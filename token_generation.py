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
    # GitHub Secrets에서 환경 변수로 API Key와 API Secret 값을 가져옵니다.
    api_key = os.environ.get("ALIEXPRESS_API_KEY")
    api_secret = os.environ.get("ALIEXPRESS_API_SECRET")
    
    # 디버깅: API Key와 API Secret 출력
    logger.debug(f"API Key: {api_key}")
    logger.debug(f"API Secret: {api_secret}")
    
    return {
        "api_key": api_key,
        "api_secret": api_secret
    }


def generate_signature(params, secret_key, api_name):
    # 1. 파라미터 정렬
    sorted_keys = sorted(params.keys())
    param_pairs = []
    for key in sorted_keys:
        value = params[key]
        if value is not None and value != "":
            param_pairs.append(f"{key}{value}")
    
    # 2. 파라미터 문자열 생성
    param_string = ''.join(param_pairs)
    
    # 3. api_name 앞에 추가
    string_to_sign = f"{api_name}{param_string}{secret_key}"
    
    # 4. MD5 해시 생성
    signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()
    
    return signature

def request_access_token(secrets, authorization_code):
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"

    params = {
        "app_key": secrets['api_key'],
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "md5",
        "code": authorization_code,
        "grant_type": "authorization_code",
    }

    # 서명 생성
    params["sign"] = generate_signature(params, secrets['api_secret'], "/rest/auth/token/create")

    # 요청 보내기
    response = requests.post(url, data=params)

    if response.status_code == 200:
        response_data = response.json()
        if "error_response" in response_data:
            print(f"Error: {response_data['error_response']['msg']}")
            return None
        return response_data.get('access_token')
    else:
        print(f"API Error: {response.status_code} - {response.text}")
        return None



if __name__ == "__main__":
    secrets = get_github_secrets()

    # 사용자 인증 후 받은 실제 'authorization_code'를 여기에 입력
    authorization_code = "3_513774_ghfazA1uInhLE24BaB0Op2fg3694"  # 사용자가 인증 후 받은 실제 코드로 교체

    # 토큰 요청
    request_access_token(secrets, authorization_code)
