import requests
import hashlib
import time

# 하드코딩된 app_key와 app_secret
app_key = "513774"  # 자신의 app_key
app_secret = "L2SMzWXVw58POzLojjQALzHqXRX4Bg2U"  # 자신의 app_secret
authorization_code = "3_513774_fZF0biL3vtaoirRHEis6ek4i777"  # 사용자 인증 후 받은 실제 코드

# 타임스탬프 (밀리초 단위로)
timestamp = str(int(time.time() * 1000))

# 서명 방법 (기본값: md5)
sign_method = "md5"

# grant_type 값
grant_type = "authorization_code"

# 서명할 문자열 구성
string_to_sign = f"{app_secret}app_key{app_key}code{authorization_code}grant_type{grant_type}sign_method{sign_method}timestamp{timestamp}{app_secret}"

# MD5 해시로 서명 생성
signature = hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()

# 요청 파라미터 설정
params = {
    "app_key": app_key,
    "timestamp": timestamp,
    "sign_method": sign_method,
    "code": authorization_code,
    "grant_type": grant_type,
    "sign": signature
}

# POST 요청 보내기
url = "https://api-sg.aliexpress.com/rest/auth/token/create"
response = requests.post(url, data=params)

# 응답 처리
if response.status_code == 200:
    print("Access Token:", response.json().get('access_token'))
else:
    print("Failed to get access token:", response.text)
