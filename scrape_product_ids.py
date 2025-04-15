import logging
import time
from datetime import datetime
import traceback
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

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
RESULT_SHEET_NAME = 'result'  # 결과 저장 시트 (날짜, 키워드, product_id, title, review_content1, review_content2)

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

def get_keywords_from_google_sheet():
    try:
        sheet = connect_to_google_sheet(READ_SHEET_NAME)
        data = sheet.get_all_records()
        today = datetime.today().strftime('%Y-%m-%d')
        keywords = [row['keyword'] for row in data if str(row.get('date', '')) == today]
        logging.info(f"오늘 날짜({today}) 키워드 수집 완료: {keywords}")
        return keywords
    except Exception as e:
        logging.error(f"키워드 수집 실패: {e}")
        traceback.print_exc()
        return []

def save_results_to_sheet(results):
    try:
        if not results:
            logging.warning("저장할 결과가 없습니다.")
            return
        sheet = connect_to_google_sheet(RESULT_SHEET_NAME)
        for row in results:
            # result 시트의 열: [날짜, keyword, product_id, title, review_content1, review_content2]
            sheet.append_row(row)
        logging.info(f"구글 시트에 결과 저장 완료: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    except Exception as e:
        logging.error(f"결과 저장 실패: {e}")
        traceback.print_exc()

def scrape_product_ids_and_titles(keyword):
    product_data = []  # (상품 ID, 상품 제목) 튜플을 저장할 리스트
    tried_products = set()  # 중복 방지를 위한 set

    if not keyword:
        logging.warning("검색어가 비어 있습니다. 건너뜁니다.")
        return product_data

    try:
        with sync_playwright() as p:
            logging.info(f"[{keyword}] Playwright 브라우저 실행")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale='ko-KR')
            page = context.new_page()

            url = f'https://www.aliexpress.com/wholesale?SearchText={keyword}&SortType=total_tranpro_desc'
            page.goto(url, wait_until='domcontentloaded')
            logging.info(f"[{keyword}] 페이지 로딩 완료")
            time.sleep(3)

            page.wait_for_load_state('load')

            for _ in range(2):
                page.evaluate('window.scrollBy(0, window.innerHeight);')
                time.sleep(2)

            # 상위 5개 상품만 처리
            product_elements = page.query_selector_all('a[href*="/item/"]')[:5]
            if not product_elements:
                return product_data

            for element in product_elements:
                href = element.get_attribute('href')
                if href:
                    product_id = href.split('/item/')[1].split('.')[0]
                    if product_id in tried_products:
                        logging.warning(f"[{keyword}] 이미 처리한 상품 ID: {product_id}, 건너뜁니다.")
                        continue
                    tried_products.add(product_id)

                    product_title = element.inner_text().strip().split('\n')[0]
                    if not product_title:
                        continue
                    
                    product_data.append((product_id, product_title))
                    logging.info(f"[{keyword}] 상품 ID: {product_id}, 제목: {product_title}")

            browser.close()
    except Exception as e:
        logging.error(f"[{keyword}] 크롤링 도중 예외 발생: {e}")
        traceback.print_exc()
    return product_data

def main():
    keywords = get_keywords_from_google_sheet()
    if not keywords:
        logging.error("키워드가 없습니다. 프로그램 종료합니다.")
        return

    results = []
    today = datetime.today().strftime('%Y-%m-%d')
    
    for keyword in keywords:
        if not keyword:
            logging.warning("빈 키워드 발견, 건너뜁니다.")
            continue
        
        logging.info(f"[PROCESS] '{keyword}' 작업 시작")
        product_data = scrape_product_ids_and_titles(keyword)
        if not product_data:
            logging.warning(f"[{keyword}] 상품 정보가 없습니다.")
        else:
            # result 시트에 저장할 형식: [날짜, keyword, product_id, title, "", ""]
            for product_id, product_title in product_data:
                results.append([today, keyword, product_id, product_title, "", ""])
        
        logging.info(f"[{keyword}] 작업 종료, 2초 대기")
        time.sleep(2)
    
    if results:
        save_results_to_sheet(results)
    else:
        logging.warning("최종 결과가 없습니다.")
    
    logging.info("[END] 프로그램 종료")

if __name__ == "__main__":
    main()
