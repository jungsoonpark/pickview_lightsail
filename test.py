import os
import logging

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def get_github_secrets():
    """GitHub Secrets에서 값을 가져옵니다."""
    api_key = os.environ.get('API_KEY')  # GitHub Actions에서 설정한 API_KEY
    api_secret = os.environ.get('API_SECRET')  # GitHub Actions에서 설정한 API_SECRET
    
    # 로깅: API Key와 API Secret 값 확인
    logger.debug(f"API Key from Secrets: {api_key}")
    logger.debug(f"API Secret from Secrets: {api_secret}")

    if api_key is None or api_secret is None:
        logger.error("API Key or Secret is missing in GitHub Secrets!")
    
    return {
        "api_key": api_key,
        "api_secret": api_secret
    }

# 테스트로 함수 실행
if __name__ == "__main__":
    get_github_secrets()
