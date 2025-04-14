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
import os

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
        
        # 결과 추가
        for row in results:
            # 각 칼럼에 맞게 데이터를 추가
            sheet.append_row([row[0], row[1], row[2], row[3], row[4]])  # date, keyword, product_id, review_content1, review_content2
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
            page.wait_for_selector(selector, timeout=30000)
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



def dynamic_selector_search(page, keyword):
    selectors = [
        'a[data-product-id]',
        'div[data-spm="itemlist"] a[href*="/item/"]',
        'a[href*="/item/"]'
    ]
    for selector in selectors:
        try:
            logging.info(f"[{keyword}] 셀렉터 시도: {selector}")
            page.wait_for_selector(selector, timeout=60000)  # 타임아웃을 60초로 늘림
            elements = page.query_selector_all(selector)
            if elements:
                return elements
        except PlaywrightTimeoutError as te:
            logging.warning(f"[{keyword}] 셀렉터 '{selector}' 타임아웃: {te}")
        except Exception as e:
            logging.error(f"[{keyword}] 셀렉터 '{selector}' 오류: {e}")
    return []






def get_and_summarize_reviews(product_id, extracted_reviews, reviews_needed=5):
    url = f"https://feedback.aliexpress.com/pc/searchEvaluation.do?productId={product_id}&lang=ko_KR&country=KR&page=1&pageSize=10&filter=5&sort=complex_default"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP 요청 오류 (상품 ID {product_id}): {e}")
        return None  # 리뷰가 없으면 None 반환

    try:
        data = response.json()
        reviews = data.get('data', {}).get('evaViewList', [])
        if not reviews:  # 5점 리뷰가 없으면 해당 상품 제외
            return None

        # 5점 리뷰만 추출 (리스트가 비어 있으면 None 반환)
        extracted_reviews += [review.get('buyerTranslationFeedback', '') for review in reviews if review.get('buyerTranslationFeedback')]
        
        # 리뷰가 부족할 경우, 추가적인 상품을 계속해서 가져옴
        if len(extracted_reviews) < reviews_needed:
            return None  # 5개 미만인 경우, 다시 추가 상품을 가져오는 로직을 구현할 수 있음
        
        # 리뷰 요약
        result = summarize_reviews(extracted_reviews)
        
        # result가 None이면, 즉 요약 실패한 경우
        if result is None:
            return None
        
        review_content1, review_content2 = result
        
        return review_content1, review_content2
    except (ValueError, KeyError) as e:
        logging.error(f"데이터 파싱 오류 (상품 ID {product_id}): {e}")
        return None


def summarize_reviews(reviews):
    if not reviews:
        return "리뷰가 없습니다.", ""

    reviews_text = "\n".join(reviews)
    try:
        # review_content1: 10-15자 이내로 간결한 카피라이팅 문구 작성
        response1 = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user",
                    "content": f"다음 리뷰를 바탕으로 이 상품의 가장 핵심적인 장점을 10-15자 이내로 간결하게 표현하는 카피라이팅 문구를 작성해 주세요. 리뷰 내용: {reviews_text}"
                }
            ],
            timeout=30
        )
        
        review_content1 = response1['choices'][0]['message']['content'].strip()

        # review_content1 글자수 10-15자 이내로 자연스럽게 조정
        logging.info(f"review_content1: {review_content1}")

        
        # review_content2: 상품의 추가적인 긍정적인 특징을 15-40자 이내로 자연스럽게 작성
        response2 = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user", 
                    "content": f"다음 리뷰를 바탕으로, '{review_content1}'에서 다루지 않은 추가적인 긍정적인 특징을 문장당 15-40자 이내의 1~2개 문장으로 작성해 주세요. 리뷰 내용: {reviews_text}"
                }
            ],
            timeout=30
        )
        
        review_content2 = response2['choices'][0]['message']['content'].strip()

        # 5개 리뷰가 안 채워지면 다음 상품을 가져오는 로직 추가
        if len(review_content1) == 0 or len(review_content2) == 0:
            return None  # 리뷰 추출 또는 요약 실패시 None 반환

        return review_content1, review_content2
    except Exception as e:
        logging.error(f"GPT 요약 중 오류 발생: {e}")
        traceback.print_exc()
        return None  # 오류 발생 시 None 반환



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
        extracted_reviews = []
        product_count = 0
        
        for pid in ids[:10]:  # 최대 10개 상품을 처리
            if product_count >= 5:
                break
            # 리뷰 크롤링 및 요약
            result = get_and_summarize_reviews(pid, extracted_reviews)
            
            if result:
                review_content1, review_content2 = result
                results.append([today, keyword, pid, review_content1, review_content2])  # 결과에 요약 추가
                product_count += 1
            else:
                logging.warning(f"[{keyword}] 리뷰가 없는 상품 제외: {pid}")
        
        logging.info(f"[{keyword}] 작업 종료, 2초 대기")
        time.sleep(2)  # 2초 대기

    if results:
        save_results_to_sheet(results)  # 결과를 Google Sheets에 저장
    else:
        logging.warning("최종 결과가 없습니다.")

    logging.info("[END] 프로그램 종료")




if __name__ == '__main__':
    main()  # main() 함수 호출
