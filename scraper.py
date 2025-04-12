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
JSON_KEY = "pickview-be786ad8e194.json"
READ_SHEET_NAME = 'list'      # 구글 시트에서 날짜, 키워드가 있는 시트; 열: [date, keyword]
RESULT_SHEET_NAME = 'result'  # 결과 저장 시트; 열: [date, keyword, product_id, review_content1, review_content2]

# OpenAI API 키 설정
openai.api_key = 'YOUR_OPENAI_API_KEY'  # 여기에 OpenAI API 키를 입력하세요.

def connect_to_google_sheet(sheet_name):
    logging.info("Google Sheet 연결 시도...")
    try:
        scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(JSON_KEY, scopes=scopes)
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
        sheet.clear()
        # 헤더 추가
        sheet.append_row(['date', 'keyword', 'product_id', 'review_content1', 'review_content2'])
        for row in results:
            sheet.append_row(row)
        logging.info(f"구글 시트에 결과 저장 완료: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    except Exception as e:
        logging.error(f"결과 저장 실패: {e}")
        traceback.print_exc()

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
            elements = dynamic_selector_search(page, keyword)
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

def get_reviews(product_id):
    url = f"https://ko.aliexpress.com/item/{product_id}.html?reviews#nav-review"
    response = requests.get(url)

    if response.status_code != 200:
        logging.error(f"Error fetching reviews for product ID {product_id}: {response.status_code}")
        return []

    reviews = []
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        review_elements = soup.find_all('div', class_='feedback-item')

        for review in review_elements:
            review_text = review.find('p', class_='feedback-text').get_text(strip=True)
            reviews.append(review_text)
            logging.info(f"추출된 리뷰: {review_text}")

    except Exception as e:
        logging.error(f"리뷰 추출 중 오류 발생: {e}")
        traceback.print_exc()

    return reviews

def summarize_reviews(reviews):
    if not reviews:
        return "리뷰가 없습니다.", ""

    reviews_text = "\n".join(reviews)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": f"다음 리뷰를 요약해 주세요:\n{reviews_text}"}
        ]
    )

    summary = response['choices'][0]['message']['content']
    return summary, reviews_text.split('\n')[0]  # 첫 문장과 요약 반환

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
                reviews = get_reviews(pid)  # 리뷰 크롤링
                review_content1, review_content2 = summarize_reviews(reviews)  # 리뷰 요약
                results.append([today, keyword, pid, review_content1, review_content2])  # 결과에 요약 추가
        else:
            logging.warning(f"[{keyword}] 크롤링 결과 0개")
        logging.info(f"[{keyword}] 작업 종료, 2초 대기")
        time.sleep(2)
    if results:
        save_results_to_sheet(results)
    else:
        logging.warning("최종 결과가 없습니다.")
    logging.info
