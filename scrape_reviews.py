import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import logging
import traceback

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
            (row['product_id'], row['keyword'], row['review_content1'], row['review_content2'], row['date'], row['row_number'])
            for row in data 
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
        for row in results:
            # 'row_number'와 'product_id'를 사용하여 해당 행을 찾아 리뷰를 업데이트합니다.
            sheet.update_cell(row[4], 4, row[3])  # review_content1 열 업데이트
            sheet.update_cell(row[4], 5, row[4])  # review_content2 열 업데이트
        logging.info(f"구글 시트에 리뷰 저장 완료: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    except Exception as e:
        logging.error(f"결과 저장 실패: {e}")
        traceback.print_exc()

def get_and_summarize_reviews(product_id, keyword):
    # 리뷰 추출 및 요약 코드 동일 (생략)
    # 이 부분은 앞서 설명한 대로 review_content1, review_content2를 추출하여 반환하는 형태로 진행됩니다.
    pass

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
