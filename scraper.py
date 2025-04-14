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



def dynamic_selector_search(page, keyword, type='id'):
    # 상품 ID와 상품 제목을 위한 셀렉터를 분리
    if type == 'id':
        # 상품 ID를 추출할 셀렉터 리스트
        selectors = [
            'a[data-product-id]',  # 상품 링크에서 추출
            'div[data-spm="itemlist"] a[href*="/item/"]',  # 다른 형식의 상품 링크
            'a[href*="/item/"]'  # 일반적인 링크 패턴
        ]
    elif type == 'title':
        # 상품 제목을 추출할 셀렉터 리스트
        selectors = [
            'h1[data-pl="product-title"]',  # 상품 제목이 들어 있는 h1 태그
            'meta[property="og:title"]',    # meta 태그에서 og:title 추출
            'span.product-title',           # 상품 제목을 포함한 span 태그
            'div.item-title'                # 다른 대체 셀렉터
        ]
    
    # 셀렉터 검색 시도
    for selector in selectors:
        try:
            logging.info(f"[{keyword}] 셀렉터 시도: {selector}")
            page.wait_for_selector(selector, timeout=60000)  # 셀렉터를 찾을 때까지 최대 30초 대기
            elements = page.query_selector_all(selector)
            if elements:
                logging.info(f"[{keyword}] 셀렉터 '{selector}'로 {len(elements)}개 요소 발견")
                return elements
        except PlaywrightTimeoutError as te:
            logging.warning(f"[{keyword}] 셀렉터 '{selector}' 타임아웃: {te}")
        except Exception as e:
            logging.error(f"[{keyword}] 셀렉터 '{selector}' 오류: {e}")
    
    return []




def scrape_product_ids_and_titles(keyword):
    product_data = []  # (상품 ID, 상품 제목) 튜플을 저장할 리스트
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
            page.goto(url, timeout=60000, wait_until='domcontentloaded')  # 페이지가 로드될 때까지 대기
            logging.info(f"[{keyword}] 페이지 로딩 완료, 3초 대기")
            time.sleep(3)
            
            # 페이지가 완전히 로드될 때까지 기다림
            page.wait_for_load_state('load')  # 'load' 상태에서 기다림

            # 동적 셀렉터를 통해 상품 요소 찾기 (상품 ID 추출)
            product_elements = dynamic_selector_search(page, keyword, type='id')
            if not product_elements:
                logging.error(f"[{keyword}] 유효한 상품 ID 셀렉터를 찾지 못했습니다.")
            else:
                for element in product_elements[:5]:  # 상위 5개 상품을 처리
                    href = element.get_attribute('href')
                    if href:
                        if '/item/' in href:
                            product_id = href.split('/item/')[1].split('.')[0]  # 상품 ID 추출
                        else:
                            product_id = href
                        logging.info(f"[{keyword}] 추출 상품 ID: {product_id}")

            # 동적 셀렉터를 통해 상품 제목 찾기
            title_elements = dynamic_selector_search(page, keyword, type='title')
            if not title_elements:
                logging.error(f"[{keyword}] 유효한 상품 제목 셀렉터를 찾지 못했습니다.")
            else:
                for element in title_elements[:5]:  # 상위 5개 제목 처리
                    product_title = element.inner_text().strip()  # 상품 제목 추출
                    logging.info(f"[{keyword}] 추출 상품 제목: {product_title}")

                    # 상품 제목이 없으면 건너뛰고 다음 상품으로 진행
                    if not product_title:
                        logging.warning(f"[{keyword}] 상품 제목을 찾지 못했습니다: {href}")
                        continue
                    
                    product_data.append((product_id, product_title))  # (상품 ID, 상품 제목) 저장
                    logging.info(f"[{keyword}] 추출 상품 ID: {product_id}, 상품 제목: {product_title}")
            
            browser.close()
    except Exception as e:
        logging.error(f"[{keyword}] 크롤링 도중 예외 발생: {e}")
        traceback.print_exc()
    
    return product_data










# def dynamic_selector_search(page, keyword, type='id'):
#     # 상품 ID와 상품 제목을 위한 셀렉터를 분리
#     if type == 'id':
#         # 상품 ID를 추출할 셀렉터 리스트
#         selectors = [
#             'a[data-product-id]',  # 상품 링크에서 추출
#             'div[data-spm="itemlist"] a[href*="/item/"]',  # 다른 형식의 상품 링크
#             'a[href*="/item/"]'  # 일반적인 링크 패턴
#         ]
#     elif type == 'title':
#         # 상품 제목을 추출할 셀렉터 리스트
#         selectors = [
#             'span.product-title',  # 기본 상품 제목
#             'div.item-title',  # 대체 셀렉터 예시
#             'h1.product-title'  # 다른 대체 셀렉터
#         ]
    
