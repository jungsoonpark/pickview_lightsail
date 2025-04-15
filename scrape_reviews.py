import logging
import time
from datetime import datetime
import traceback
import gspread
from google.oauth2.service_account import Credentials
import requests
import openai
import os

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, 
    format='[%(levelname)s] %(asctime)s - %(message)s', 
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 구글 시트 설정
SHEET_ID = "1Ew7u6N72VP3nVvgNiLKZDyIpHg4xXz-prkyV4SW7EkI"
JSON_KEY_PATH = '/home/ubuntu/pickview-be786ad8e194.json'  # JSON 파일 경로
READ_SHEET_NAME = 'list'      # 키워드가 있는 시트
RESULT_SHEET_NAME = 'result'  # 결과 저장 시트 (날짜, 키워드, product_id, review_content1, review_content2)

# OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

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
            (row['product_id'], row['keyword'], row['review_content1'], row['review_content2'], index+2)  # 행 인덱스를 직접 사용
            for index, row in enumerate(data) 
            if str(row.get('date', '')) == today  # 오늘 날짜의 상품들만 필터링
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

        # 첫 번째 행에서 열 이름을 가져오기
        header = sheet.row_values(1)
        
        # 열 이름을 기준으로 각 열의 인덱스를 찾기 (0-based index)
        date_col = header.index('date') + 1  # 'date' 열 (1-based index)
        keyword_col = header.index('keyword') + 1  # 'keyword' 열
        product_id_col = header.index('product_id') + 1  # 'product_id' 열
        title_col = header.index('title') + 1  # 'title' 열
        review_content1_col = header.index('review_content1') + 1  # 'review_content1' 열
        review_content2_col = header.index('review_content2') + 1  # 'review_content2' 열

        for row in results:
            row_number = row[5]  # 리뷰를 저장할 행 번호

            # 각 열 번호에 맞게 업데이트
            sheet.update_cell(row_number, date_col, row[0])  # date
            sheet.update_cell(row_number, keyword_col, row[1])  # keyword
            sheet.update_cell(row_number, product_id_col, row[2])  # product_id
            sheet.update_cell(row_number, title_col, row[3])  # title
            sheet.update_cell(row_number, review_content1_col, row[4])  # review_content1
            sheet.update_cell(row_number, review_content2_col, row[5])  # review_content2

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
    product_ids = get_product_ids_from_google_sheet()  # `result` 시트에서 상품 ID 리스트 가져오기
    if not product_ids:
        logging.error("리뷰를 추출할 상품이 없습니다. 프로그램 종료합니다.")
        return

    results = []
    today = datetime.today().strftime('%Y-%m-%d')

    for product_id, keyword, review_content1, review_content2, row_number in product_ids:
        logging.info(f"[{keyword}] '{product_id}' 작업 시작")
        
        # 리뷰 크롤링 및 요약
        if not review_content1 or not review_content2:  # 비어있는 부분만 리뷰 추출
            result = get_and_summarize_reviews(product_id, keyword)
            
            if result:
                review_content1, review_content2 = result
                results.append([today, keyword, product_id, review_content1, review_content2, row_number])
            else:
                logging.warning(f"[{keyword}] 리뷰가 없는 상품 제외: {product_id}")
        else:
            logging.info(f"[{keyword}] 리뷰가 이미 존재합니다. 건너뜁니다.")

        logging.info(f"[{keyword}] 작업 종료, 2초 대기")
        time.sleep(2)

    if results:
        save_reviews_to_sheet(results)
    else:
        logging.warning("최종 결과가 없습니다.")
    
    logging.info("[END] 프로그램 종료")

if __name__ == "__main__":
    main()
