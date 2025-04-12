import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
import time
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

JSON_KEY = 'pickview-be786ad8e194.json'
READ_SHEET_NAME = 'list'
RESULT_SHEET_NAME = 'result'

def connect_to_google_sheet(sheet_name):
    logging.info('Google Sheet 연결 시도')
    scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(JSON_KEY, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1Ew7u6N72VP3nVvgNiLKZDyIpHg4xXz-prkyV4SW7EkI/edit').worksheet(sheet_name)
    logging.info(f'Google Sheet "{sheet_name}" 연결 성공')
    return sheet

def get_keywords_from_google_sheet():
    sheet = connect_to_google_sheet(READ_SHEET_NAME)
    data = sheet.get_all_records()
    today = pd.Timestamp.now().strftime('%Y-%m-%d')
    keywords = [row['keyword'] for row in data if str(row['date']) == today]
    logging.info(f'오늘 날짜 키워드 수집 완료: {keywords}')
    return keywords

def save_results_to_sheet(results):
    sheet = connect_to_google_sheet(RESULT_SHEET_NAME)
    sheet.clear()
    sheet.append_row(['date', 'keyword', 'product_id'])
    for row in results:
        sheet.append_row(row)
    logging.info('구글 시트에 결과 저장 완료')

def extract_product_ids(page):
    logging.info('상품 ID 추출 시도 중...')
    try:
        product_elements = page.query_selector_all('a[data-product-id]')
        product_ids = [element.get_attribute('data-product-id') for element in product_elements]
        logging.info(f'상품 ID {len(product_ids)}개 추출 완료')
        return product_ids
    except Exception as e:
        logging.error(f'상품 ID 추출 중 오류 발생: {e}')
        return []

def scrape(keyword):
    logging.info(f'크롤링 시작 - 키워드: {keyword}')
    url = f'https://www.aliexpress.com/wholesale?SearchText={keyword}&SortType=total_tranpro_desc'

    with sync_playwright() as p:
        logging.info('브라우저 실행 중...')
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        logging.info(f'페이지 열기: {url}')
        page.goto(url, timeout=60000)
        time.sleep(3)

        product_ids = extract_product_ids(page)[:5]  # 최대 5개
        browser.close()
        return product_ids

def main():
    logging.info('[START] 프로그램 시작')
    try:
        keywords = get_keywords_from_google_sheet()
    except Exception as e:
        logging.error(f'구글 시트 키워드 수집 실패: {e}')
        return

    results = []
    for keyword in keywords:
        try:
            product_ids = scrape(keyword)
            today = pd.Timestamp.now().strftime('%Y-%m-%d')
            for product_id in product_ids:
                results.append([today, keyword, product_id])
        except Exception as e:
            logging.error(f'크롤링 실패 - 키워드: {keyword}, 오류: {e}')
        time.sleep(2)

    if results:
        try:
            save_results_to_sheet(results)
        except Exception as e:
            logging.error(f'결과 저장 실패: {e}')

    logging.info('[END] 프로그램 종료')

if __name__ == '__main__':
    main()
