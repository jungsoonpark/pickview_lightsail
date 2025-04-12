import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import logging
import traceback
from datetime import datetime
import requests
import openai
from bs4 import BeautifulSoup

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 구글 시트 설정
SHEET_ID = "1Ew7u6N72VP3nVvgNiLKZDyIpHg4xXz-prkyV4SW7EkI"
JSON_KEY_PATH = '/home/ubuntu/pickview-be786ad8e194.json'  # JSON 파일 경로 설정
READ_SHEET_NAME = 'list'      # 구글 시트에서 날짜, 키워드가 있는 시트; 열: [date, keyword]
RESULT_SHEET_NAME = 'result'  # 결과 저장 시트; 열: [date, keyword, product_id, review_content1, review_content2]

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

        # 기존 데이터 아래에 결과를 추가합니다.
        for row in results:
            sheet.append_row(row)  # 각 결과를 새로운 행에 추가
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

# scrape_product_ids 함수 아래에 추가
def scrape_product_ids(keyword):
    product_ids = []
    try:
        with sync_playwright() as p:
            logging.info(f"[{keyword}] Playwright 브라우저 실행")
            browser = p.chromium.launch(headless=True, timeout=60000)
            context = browser.new_context(
                locale='ko-KR',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            url = f'https://www.aliexpress.com/wholesale?SearchText={keyword}&SortType=total_tranpro_desc'
            logging.info(f"[{keyword}] 페이지 열기: {url}")
            page.goto(url, timeout=60000, wait_until='domcontentloaded')
            logging.info(f"[{keyword}] 페이지 로딩 완료, 3초 대기")
            time.sleep(3)
            elements = dynamic_selector_search(page, keyword)  # 이 부분에서 호출
            if not elements:
                logging.error(f"[{keyword}] 유효한 셀렉터를 찾지 못했습니다.")
            else:
                for element in elements[:5]:
                    href = element.get_attribute('href')
                    if href:
                        if '/item/' in href:
                            product_id = href.split('/item/')[1].split('.')[0]
                        else:
                            product_id = href
                        product_ids.append(product_id)
                        logging.info(f"[{keyword}] 추출 상품 ID: {product_id}")
            browser.close()
    except Exception as e:
        logging.error(f"[{keyword}] 크롤링 도중 예외 발생: {e}")
        traceback.print_exc()
    return product_ids

def get_and_summarize_reviews(product_id):
    url = f"https://feedback.aliexpress.com/pc/searchEvaluation.do?productId={product_id}&lang=ko_KR&country=KR&page=1&pageSize=10&filter=5&sort=complex_default"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP 요청 오류 (상품 ID {product_id}): {e}")
        return "리뷰를 가져오는 데 실패했습니다.", "", ""

    # JSON 데이터 파싱
    try:
        data = response.json()
        reviews = data['data']['evaViewList']
        extracted_reviews = [review['buyerFeedback'] for review in reviews]

        # 리뷰 요약
        summary = summarize_reviews(extracted_reviews)
        
        # review_content1: 가장 중요한 카피라이팅
        review_content1 = summary.split('.')[0] if summary else ""  # 첫 문장을 카피라이팅으로 사용
        # review_content2: 나머지 요약 내용
        review_content2 = summary if summary else ""
        
        return summary, review_content1, review_content2
    except (ValueError, KeyError) as e:
        logging.error(f"데이터 파싱 오류 (상품 ID {product_id}): {e}")
        return "리뷰를 가져오는 데 실패했습니다.", "", ""

def summarize_reviews(reviews):
    if not reviews:
        return "리뷰가 없습니다."

    reviews_text = "\n".join(reviews)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"다음 리뷰들을 2-3줄로 간결하게 요약해 주세요:\n{reviews_text}"}
            ],
            timeout=30
        )
        summary = response['choices'][0]['message']['content']
        return summary
    except Exception as e:
        logging.error(f"GPT 요약 중 오류 발생: {e}")
        traceback.print_exc()
        return "요약 실패"



def main():
    logging.info("[START] 프로그램 시작")
    keywords = get_keywords_from_google_sheet()  # Google Sheets에서 키워드 가져오기
    if not keywords:
        logging.error("키워드가 없습니다. 프로그램 종료합니다.")
        return

    results = []
    today = datetime.today().strftime('%Y-%m-%d')
    
    for keyword in keywords:
        logging.info(f"[PROCESS] '{keyword}' 작업 시작")
        ids = scrape_product_ids(keyword)  # 제품 ID 크롤링
        if ids:
            for pid in ids:
                # 리뷰 크롤링 및 요약
                summary, review_content1, review_content2 = get_and_summarize_reviews(pid)
                results.append([today, keyword, pid, review_content1, review_content2])  # 결과에 요약 추가
        else:
            logging.warning(f"[{keyword}] 크롤링 결과 0개")
        
        logging.info(f"[{keyword}] 작업 종료, 2초 대기")
        time.sleep(2)  # 2초 대기

    if results:
        save_results_to_sheet(results)  # 결과를 Google Sheets에 저장
    else:
        logging.warning("최종 결과가 없습니다.")

    logging.info("[END] 프로그램 종료")

if __name__ == '__main__':
    main()  # main() 함수 호출
