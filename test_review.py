import requests
import logging

def get_reviews(product_id):
    url = f"https://feedback.aliexpress.com/pc/searchEvaluation.do?productId={product_id}&lang=ko_KR&country=KR&page=1&pageSize=10&filter=5&sort=complex_default"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        
        # JSON 형식 확인
        if 'application/json' in response.headers.get('Content-Type', ''):
            data = response.json()
            reviews = data.get('data', {}).get('evaViewList', [])
            return [review.get('buyerTranslationFeedback') for review in reviews if review.get('buyerTranslationFeedback')]
        else:
            logging.error(f"JSON 형식이 아닙니다: {response.text}")
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP 요청 오류: {e}")
        return []
    except ValueError:
        logging.error("JSON 파싱 오류")
        return []

# 사용 예시
product_id = "1005007171050895"  # 예시 상품 ID
reviews = get_reviews(product_id)
print(reviews)
