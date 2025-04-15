import logging
import requests
import traceback
import openai

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# OpenAI API 키 설정
openai.api_key = "YOUR_OPENAI_API_KEY"

# 리뷰를 크롤링하고 요약하는 함수
def get_and_summarize_reviews(product_id, extracted_reviews, reviews_needed=5):
    try:
        url = f"https://feedback.aliexpress.com/pc/searchEvaluation.do?productId={product_id}&lang=ko_KR&country=KR&page=1&pageSize=10&filter=5&sort=complex_default"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            logging.error(f"[{product_id}] 리뷰 데이터 요청 실패, 상태 코드: {response.status_code}, 내용: {response.text}")
            return None
        
        # JSON 형식 확인
        if 'application/json' in response.headers.get('Content-Type', ''):
            data = response.json()
        else:
            logging.error(f"[{product_id}] JSON 형식이 아닙니다: {response.text}")
            return None

        reviews = data.get('data', {}).get('evaViewList', [])
        if not reviews:
            return None

        # 'buyerTranslationFeedback' 추출
        extracted_reviews += [review.get('buyerTranslationFeedback', '') for review in reviews if review.get('buyerTranslationFeedback')]

        # 중간 로깅: 리뷰 수집 완료 후 출력
        logging.info(f"[{product_id}] 리뷰 수집 완료: {len(extracted_reviews)}개")

        if len(extracted_reviews) < reviews_needed:
            logging.warning(f"[{product_id}] 필요한 리뷰 수({reviews_needed})에 미치지 못했습니다.")
            return None
        
        # 리뷰 요약
        result = summarize_reviews(extracted_reviews, product_id)
        if result is None:
            return None
        
        review_content1, review_content2 = result
        return review_content1, review_content2
    except Exception as e:
        logging.error(f"[{product_id}] 리뷰 크롤링 도중 예외 발생: {e}")
        traceback.print_exc()
        return None


# 리뷰를 요약하는 함수
def summarize_reviews(reviews, product_title):
    reviews_text = "\n".join(reviews)
    try:
        # review_content1: 10-15자 이내로 간결한 카피라이팅 문구 작성
        response1 = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user",
                    "content": f"다음 상품 제목과 리뷰를 바탕으로 이 상품의 가장 핵심적인 장점을 10-20자 이내로 간결하게 표현하는 카피라이팅 문구를 작성해 주세요. 리뷰 내용: {reviews_text}. 상품 제목: {product_title}"
                }
            ],
            timeout=30
        )
        
        review_content1 = response1['choices'][0]['message']['content'].strip()

        logging.info(f"상품 제목: {product_title}, 카피라이팅 문구: {review_content1}")

        # review_content2: 상품의 추가적인 긍정적인 특징을 15-40자 이내로 자연스럽게 작성
        response2 = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user", 
                    "content": f"다음 상품 제목과 리뷰를 바탕으로, '{review_content1}'에서 다루지 않은 추가적인 장점을 문장당 15-40자 이내의 1~2개 문장으로 작성해 주세요. 리뷰 내용: {reviews_text}. 상품 제목: {product_title}"
                }
            ],
            timeout=30
        )
        
        review_content2 = response2['choices'][0]['message']['content'].strip()

        # 5개 리뷰가 안 채워지면 다음 상품을 가져오는 로직 추가
        if len(review_content1) == 0 or len(review_content2) == 0:
            return None  # 리뷰 추출 또는 요약 실패시 None 반환

        return review_content1, review_content2
    except Exception as e:
        logging.error(f"GPT 요약 중 오류 발생: {e}")
        traceback.print_exc()
        return None  # 오류 발생 시 None 반환
