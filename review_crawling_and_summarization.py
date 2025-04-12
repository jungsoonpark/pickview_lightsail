# review_crawling_and_summarization.py

import requests
from playwright.sync_api import sync_playwright
import os


def crawl_reviews(product_url):
    reviews = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(product_url)
        review_elements = page.query_selector_all('.review-class')  # 실제 클래스명으로 변경
        for element in review_elements:
            reviews.append(element.inner_text())
        browser.close()
    return reviews

def summarize_reviews(reviews):
    # OpenAI API 키 설정
    api_key = "YOUR_OPENAI_API_KEY"  # 실제 API 키로 변경
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 요약 요청
    prompt = f"다음 리뷰를 2-3줄로 요약해 주세요:\n{reviews}"
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100
    }
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    
    if response.status_code == 200:
        summary = response.json()['choices'][0]['message']['content']
        return summary
    else:
        print(f"OpenAI API 요청 중 오류 발생: {response.status_code}")
        return None

# 사용 예시
if __name__ == "__main__":
    product_url = "https://example.com/product/123456"  # 예시 제품 URL
    reviews = crawl_reviews(product_url)
    if reviews:
        summary = summarize_reviews(reviews)
        print("리뷰 요약:", summary)
