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
    repo = g.get_repo("junsoonpark/pickview_lightsail")
    secrets = repo.get_secrets()
    
    return {
        "api_key": secrets.get("ALIEXPRESS_API_KEY"),
        "api_secret": secrets.get("ALIEXPRESS_API_SECRET"),
        "access_token": secrets.get("ALIEXPRESS_ACCESS_TOKEN"),
        "refresh_token": secrets.get("ALIEXPRESS_REFRESH_TOKEN")
    }

def generate_signature(params, secret_key):
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
            # 값이 문자열이 아닌 경우 문자열로 변환
            if not isinstance(value, str):
                value = str(value)
            param_pairs.append(f"{key}{value}")
    
    param_string = ''.join(param_pairs)
    
    # app_secret을 앞뒤에 추가
    string_to_sign = f"{secret_key}{param_string}{secret_key}"
    
    # MD5 해시 생성
    signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()
    
    # 디버깅 정보 출력
    print("\n=== 서명 생성 정보 ===")
    print(f"파라미터 문자열: {param_string}")
    print(f"서명할 문자열: {string_to_sign}")
    print(f"생성된 서명: {signature}")
    print("===================\n")
    
    return signature

def refresh_access_token(refresh_token, secrets):
    """리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급받습니다."""
    url = "https://api-sg.aliexpress.com/rest/auth/token/refresh"
    
    # 디버깅: 환경 변수 값 출력
    print("\n=== 환경 변수 디버깅 ===")
    print(f"API Key: {secrets['api_key']}")
    print(f"API Secret: {secrets['api_secret']}")
    print(f"Access Token: {secrets['access_token']}")
    print(f"Refresh Token: {refresh_token}")
    print("=====================\n")
    
    # 필수 파라미터
    params = {
        "app_key": secrets['api_key'],
        "refresh_token": refresh_token,
        "format": "json",
        "method": "aliexpress.auth.token.refresh",
        "sign_method": "md5",
        "timestamp": str(int(time.time() * 1000)),
        "v": "2.0"
    }
    
    # 서명을 생성하고 파라미터에 추가
    params["sign"] = generate_signature(params, secrets['api_secret'])
    
    # 디버깅: 요청 파라미터 출력
    print("\n=== 요청 파라미터 ===")
    masked_params = params.copy()
    masked_params['app_key'] = '******'
    masked_params['sign'] = '******'
    print(json.dumps(masked_params, indent=2))
    print("===================\n")
    
    # URL 인코딩된 파라미터로 변환
    encoded_params = urllib.parse.urlencode(params)
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        response = requests.post(url, data=encoded_params, headers=headers)
        print(f"토큰 갱신 응답 상태 코드: {response.status_code}")
        print(f"토큰 갱신 응답 내용: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if "error_response" in data:
                print(f"토큰 갱신 실패: {data['error_response'].get('code')} - {data['error_response'].get('msg')}")
                return None
            else:
                print("토큰 갱신 성공!")
                # 새로운 토큰 정보를 파일에 저장
                with open('token_info.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print("새로운 토큰 정보가 token_info.json 파일에 저장되었습니다.")
                return data.get('access_token')
        else:
            print("토큰 갱신 실패")
            return None
            
    except Exception as e:
        print(f"토큰 갱신 중 에러 발생: {str(e)}")
        return None

def get_tokens_from_file():
    """token_info.json 파일에서 토큰 정보를 읽어옵니다."""
    try:
        with open('token_info.json', 'r') as f:
            token_data = json.load(f)
            return token_data.get('access_token'), token_data.get('refresh_token')
    except Exception as e:
        print(f"토큰 파일 읽기 실패: {str(e)}")
        return None, None

def create_token_info_file():
    """GitHub Secrets에서 토큰을 읽어와 token_info.json 파일을 생성합니다."""
    access_token = os.getenv("ALIEXPRESS_ACCESS_TOKEN")
    refresh_token = os.getenv("ALIEXPRESS_REFRESH_TOKEN")
    
    if not access_token or not refresh_token:
        print("GitHub Secrets에서 토큰을 찾을 수 없습니다.")
        return False
    
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token
    }
    
    try:
        with open('token_info.json', 'w') as f:
            json.dump(token_data, f, indent=2)
        print("token_info.json 파일이 생성되었습니다.")
        return True
    except Exception as e:
        print(f"토큰 파일 생성 실패: {str(e)}")
        return False

def test_token():
    """저장된 토큰이 유효한지 테스트합니다."""
    secrets = get_github_secrets()
    
    url = "https://api-sg.aliexpress.com/sync"
    
    params = {
        "method": "aliexpress.affiliate.product.query",
        "app_key": secrets['api_key'],
        "access_token": secrets['access_token'],
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "md5",
        "keywords": "test",
        "page_size": 1,
        "format": "json",
        "v": "2.0"
    }
    
    params["sign"] = generate_signature(params, secrets['api_secret'])
    encoded_params = urllib.parse.urlencode(params)
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        response = requests.post(url, data=encoded_params, headers=headers)
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 내용: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if "error_response" in data:
                error_code = data["error_response"].get("code")
                error_msg = data["error_response"].get("msg")
                print(f"API 에러: {error_code} - {error_msg}")
                
                if error_code == "IllegalAccessToken":
                    print("\n토큰이 만료되어 리프레시 토큰으로 갱신을 시도합니다...")
                    new_token = refresh_access_token(secrets['refresh_token'], secrets)
                    if new_token:
                        print(f"새로운 액세스 토큰: {new_token}")
                        return True
                    else:
                        print("토큰 갱신 실패")
                        return False
            else:
                print("토큰이 유효합니다.")
                return True
        else:
            print("API 요청 실패")
            return False
            
    except Exception as e:
        print(f"에러 발생: {str(e)}")
        return False

if __name__ == "__main__":
    test_token() 
