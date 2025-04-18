import requests
import time
import hashlib
import yaml

def generate_signature(params, secret_key):
    # 'sign' 파라미터 제외
    params.pop('sign', None)
    
    # 파라미터 정렬
    sorted_params = sorted(params.items())
    
    # 정렬된 파라미터 문자열 생성
    param_string = ''.join(f"{k}{v}" for k, v in sorted_params)
    
    # 서명 문자열 생성 (AppSecret을 앞뒤에 추가)
    string_to_sign = f"{secret_key}{param_string}{secret_key}"
    
    # MD5 해시 생성
    signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()
    
    return signature

def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def main():
    # YAML 파일에서 설정 로드
    config = load_config('token_test.yml')
    
    app_key = config['app_key']
    app_secret = config['app_secret']
    authorization_code = config['authorization_code']
    
    # API 요청 URL
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"

    # 요청 파라미터 설정
    params = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "app_key": app_key,
        "sign_method": "md5",
        "timestamp": str(int(time.time() * 1000)),
    }

    # 서명 생성
    params['sign'] = generate_signature(params, app_secret)

    # POST 요청 보내기
    response = requests.post(url, data=params)

    # 응답 상태 코드 및 본문 출력
    print("Response Status Code:", response.status_code)
    print("Response Body:", response.text)

if __name__ == "__main__":
    main()