#     # 셀렉터 검색 시도
#     for selector in selectors:
#         try:
#             logging.info(f"[{keyword}] 셀렉터 시도: {selector}")
#             page.wait_for_selector(selector, timeout=30000)  # 셀렉터를 찾을 때까지 최대 30초 대기
#             elements = page.query_selector_all(selector)
#             if elements:
#                 logging.info(f"[{keyword}] 셀렉터 '{selector}'로 {len(elements)}개 요소 발견")
#                 return elements
#         except PlaywrightTimeoutError as te:
#             logging.warning(f"[{keyword}] 셀렉터 '{selector}' 타임아웃: {te}")
#         except Exception as e:
#             logging.error(f"[{keyword}] 셀렉터 '{selector}' 오류: {e}")
    
#     return []




# def get_product_title(product_id):
#     url = f"https://www.aliexpress.com/item/{product_id}"
    
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
#         'Accept-Language': 'en-US,en;q=0.9',
#     }
    
#     response = requests.get(url, headers=headers)
#     if response.status_code != 200:
#         logging.error(f"상품 상세 페이지를 불러오는 데 실패했습니다. (상품 ID: {product_id})")
#         return 'No title'

#     soup = BeautifulSoup(response.text, 'html.parser')

#     # 상품 제목 추출 (헤더에 따라 다른 선택자 사용)
#     title = soup.find('h1', class_='product-title-text')
#     if title:
#         return title.text.strip()
    
#     return 'No title'





def get_and_summarize_reviews(product_id, extracted_reviews, reviews_needed=5, keyword=None):
    try:
        # 상품 제목 추출
        product_data = scrape_product_ids_and_titles(keyword)
        product_title = next((title for pid, title in product_data if pid == product_id), 'No title')
        logging.info(f"[{product_id}] 상품 제목: {product_title}")

        # 리뷰 크롤링 및 요약 처리
        url = f"https://feedback.aliexpress.com/pc/searchEvaluation.do?productId={product_id}&lang=ko_KR&country=KR&page=1&pageSize=10&filter=5&sort=complex_default"
        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            logging.error(f"[{product_id}] 리뷰 API 응답 실패")
            return None
        
        try:
            data = response.json()
        except ValueError:
            logging.error(f"[{product_id}] JSON 파싱 오류")
            return None
        
        reviews = data.get('data', {}).get('evaViewList', [])
        if not reviews:
            return None

        # 리뷰가 부족할 경우, 추가적인 상품을 계속해서 가져옴
        extracted_reviews += [review.get('buyerTranslationFeedback', '') for review in reviews if review.get('buyerTranslationFeedback')]
        
        if len(extracted_reviews) < reviews_needed:
            return None
        
        # 리뷰 요약
        result = summarize_reviews(extracted_reviews, product_title)
        if result is None:
            return None
        
        review_content1, review_content2 = result
        return review_content1, review_content2
    except Exception as e:
        logging.error(f"[{product_id}] 리뷰 크롤링 도중 예외 발생: {e}")
        traceback.print_exc()
        return None





def summarize_reviews(reviews, product_title):
    
    reviews_text = "\n".join(reviews)
    try:
        # review_content1: 10-15자 이내로 간결한 카피라이팅 문구 작성
        response1 = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user",
                    "content": f"다음 상품 제목과 리뷰를 바탕으로 이 상품의 가장 핵심적인 장점을 10-20자 이내로 간결하게 표현하는 카피라이팅 문구를 작성해 주세요. 리뷰 내용: {reviews_text}. 상품 제목: {product_title}"
                }
            ],
            timeout=30
        )
        
        review_content1 = response1['choices'][0]['message']['content'].strip()

        
        logging.info(f"상품 제목: {product_title}, 카피라이팅 문구: {review_content1}")

        
        # review_content2: 상품의 추가적인 긍정적인 특징을 15-40자 이내로 자연스럽게 작성
        response2 = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user", 
                    "content": f"다음 상품 제목과 리뷰를 바탕으로, '{review_content1}'에서 다루지 않은 추가적인 장점을 문장당 15-40자 이내의 1~2개 문장으로 작성해 주세요. 리뷰 내용: {reviews_text}. 상품 제목: {product_title}"
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
        ids = scrape_product_ids_and_titles(keyword)  # 제품 ID 크롤링
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
