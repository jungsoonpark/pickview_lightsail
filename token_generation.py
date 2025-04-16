import os
import requests
import json
import time
import hmac
import hashlib
import urllib.parse
from github import Github

def get_github_secrets():
    """GitHub Secrets에서 값을 가져옵니다."""
    g = Github(os.environ.get("GITHUB_TOKEN"))
    repo = g.get_repo("jungsoonpark/pickview_lightsail")  # 리포지토리 이름 확인
    secrets = repo.get_secrets()

    # 비밀을 딕셔너리로 변환
    secrets_dict = {secret.name: secret for secret in secrets}

    print(f"API Key: {secrets_dict.get('ALIEXPRESS_API_KEY')}")

    return {
        "api_key": secrets_dict.get("ALIEXPRESS_API_KEY"),
        "api_secret": secrets_dict.get("ALIEXPRESS_API_SECRET")
    }

def generate_signature(params, secret_key):
    """요청 파라미터와 비밀 키를 사용하여 서명을 생성합니다."""
    params_to_sign = {k: v for k, v in params.items() if k != 'sign'}
    sorted_keys = sorted(params_to_sign.keys())
    param_pairs = []
    for key in sorted_keys:
        value = params_to_sign[key]
        if value is not None and value != "":
            if not isinstance(value, str):
                value = str(value)
            param_pairs.append(f"{key}{value}")
    
    param_string = ''.join(param_pairs)
    string_to_sign = f"{secret_key}{param_string}{secret_key}"
    signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()
    
    return signature

def request_access_token(secrets):
    """새로운 액세스 토큰을 발급받습니다."""
    url = "https://api-sg.aliexpress.com/rest/auth/token"
    
    # 필수 파라미터
    params = {
        "app_key": secrets['api_key'],
        "format": "json",
        "method": "aliexpress.auth.token.create",
        "sign_method": "md5",
        "timestamp": str(int(time.time() * 1000)),
        "v": "2.0"
    }
    
    # 서명을 생성하고 파라미터에 추가
    params["sign"] = generate_signature(params, secrets['api_secret'])
    
    # URL 인코딩된 파라미터로 변환
    encoded_params = urllib.parse.urlencode(params)
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        response = requests.post(url, data=encoded_params, headers=headers)
        print(f"토큰 요청 응답 상태 코드: {response.status_code}")
        print(f"토큰 요청 응답 내용: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if "error_response" in data:
                print(f"토큰 요청 실패: {data['error_response'].get('code')} - {data['error_response'].get('msg')}")
                return None
            else:
                print("토큰 발급 성공!")
                with open('token_info.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print("새로운 토큰 정보가 token_info.json 파일에 저장되었습니다.")
                return data.get('access_token')
        else:
            print("토큰 요청 실패")
            return None
            
    except Exception as e:
        print(f"토큰 요청 중 에러 발생: {str(e)}")
        return None

if __name__ == "__main__":
    secrets = get_github_secrets()
    request_access_token(secrets)
