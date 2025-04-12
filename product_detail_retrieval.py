# product_detail_retrieval.py

import requests
import os

def fetch_product_details(product_id):
    api_url = f"https://api.your_actual_service.com/products/{product_id}"  # 실제 API URL로 변경
    token = os.getenv("REPO_TOKEN")  # 환경 변수에서 토큰 가져오기
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"API 요청 중 오류 발생: {response.status_code}")
        return None

# 사용 예시
if __name__ == "__main__":
    product_id = "123456"  # 예시 제품 ID
    details = fetch_product_details(product_id)
    if details:
        print(details)
