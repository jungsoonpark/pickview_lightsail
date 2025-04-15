import requests
import logging
import traceback

def get_and_summarize_reviews(product_id, extracted_reviews, reviews_needed=5, keyword=None):
    try:
        # 상품 제목 추출
        product_data = scrape_product_ids_and_titles(keyword)
        product_title = next((title for pid, title in product_data if pid == product_id), 'No title')

        # 리뷰 크롤링 및 요약 처리
        url = f"https://feedback.aliexpress.com/pc/searchEvaluation.do?productId={product_id}&lang=ko_KR&country=KR&page=1&pageSize=10&filter=5&sort=complex_default"
        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            logging.error(f"[{product_id}] 리뷰 페이지 요청 실패, 상태 코드: {response.status_code}")
            return None

        # 응답이 JSON 형식인지 확인
        try:
            data = response.json()  # JSON 파싱
            logging.info(f"[{product_id}] JSON 파싱 성공")
        except ValueError:
            logging.error(f"[{product_id}] JSON 파싱 실패, HTML 응답을 받았음")
            return None
        
        # 리뷰 데이터 추출
        reviews = data.get('data', {}).get('evaViewList', [])
        if not reviews:
            logging.warning(f"[{product_id}] 리뷰가 없습니다.")
            return None

        # 필요한 리뷰 수만큼 추출
        extracted_reviews += [review.get('buyerTranslationFeedback', '') for review in reviews if review.get('buyerTranslationFeedback')]

        # 중간 로깅: 리뷰 수집 완료 후 출력
        logging.info(f"[{product_id}] 리뷰 수집 완료: {len(extracted_reviews)}개")

        if len(extracted_reviews) < reviews_needed:
            return None

        # 리뷰 요약
        result = summarize_reviews(extracted_reviews, product_title)
        if result is None:
            return None
        
        review_content1, review_content2 = result
        return review_content1, review_content2

    except Exception as e:
        logging.error(f"[{product_id}] 리뷰 크롤링 도중 예외 발생: {e}")
        traceback.print_exc()
        return None
