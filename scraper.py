import pandas as pd
from playwright.sync_api import sync_playwright
import time
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ✅ 구글 시트 설정
SHEET_ID = '1Ew7u6N72VP3nVvgNiLKZDyIpHg4xXz-prkyV4SW7EkI'
JSON_KEY = 'pickview-be786ad8e194.json'
READ_SHEET_NAME = 'list'       # 키워드 시트
WRITE_SHEET_NAME = 'result'    # 결과 저장 시트

# ✅ 구글 시트 연결
def connect_to_google_sheet(sheet_name):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(JSON_KEY, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    return sheet

# ✅ 키워드 가져오기 (오늘 날짜 기준)
def get_keywords_from_google_sheet():
    sheet = connect_to_google_sheet(READ_SHEET_NAME)
    data = sheet.get_all_records()
    today = datetime.today().strftime('%Y-%m-%d')
    keywords = [row['keyword'] for row in data if str(row['date']) == today]
    print(f"✅ {len(keywords)}개의 키워드를 수집했습니다: {keywords}")
    return keywords

# ✅ 구글 시트 저장
def save_results_to_google_sheet(results):
    sheet = connect_to_google_sheet(WRITE_SHEET_NAME)
    sheet.clear()
    sheet.append_row(["date", "keyword", "product_id"])
    for row in results:
        sheet.append_row(row)
    print(f"✅ 구글 시트에 저장 완료: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

# ✅ 상품 ID 수집
def scrape_product_ids(keyword):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            locale='ko-KR',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        url = f'https://www.aliexpress.com/wholesale?SearchText={keyword}&SortType=total_tranpro_desc'
        print(f"\n🔍 키워드 '{keyword}' 상품 수집 시작")
        print(f"[INFO] 검색 URL: {url}")

        try:
            page.goto(url, timeout=60000)
            print(f"[INFO] '{keyword}' 페이지 진입 성공")
        except Exception as e:
            print(f"[ERROR] '{keyword}' 페이지 진입 실패: {e}")
            browser.close()
            return []

        time.sleep(2)  # 페이지 안정화 대기

        selectors = [
            'div[data-spm="itemlist"] a[href*="/item/"]',
            'a[itemprop="url"]',
            'a[href*="/item/"]'
        ]

        elements = []
        for selector in selectors:
            try:
                print(f"[INFO] '{keyword}' 셀렉터 시도: {selector}")
                page.wait_for_selector(selector, timeout=10000)
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"[SUCCESS] '{keyword}' 셀렉터 찾음: {selector}")
                    break
            except Exception as e:
                print(f"[WARNING] '{keyword}' 셀렉터 실패: {selector} / {e}")

        if not elements:
            print(f"[ERROR] '{keyword}' 유효한 셀렉터를 찾지 못했습니다.")
            browser.close()
            return []

        product_ids = []
        for element in elements[:5]:  # 정확히 5개 상품만
            href = element.get_attribute('href')
            if href:
                try:
                    product_id = href.split('/')[-1].split('.')[0]
                    product_ids.append(product_id)
                except Exception as e:
                    print(f"[WARNING] href 파싱 실패: {href} / {e}")

        print(f"✅ 키워드 '{keyword}'에서 {len(product_ids)}개 상품 수집 완료.")
        browser.close()
        return product_ids

# ✅ 메인 실행
def main():
    keywords = get_keywords_from_google_sheet()
    all_results = []
    today = datetime.today().strftime('%Y-%m-%d')

    for keyword in keywords:
        product_ids = scrape_product_ids(keyword)
        for product_id in product_ids:
            all_results.append([today, keyword, product_id])
        time.sleep(2)  # 키워드 간 대기

    save_results_to_google_sheet(all_results)
    print("🎉 모든 작업 완료!")

if __name__ == '__main__':
    main()
