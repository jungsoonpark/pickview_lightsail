import pandas as pd
from playwright.sync_api import sync_playwright
import time
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ✅ 구글 시트 설정
SHEET_ID = '1Ew7u6N72VP3nVvgNiLKZDyIpHg4xXz-prkyV4SW7EkI'
JSON_KEY = 'pickview-be786ad8e194.json'
READ_SHEET_NAME = 'list'
WRITE_SHEET_NAME = 'result'

# ✅ 구글 시트 연결 함수
def connect_to_google_sheet(sheet_name):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(JSON_KEY, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    return sheet

# ✅ 오늘 날짜 키워드 가져오기
def get_keywords_from_google_sheet():
    sheet = connect_to_google_sheet(READ_SHEET_NAME)
    data = sheet.get_all_records()
    today = datetime.now().strftime("%Y-%m-%d")
    keywords = [row['keyword'] for row in data if row.get('date') == today]
    print(f"✅ {len(keywords)}개의 키워드를 수집했습니다: {keywords}")
    return keywords

# ✅ 구글 시트 저장 함수
def save_to_google_sheet(results):
    sheet = connect_to_google_sheet(WRITE_SHEET_NAME)
    sheet.clear()
    sheet.append_row(["date", "keyword", "product_id"])
    for row in results:
        sheet.append_row(row)
    print(f"✅ 구글 시트에 저장 완료: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

# ✅ 상품 수집 함수
def scrape_products(keyword, max_results=5):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            url = f'https://www.aliexpress.com/wholesale?SearchText={keyword}&SortType=total_tranpro_desc'
            print(f"\n🔍 키워드 '{keyword}' 상품 수집 시작")
            print(f"[INFO] 검색 URL: {url}")

            page.goto(url, timeout=120000)
            page.wait_for_load_state('networkidle',timeout=120000)
            time.sleep(2)

            # ✅ 동적 셀렉터 대응 (복수 시도)
            selector_candidates = [
                'a[data-product-id]',
                'div[data-spm="itemlist"] a[href*="/item/"]',
                'a[href*="/item/"]',
            ]

            elements = []
            for selector in selector_candidates:
                try:
                    page.wait_for_selector(selector, timeout=4000)
                    elements = page.query_selector_all(selector)
                    if elements:
                        break
                except:
                    continue

            if not elements:
                print(f"[WARNING] '{keyword}' 페이지에서 셀렉터 미발견")
                return []

            product_ids = []
            for element in elements:
                href = element.get_attribute('href')
                if href and '/item/' in href:
                    product_id = href.split('/item/')[1].split('.')[0]
                    if product_id not in product_ids:
                        product_ids.append(product_id)
                    if len(product_ids) >= max_results:
                        break

            print(f"✅ 키워드 '{keyword}'에서 {len(product_ids)}개 상품 수집 완료.")
            browser.close()
            return product_ids

    except Exception as e:
        print(f"[ERROR] 크롤링 실패: {e}")
        return []

# ✅ 메인 함수
def main():
    keywords = get_keywords_from_google_sheet()
    all_results = []
    today = datetime.now().strftime("%Y-%m-%d")

    for keyword in keywords:
        product_ids = scrape_products(keyword)
        for product_id in product_ids:
            all_results.append([today, keyword, product_id])

        # ✅ 매 키워드마다 저장
        save_to_google_sheet(all_results)

        # ✅ 너무 빠르지 않게 대기
        time.sleep(3)

    print("🎉 모든 작업 완료!")

# ✅ 실행
if __name__ == '__main__':
    main()
