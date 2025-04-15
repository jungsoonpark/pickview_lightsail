import logging
import time
from playwright.sync_api import sync_playwright
import traceback
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 구글 시트 연결 설정
SHEET_ID = "1Ew7u6N72VP3nVvgNiLKZDyIpHg4xXz-prkyV4SW7EkI"
JSON_KEY_PATH = '/home/ubuntu/pickview-be786ad8e194.json'  # JSON 파일 경로 설정
READ_SHEET_NAME = 'list'  # 구글 시트에서 날짜, 키워드가 있는 시트

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 구글 시트 연결 함수
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

# 구글 시트에서 키워드 가져오기
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

# 상품 ID와 제목을 크롤링하는 함수
def scrape_product_ids_and_titles(keyword):
    product_data = []  # 상품 ID와 제목을 저장할 리스트
    tried_products = set()  # 이미 시도한 상품을 기록할 set (중복 방지)

    if not keyword:  # 키워드가 None일 경우 바로 종료
        logging.warning(f"검색어가 비어 있습니다. 건너뜁니다.")
        return product_data  # 빈 키워드면 바로 종료

    try:
        with sync_playwright() as p:
            logging.info(f"[{keyword}] Playwright 브라우저 실행")
            browser = p.chromium.launch(headless=True)  # headless=True로 설정
            context = browser.new_context(locale='ko-KR')
            page = context.new_page()

            url = f'https://www.aliexpress.com/wholesale?SearchText={keyword}&SortType=total_tranpro_desc'
            page.goto(url, wait_until='domcontentloaded')  # 페이지가 로드될 때까지 대기
            logging.info(f"[{keyword}] 페이지 로딩 완료")
            time.sleep(3)  # 로딩 완료 후 잠시 대기

            # 페이지 완전히 로드 대기
            page.wait_for_load_state('load')  # 페이지가 완전히 로드될 때까지 대기

            # 스크롤을 통해 더 많은 상품을 로딩
            for _ in range(2):  # 페이지 2번 스크롤하여 추가 로드
                page.evaluate('window.scrollBy(0, window.innerHeight);')
                time.sleep(2)  # 스크롤 후 대기

            # 상위 5개 상품만 처리
            product_elements = page.query_selector_all('a[href*="/item/"]')[:5]  # 상위 5개만 선택

            if not product_elements:
                return product_data  # 상품 요소가 없다면 바로 반환

            for element in product_elements:
                href = element.get_attribute('href')
                if href:
                    product_id = href.split('/item/')[1].split('.')[0]  # 상품 ID 추출

                    # 이미 시도한 상품 ID는 건너뜁니다.
                    if product_id in tried_products:
                        logging.warning(f"[{keyword}] 이미 처리한 상품 ID: {product_id}, 건너뜁니다.")
                        continue
                    tried_products.add(product_id)  # 상품 ID를 시도 목록에 추가

                    # 상품 제목 추출
                    product_title = element.inner_text().strip().split('\n')[0]  # 상품 제목만 추출 (가격 등 정보는 제외)

                    # 제목이 없는 경우 건너뛰기
                    if not product_title:
                        continue  # 상품 제목이 없는 경우 건너뛰기
                    
                    # 추출된 상품 ID와 제목을 튜플로 저장
                    product_data.append((product_id, product_title))
                    logging.info(f"[{keyword}] 상품 ID: {product_id}, 제목: {product_title}")

            browser.close()
    except Exception as e:
        logging.error(f"[{keyword}] 크롤링 도중 예외 발생: {e}")
        traceback.print_exc()

    return product_data

# main 함수
def main():
    keywords = get_keywords_from_google_sheet()  # Google Sheets에서 키워드 가져오기
    if not keywords:
        logging.error("키워드가 없습니다. 프로그램 종료합니다.")
        return

    all_product_data = []

    for keyword in keywords:
        logging.info(f"[PROCESS] '{keyword}' 작업 시작")
        product_data = scrape_product_ids_and_titles(keyword)  # 제품 ID 크롤링

        if product_data:
            all_product_data.extend(product_data)
        else:
            logging.warning(f"[{keyword}] 상품 ID가 없습니다.")

    logging.info(f"총 {len(all_product_data)}개의 상품 정보가 추출되었습니다.")
    for product in all_product_data:
        logging.info(f"상품 ID: {product[0]}, 제목: {product[1]}")

# 실행 코드
if __name__ == "__main__":
    main()
