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


# def generate_review_content2(reviews_text):
#     try:
#         # `reviews_text`를 바탕으로 간결한 리뷰 설명 생성
#         response = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "user", "content": f"당신은 한국 최고의 마케터입니다. 다음 리뷰 내용을 바탕으로 긍정적인 특징을 1~2문구로 간단히 설명해 주세요. 각 문장은 15~30자 이내로 작성해 주세요:\n{reviews_text}"}
#             ],
#             timeout=30
#         )
#         return response['choices'][0]['message']['content'].strip()
#     except Exception as e:
#         logging.error(f"generate_review_content2 함수에서 오류 발생: {e}")
#         traceback.print_exc()
#         return "요약 실패"




def filter_reviews_by_language(reviews):
    korean_reviews = []
    for review in reviews:
        if is_korean(review):  # is_korean 함수를 사용하여 한국어인지 확인
            korean_reviews.append(review)
    return korean_reviews

def is_korean(text):
    return any([ord(c) > 127 for c in text])  # 텍스트에서 한글이 포함되어 있는지 확인




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
        extracted_reviews += [review.get('buyerFeedback', '') for review in reviews if review.get('buyerFeedback')]
        
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
        # review_content1: 10-15자 이내로 자연스럽고 강렬한 카피라이팅 문장 작성
        response1 = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user", 
                     "content": f"당신은 한국 최고의 마케터입니다. 상품의 핵심적인 특징을 10-15자 이내의 문구로 작성해 주세요. 리뷰 내용은 {reviews_text}입니다."
                }
            ],
            timeout=30
        )
        
        review_content1 = response1['choices'][0]['message']['content'].strip()

        # review_content1 글자수 10-15자 이내로 조정 (자르는 부분 제거)
        if len(review_content1) < 10 or len(review_content1) > 15:
            # 글자 수가 10-15자 범위에 맞지 않으면 GPT에서 다시 수정하도록 유도하는 방법이 필요함
            logging.warning(f"review_content1의 길이가 10-15자 범위 밖입니다: {review_content1}")

        # review_content2: 영어가 섞이지 않도록 한국어로만 처리하고, 긍정적인 특징을 자연스럽게 15-30자 이내로 작성
        response2 = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user", 
                    "content": f"당신은 한국 최고의 마케터입니다. 이 상품에 대한 리뷰에서 {review_content1}의 내용에서 다루지 않은 긍정적인 특징을 15-40자 이내로 간결한 문장으로 작성해주세요. 리뷰는 한국어로만 작성되어야 하며, 영어는 포함되지 않도록 해주세요.:\n{reviews_text}"
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
        return "요약 실패", "요약 실패"








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
