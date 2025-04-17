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



if __name__ == "__main__":
    secrets = get_github_secrets()

    # 사용자 인증 후 받은 실제 'authorization_code'를 여기에 입력
    authorization_code = "3_513774_ghfazA1uInhLE24BaB0Op2fg3694"  # 사용자가 인증 후 받은 실제 코드로 교체

    # 토큰 요청
    request_access_token(secrets, authorization_code)
