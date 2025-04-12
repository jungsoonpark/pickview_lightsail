# product_detail_retrieval.py

import requests

def fetch_product_details(product_id):
    # API 엔드포인트 URL (예시)
    api_url = f"https://api.example.com/products/{product_id}"
    
    try:
        # API 요청
        response = requests.get(api_url)
        response.raise_for_status()  # 요청이 성공하지 않으면 예외 발생
        
        # JSON 응답 파싱
        product_data = response.json()
        
        # 필요한 정보 추출
        product_info = {
            "title": product_data.get("title"),
            "price": product_data.get("price"),
            "affiliate_link": product_data.get("affiliate_link"),
            # 추가 정보가 필요하면 여기에 추가
        }
        
        return product_info
    
    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류 발생: {e}")
        return None

# 사용 예시
if __name__ == "__main__":
    product_id = "123456"  # 예시 제품 ID
    details = fetch_product_details(product_id)
    if details:
        print(details)
