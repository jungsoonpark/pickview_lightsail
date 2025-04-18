# purchase_guide_creation.py

import requests
import os

def generate_purchase_guide(product_info, review_summary):
    api_key = os.getenv("OPENAI_API_KEY")  # 환경 변수에서 API 키 가져오기
    headers = {"Authorization": f"Bearer {api_key}"}
    prompt = f"Generate a purchase guide for {product_info['title']} based on the following reviews: {review_summary}"
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json={"messages": [{"role": "user", "content": prompt}]})
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print(f"API 요청 중 오류 발생: {response.status_code}")
        return None
    
    # 구매 가이드 요청
    prompt = (
        f"다음 제품 정보를 바탕으로 구매 가이드를 작성해 주세요:\n"
        f"제품명: {product_info['title']}\n"
        f"가격: {product_info['price']}\n"
        f"리뷰 요약: {review_summary}\n"
        f"구매 가이드를 작성해 주세요."
    )
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150
    }
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    
    if response.status_code == 200:
        guide = response.json()['choices'][0]['message']['content']
        return guide
    else:
        print(f"OpenAI API 요청 중 오류 발생: {response.status_code}")
        return None

# 사용 예시
if __name__ == "__main__":
    product_info = {
        "title": "예시 제품",
        "price": "$100",
        "affiliate_link": "https://example.com/affiliate"
    }
    review_summary = "이 제품은 매우 좋습니다. 가격 대비 성능이 뛰어납니다."
    
    purchase_guide = generate_purchase_guide(product_info, review_summary)
    if purchase_guide:
        print("구매 가이드:", purchase_guide)
