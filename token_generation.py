import hashlib
import time
import hmac
import requests

# 하드코딩된 app_key와 app_secret
app_key = "513774"
app_secret = "Uzy0PtFg3oqmIFZtXrrGEN9s0speXaXl"
authorization_code = "3_513774_fZF0biL3vtaoirRHEis6ek4i777"

# 타임스탬프 (밀리초 단위로)
timestamp = str(int(time.time() * 1000))

# 서명 방법 (기본값: md5)
sign_method = 'sha256'

# grant_type 값
grant_type = "authorization_code"

# API 경로
api_path = "/rest/auth/token/create"

# 요청 파라미터 설정
params = {
    "app_key": app_key,
    "timestamp": timestamp,
    "sign_method": sign_method,
    "code": authorization_code,
    "grant_type": grant_type
}

# 파라미터 정렬
sorted_params = sorted(params.items())
param_string = ''.join(f"{k}{v}" for k, v in sorted_params)

# 서명할 문자열 구성 (app_secret 양 끝에 추가)
string_to_sign = f"{api_path}{param_string}"

# 디버깅: 서명할 문자열 출력
print(f"서명할 문자열: {string_to_sign}")

# MD5 해시로 서명 생성
signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()

# 디버깅: 생성된 서명 출력
print(f"생성된 서명: {signature}")

# 요청 파라미터에 서명 추가
params['sign'] = signature

# 디버깅: 요청 파라미터 출력
print(f"요청 파라미터: {params}")

# POST 요청 보내기
url = "https://api-sg.aliexpress.com/rest/auth/token/create"
response = requests.post(url, data=params)

# 디버깅: API 응답 출력
print(f"Response Status Code: {response.status_code}")
print(f"Response Body: {response.text}")

# 응답 처리
if response.status_code == 200:
    print("Access Token: ", response.json().get('access_token'))
else:
    print("Failed to get access token")
