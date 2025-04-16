import os
import json
import sys  # sys 모듈을 임포트합니다.
import time
from github import Github

# SDK 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'aliexpress_sdk'))  # aliexpress_sdk 폴더 경로 추가

from aliexpress_sdk import AliExpress  # SDK에서 AliExpress 클래스를 가져옵니다.

def get_github_secrets():
    """GitHub Secrets에서 값을 가져옵니다."""
    g = Github(os.environ.get("REPO_TOKEN"))  # REPO_TOKEN 사용
    repo = g.get_repo("jungsoonpark/pickview_lightsail")  # 리포지토리 이름 확인
    secrets = repo.get_secrets()

    # 비밀을 딕셔너리로 변환
    secrets_dict = {secret.name: secret for secret in secrets}

    return {
        "api_key": secrets_dict.get("ALIEXPRESS_API_KEY").value,  # 실제 API 키 값 가져오기
        "api_secret": secrets_dict.get("ALIEXPRESS_API_SECRET").value  # 실제 API Secret 값 가져오기
    }

def request_access_token(secrets):
    """새로운 액세스 토큰을 발급받습니다."""
    # AliExpress SDK 초기화
    aliexpress = AliExpress(app_key=secrets['api_key'], app_secret=secrets['api_secret'])

    try:
        # 액세스 토큰 요청
        response = aliexpress.auth.request_token(grant_type='client_credentials')  # SDK 문서에 따라 수정
        print(f"토큰 요청 응답 내용: {response}")

        if response.get("error_response"):
            print(f"토큰 요청 실패: {response['error_response']['code']} - {response['error_response']['msg']}")
            return None
        else:
            print("토큰 발급 성공!")
            # 새로운 토큰 정보를 파일에 저장
            with open('token_info.json', 'w') as f:
                json.dump(response, f, indent=2)
            print("새로운 토큰 정보가 token_info.json 파일에 저장되었습니다.")
            return response.get('access_token')
    except Exception as e:
        print(f"토큰 요청 중 에러 발생: {str(e)}")
        return None

if __name__ == "__main__":
    secrets = get_github_secrets()
    request_access_token(secrets)
