import requests
import time
import hashlib

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

def main():
    # 하드코딩된 API 설정
    app_key = "513774"  # 실제 App Key
    app_secret = "L2SMzWXVw58POzLojjQALzHqXRX4Bg2U"  # 실제 Secret Key
    authorization_code = "3_513774_fZF0biL3vtaoirRHEis6ek4i777"  # 실제 Authorization Code

    # API 요청 URL
    url = "https://api-sg.aliexpress.com/rest/auth/token/create"

    # 요청 파라미터 설정
    params = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "app_key": app_key,
        "sign_method": "md5",
        "timestamp": str(int(time.time() * 1000)),  # 밀리초 단위 타임스탬프
    }

    # 서명 생성
    params['sign'] = generate_signature(params, app_secret)

    # 디버깅 정보 출력
    print("Request URL:", url)
    print("Request Parameters:", params)

    # POST 요청 보내기
    response = requests.post(url, data=params)

    # 응답 상태 코드 및 본문 출력
    print("Response Status Code:", response.status_code)
    print("Response Body:", response.text)

if __name__ == "__main__":
    main()
