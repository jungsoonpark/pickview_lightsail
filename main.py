# main.py

from product_detail_retrieval import fetch_product_details
from review_crawling_and_summarization import crawl_reviews, summarize_reviews
from purchase_guide_creation import generate_purchase_guide
from html_template_generation import generate_html_post
from wordpress_uploader import upload_post_to_wordpress

def main(product_id, product_url, wordpress_url, username, password):
    # 1. 제품 상세 정보 가져오기
    product_info = fetch_product_details(product_id)
    
    if product_info:
        # 2. 리뷰 크롤링
        reviews = crawl_reviews(product_url)
        
        if reviews:
            # 3. 리뷰 요약
            review_summary = summarize_reviews(reviews)
            
            # 4. 구매 가이드 생성
            purchase_guide = generate_purchase_guide(product_info, review_summary)
            
            # 5. HTML 포스트 생성
            html_post = generate_html_post(product_info, review_summary, purchase_guide)
            
            # 6. WordPress에 포스트 업로드
            upload_post_to_wordpress(product_info['title'], html_post, wordpress_url, username, password)

if __name__ == "__main__":
    product_id = "123456"  # 예시 제품 ID
    product_url = "https://example.com/product/123456"  # 예시 제품 URL
    wordpress_url = "https://yourwordpresssite.com"  # 실제 WordPress URL로 변경
    username = "your_username"  # WordPress 사용자 이름
    password = "your_password"  # WordPress 비밀번호
    
    main(product_id, product_url, wordpress_url, username, password)
