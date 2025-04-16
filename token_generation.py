import os
import json
import sys  # sys 모듈을 임포트합니다.
from github import Github

# SDK 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'aliexpress_sdk'))  # aliexpress_sdk 경로 추가

# SDK에서 IopClient 클래스를 가져옵니다.
from iop import IopClient  # 'iop' 모듈에서 IopClient 클래스 가져오기

def get_github_secrets():
    """GitHub Secrets에서 값을 가져옵니다."""
    g = Github(os.environ.get("GITHUB_TOKEN"))  # REPO_TOKEN 사용
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
    # IopClient 초기화
    aliexpress_client = IopClient(server_url="https://api-sg.aliexpress.com", app_key=secrets['api_key'], app_secret=secrets['api_secret'])

    try:
        # 액세스 토큰 요청 (예시 API)
        request = IopRequest("aliexpress.auth.token.create")  # 해당 API 메서드를 사용할 수 있도록 수정
        request.add_api_param("grant_type", "client_credentials")  # 필요한 파라미터 추가
        
        # 토큰 요청 및 응답 받기
        response = aliexpress_client.execute(request)  # IopClient의 execute() 메서드 사용
        
        print(f"토큰 요청 응답 내용: {response.body}")

        if response.code != "0":  # 성공적 응답 확인
            print(f"토큰 요청 실패: {response.code} - {response.message}")
            return None
        else:
            print("토큰 발급 성공!")
            # 새로운 토큰 정보를 파일에 저장
            with open('token_info.json', 'w') as f:
                json.dump(response.body, f, indent=2)
            print("새로운 토큰 정보가 token_info.json 파일에 저장되었습니다.")
            return response.body.get('access_token')
    except Exception as e:
        print(f"토큰 요청 중 에러 발생: {str(e)}")
        return None

if __name__ == "__main__":
    secrets = get_github_secrets()
    request_access_token(secrets)
