import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import logging
import traceback
import time
import requests
import openai



# 구글 시트 설정
SHEET_ID = "1Ew7u6N72VP3nVvgNiLKZDyIpHg4xXz-prkyV4SW7EkI"
JSON_KEY_PATH = '/home/ubuntu/pickview-be786ad8e194.json'  # JSON 파일 경로
RESULT_SHEET_NAME = 'result'  # 결과 저장 시트 (날짜, 키워드, product_id, review_content1, review_content2)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def connect_to_google_sheet(sheet_name):
    logging.info("Google Sheet 연결 시도...")
    try:
        scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(JSON_KEY_PATH, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
        logging.info(f'Google Sheet "{sheet_name}" 연결 성공')
        return sheet
    except Exception as e:
        logging.error(f"구글 시트 연결 실패: {e}")
        traceback.print_exc()
        raise

def get_product_ids_from_google_sheet():
    try:
        sheet = connect_to_google_sheet(RESULT_SHEET_NAME)
        data = sheet.get_all_records()
        today = datetime.today().strftime('%Y-%m-%d')  # 오늘 날짜 가져오기
        product_ids = [
            (row['product_id'], row['keyword'], row['review_content1'], row['review_content2'], row['date'], idx+2)  # 행 번호 추가
            for idx, row in enumerate(data) 
            if str(row.get('date', '')) == today and (not row['review_content1'] or not row['review_content2'])  # 비어있는 리뷰만
        ]
        logging.info(f"오늘 날짜({today}) 리뷰 추출할 상품 ID 리스트 수집 완료: {product_ids}")
        return product_ids
    except Exception as e:
        logging.error(f"상품 ID 수집 실패: {e}")
        traceback.print_exc()
        return []


def save_reviews_to_sheet(results):
    try:
        if not results:
            logging.warning("저장할 리뷰가 없습니다.")
            return
        sheet = connect_to_google_sheet(RESULT_SHEET_NAME)
        
        # 열 이름 기준으로 열 번호를 매핑
        headers = sheet.row_values(1)  # 첫 번째 행에 열 이름이 있기 때문에 이를 기준으로 열 번호를 추출
        title_index = headers.index('title') + 1
        review_content1_index = headers.index('review_content1') + 1
        review_content2_index = headers.index('review_content2') + 1

        for row in results:
            row_number = int(row[5])  # row[5]는 row_number (정수로 변환)
            # 리뷰 내용이 있으면 review_content1, review_content2 열에 각각 넣기
            sheet.update_cell(row_number, review_content1_index, row[3])  # review_content1 업데이트
            sheet.update_cell(row_number, review_content2_index, row[4])  # review_content2 업데이트
        
        logging.info(f"구글 시트에 리뷰 저장 완료: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    except Exception as e:
        logging.error(f"결과 저장 실패: {e}")
        traceback.print_exc()





def get_and_summarize_reviews(product_id, keyword):
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
            logging.warning(f"[{product_id}] 리뷰가 없습니다.")
            return None

        # buyerTranslationFeedback 추출
        extracted_reviews = [review.get('buyerTranslationFeedback', '') for review in reviews if review.get('buyerTranslationFeedback')]
        logging.info(f"[{product_id}] 리뷰 수집 완료: {len(extracted_reviews)}개")

        if len(extracted_reviews) < 1:
            logging.warning(f"[{product_id}] 필요한 리뷰가 부족합니다.")
            return None
        
        # 리뷰 요약
        result = summarize_reviews(extracted_reviews, keyword)
        if result is None:
            return None
        
        review_content1, review_content2 = result
        return review_content1, review_content2

    except Exception as e:
        logging.error(f"[{product_id}] 리뷰 크롤링 도중 예외 발생: {e}")
        traceback.print_exc()
        return None




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

        return review_content1, review_content2
    except Exception as e:
        logging.error(f"GPT 요약 중 오류 발생: {e}")
        traceback.print_exc()
        return None




def main():
    product_ids = get_product_ids_from_google_sheet()  # 'result' 시트에서 상품 ID 리스트 가져오기
    if not product_ids:
        logging.error("리뷰를 추출할 상품이 없습니다. 프로그램 종료합니다.")
        return

    results = []
    today = datetime.today().strftime('%Y-%m-%d')

    for product_id, keyword, review_content1, review_content2, date, row_number in product_ids:
        logging.info(f"[{keyword}] '{product_id}' 작업 시작")
        
        # 리뷰 크롤링 및 요약
        result = get_and_summarize_reviews(product_id, keyword)
        
        if result:
            # 결과가 있을 경우 review_content1, review_content2 갱신
            review_content1, review_content2 = result
            results.append([today, keyword, product_id, review_content1, review_content2, row_number])
        else:
            logging.warning(f"[{keyword}] 리뷰가 없는 상품 제외: {product_id}")
        
        logging.info(f"[{keyword}] 작업 종료, 2초 대기")
        time.sleep(2)

    if results:
        save_reviews_to_sheet(results)
    else:
        logging.warning("최종 결과가 없습니다.")
    
    logging.info("[END] 프로그램 종료")

if __name__ == "__main__":
    main()
