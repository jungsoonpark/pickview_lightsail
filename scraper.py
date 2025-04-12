import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import logging
import traceback
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 구글 시트 설정
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
JSON_KEY = os.getenv("GOOGLE_JSON_KEY")
READ_SHEET_NAME = 'list'      # 구글 시트에서 날짜, 키워드가 있는 시트; 열: [date, keyword]
RESULT_SHEET_NAME = 'result'  # 결과 저장 시트; 열: [date, keyword, product_id]

def connect_to_google_sheet(sheet_name):
    logging.info("Google Sheet 연결 시도...")
    try:
        scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(JSON_KEY, scopes=scopes)
        client = gspread.authorize(creds)
        # URL 방식으로 열어서 연결 (더 명시적)
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
        sheet = connect_to_google_sheet(RESULT_SHEET_NAME)
        sheet.clear()
        # 헤더 추가
        sheet.append_row(['date', 'keyword', 'product_id'])
        for row in results:
            sheet.append_row(row)
        logging.info(f"구글 시트에 결과 저장 완료: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    except Exception as e:
        logging.error(f"결과 저장 실패: {e}")
        traceback.print_exc()

def dynamic_selector_search(page, keyword):
    # 다양한 셀렉터 후보를 리스트로 구성합니다.
    selectors = [
        'a[data-product-id]',  # 과거 자주 사용된 방식
        'div[data-spm="itemlist"] a[href*="/item/"]',  # 리스트 형태
        'a[href*="/item/"]'  # 좀 더 일반적인 패턴
    ]
    for selector in selectors:
        try:
            logging.info(f"[{keyword}] 셀렉터 시도: {selector}")
            page.wait_for_selector(selector, timeout=10000)
            elements = page.query_selector_all(selector)
            logging.info(f"[{keyword}] 셀렉터 '{selector}'로 {len(elements)}개 요소 발견")
            if elements:
                return elements
        except PlaywrightTimeoutError as te:
            logging.warning(f"[{keyword}] 셀렉터 '{selector}' 타임아웃: {te}")
        except Exception as e:
            logging.error(f"[{keyword}] 셀렉터 '{selector}' 오류: {e}")
    return []

def scrape_product_ids(keyword):
    product_ids = []
    try:
        with sync_playwright() as p:
            logging.info(f"[{keyword}] Playwright 브라우저 실행")
            browser = p.chromium.launch(headless=True, timeout=60000)
            context = browser.new_context(
                # 한국어 페이지 보장을 위해 locale 및 User-Agent를 한국용으로 설정합니다.
                locale='ko-KR',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            url = f'https://www.aliexpress.com/wholesale?SearchText={keyword}&SortType=total_tranpro_desc'
            logging.info(f"[{keyword}] 페이지 열기: {url}")
            page.goto(url, timeout=60000, wait_until='domcontentloaded')
            logging.info(f"[{keyword}] 페이지 로딩 완료, 3초 대기")
            time.sleep(3)
            # 동적으로 셀렉터 시도
            elements = dynamic_selector_search(page, keyword)
            if not elements:
                logging.error(f"[{keyword}] 유효한 셀렉터를 찾지 못했습니다.")
            else:
                # 상위 5개 상품만 취함
                for element in elements[:5]:
                    href = element.get_attribute('href')
                    if href:
                        try:
                            # 예시: https://www.aliexpress.com/item/1234567890.html 등에서 상품 ID 추출
                            # 혹은 href 형식이 다를 수 있으므로 로직을 유연하게 구성합니다.
                            if '/item/' in href:
                                product_id = href.split('/item/')[1].split('.')[0]
                            else:
                                product_id = href
                            product_ids.append(product_id)
                            logging.info(f"[{keyword}] 추출 상품 ID: {product_id}")
                        except Exception as e:
                            logging.error(f"[{keyword}] href 파싱 오류: {href} - {e}")
            browser.close()
    except Exception as e:
        logging.error(f"[{keyword}] 크롤링 도중 예외 발생: {e}")
        traceback.print_exc()
    return product_ids

def main():
    logging.info("[START] 프로그램 시작")
    keywords = get_keywords_from_google_sheet()
    if not keywords:
        logging.error("키워드가 없습니다. 프로그램 종료합니다.")
        return
    results = []
    today = datetime.today().strftime('%Y-%m-%d')
    for keyword in keywords:
        logging.info(f"[PROCESS] '{keyword}' 작업 시작")
        ids = scrape_product_ids(keyword)
        if ids:
            for pid in ids:
                results.append([today, keyword, pid])
        else:
            logging.warning(f"[{keyword}] 크롤링 결과 0개")
        logging.info(f"[{keyword}] 작업 종료, 2초 대기")
        time.sleep(2)
    if results:
        save_results_to_sheet(results)
    else:
        logging.warning("최종 결과가 없습니다.")
    logging.info("[END] 프로그램 종료")

if __name__ == '__main__':
    main()
