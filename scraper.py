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




# def save_results_to_sheet(results):
#     try:
#         sheet = connect_to_google_sheet(RESULT_SHEET_NAME)
        
#         # 결과 추가
#         for row in results:
#             # 각 칼럼에 맞게 데이터를 추가
#             sheet.append_row([row[0], row[1], row[2], row[3], row[4]])  # date, keyword, product_id, review_content1, review_content2
#         logging.info(f"구글 시트에 결과 저장 완료: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
#     except Exception as e:
#         logging.error(f"결과 저장 실패: {e}")
#         traceback.print_exc()

def save_results_to_sheet(results):
    try:
        if not results:
            logging.warning("저장할 결과가 없습니다.")
            return
        sheet = connect_to_google_sheet(RESULT_SHEET_NAME)
        for row in results:
            sheet.append_row([row[0], row[1], row[2], row[3], row[4]])  # date, keyword, product_id, review_content1, review_content2
        logging.info(f"구글 시트에 결과 저장 완료: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    except Exception as e:
        logging.error(f"결과 저장 실패: {e}")
        traceback.print_exc()





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
                # logging.warning(f"[{keyword}] 상품 요소가 없습니다. 건너뜁니다.")
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

                    # logging.info(f"[{keyword}] 상품 ID 추출: {product_id}")

                    # 상품 제목 추출
                    product_title = element.inner_text().strip().split('\n')[0]  # 상품 제목만 추출 (가격 등 정보는 제외)

                    # 제목이 없는 경우 건너뛰기
                    if not product_title:
                        # logging.warning(f"[{keyword}] 상품 제목을 찾을 수 없습니다: {href}")
                        continue  # 상품 제목이 없는 경우 건너뛰기
                    
                    # 추출된 상품 ID와 제목을 튜플로 저장
                    product_data.append((product_id, product_title))
                    logging.info(f"[{keyword}] 상품 ID: {product_id}, 제목: {product_title}")

            browser.close()
    except Exception as e:
        logging.error(f"[{keyword}] 크롤링 도중 예외 발생: {e}")
        traceback.print_exc()

    return product_data








# def get_and_summarize_reviews(product_id, extracted_reviews, reviews_needed=5, keyword=None):
#     try:
#         # 상품 제목 추출
#         product_data = scrape_product_ids_and_titles(keyword)
#         product_title = next((title for pid, title in product_data if pid == product_id), 'No title')
#         # logging.info(f"[{product_id}] 상품 제목: {product_title}")

#         # 리뷰 크롤링 및 요약 처리
#         url = f"https://feedback.aliexpress.com/pc/searchEvaluation.do?productId={product_id}&lang=ko_KR&country=KR&page=1&pageSize=10&filter=5&sort=complex_default"
#         headers = {"User-Agent": "Mozilla/5.0"}

#         response = requests.get(url, headers=headers, timeout=30)
#         if response.status_code != 200:
#             logging.error(f"[{product_id}] 리뷰 API 요청 실패, 상태 코드: {response.status_code}, 내용: {response.text}")
#             return None
        
#         try:
#             data = response.json()
#         except ValueError:
#             logging.error(f"[{product_id}] JSON 파싱 오류")
#             return None
        
#         reviews = data.get('data', {}).get('evaViewList', [])
#         if not reviews:
#             return None

#         # 리뷰가 부족할 경우, 추가적인 상품을 계속해서 가져옴
#         extracted_reviews += [review.get('buyerTranslationFeedback', '') for review in reviews if review.get('buyerTranslationFeedback')]


#         # 중간 로깅: 리뷰 수집 완료 후 출력
#         logging.info(f"[{product_id}] 리뷰 수집 완료: {len(extracted_reviews)}개")

        
#         if len(extracted_reviews) < reviews_needed:
#             return None
        
#         # 리뷰 요약
#         result = summarize_reviews(extracted_reviews, product_title)
#         if result is None:
#             return None
        
#         review_content1, review_content2 = result
#         return review_content1, review_content2
#     except Exception as e:
#         logging.error(f"[{product_id}] 리뷰 크롤링 도중 예외 발생: {e}")
#         traceback.print_exc()
#         return None



import requests
import logging
import traceback

def get_and_summarize_reviews(product_id, extracted_reviews, reviews_needed=5, keyword=None):
    try:
        # 상품 제목 추출
        product_data = scrape_product_ids_and_titles(keyword)
        product_title = next((title for pid, title in product_data if pid == product_id), 'No title')
        logging.info(f"[{product_id}] 상품 제목: {product_title}")

        # 리뷰 크롤링 처리
        url = f"https://feedback.aliexpress.com/pc/searchEvaluation.do?productId={product_id}&lang=ko_KR&country=KR&page=1&pageSize=10&filter=5&sort=complex_default"
        headers = {"User-Agent": "Mozilla/5.0"}

        # 요청 보내기
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logging.error(f"[{product_id}] 리뷰 페이지 요청 실패, 상태 코드: {response.status_code}")
            return None

        # 페이지 파싱
        try:
            data = response.json()  # JSON 파싱
        except ValueError:
            logging.error(f"[{product_id}] JSON 파싱 오류, 응답: {response.text}")
            return None

        # 리뷰 추출
        reviews = []
        review_elements = data.get('data', {}).get('evaViewList', [])
        
        # 리뷰가 있는 경우만 추출
        for review_element in review_elements:
            review_text = review_element.get('buyerTranslationFeedback', '')  # 리뷰 추출
            if review_text:
                reviews.append(review_text)

        if len(reviews) == 0:
            logging.warning(f"[{product_id}] 리뷰가 없습니다.")
            return None
        
        # 리뷰가 부족할 경우, 추가적인 상품을 계속해서 가져옴
        extracted_reviews += reviews
        logging.info(f"[{product_id}] 리뷰 수집 완료: {len(extracted_reviews)}개")

        if len(extracted_reviews) < reviews_needed:
            logging.info(f"[{product_id}] 리뷰가 부족합니다. 더 많은 리뷰를 수집합니다.")
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









# def main():
#     logging.info("[START] 프로그램 시작")
#     keywords = get_keywords_from_google_sheet()  # Google Sheets에서 키워드 가져오기
#     if not keywords:
#         logging.error("키워드가 없습니다. 프로그램 종료합니다.")
#         return

#     results = []
#     today = datetime.today().strftime('%Y-%m-%d')
    
#     for keyword in keywords:
#         logging.info(f"[PROCESS] '{keyword}' 작업 시작")
#         ids = scrape_product_ids_and_titles(keyword)  # 제품 ID 크롤링
#         extracted_reviews = []
#         product_count = 0
        
#         for pid in ids[:10]:  # 최대 10개 상품을 처리
#             if product_count >= 5:
#                 break
#             # 리뷰 크롤링 및 요약
#             result = get_and_summarize_reviews(pid, extracted_reviews)
            
#             if result:
#                 review_content1, review_content2 = result
#                 results.append([today, keyword, pid, review_content1, review_content2])  # 결과에 요약 추가
#                 product_count += 1
#             else:
#                 logging.warning(f"[{keyword}] 리뷰가 없는 상품 제외: {pid}")
        
#         logging.info(f"[{keyword}] 작업 종료, 2초 대기")
#         time.sleep(2)  # 2초 대기

#     if results:
#         save_results_to_sheet(results)  # 결과를 Google Sheets에 저장
#     else:
#         logging.warning("최종 결과가 없습니다.")

#     logging.info("[END] 프로그램 종료")


def main():
    logging.info("[START] 프로그램 시작")
    keywords = get_keywords_from_google_sheet()  # Google Sheets에서 키워드 가져오기
    if not keywords:
        logging.error("키워드가 없습니다. 프로그램 종료합니다.")
        return

    results = []
    today = datetime.today().strftime('%Y-%m-%d')
    
    for keyword in keywords:
        if not keyword:  # 키워드가 None이나 빈 값일 경우 건너뛰기
            logging.warning("빈 키워드 발견, 건너뜁니다.")
            continue
        
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
