import os
import requests
import hashlib
import hmac
import json
import logging
import traceback
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

# OpenAI 사용 시 (필요하면)
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")  # GitHub Secrets로 관리

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s', 
                    datefmt='%Y-%m-%d %H:%M:%S')

# 구글 시트 설정
SHEET_ID = "1Ew7u6N72VP3nVvgNiLKZDyIpHg4xXz-prkyV4SW7EkI"
JSON_KEY_PATH = '/home/ubuntu/pickview-be786ad8e194.json'  # Lightsail 서버 내 JSON 키 파일 경로
READ_SHEET_NAME = 'list'       # 시트: [date, keyword]
RESULT_SHEET_NAME = 'result'   # 시트: [date, keyword, product_id, product_title, target_sale_price, affiliate_link]

# API 호출에 사용할 AliExpress Affiliate API 파라미터 (환경 변수로 Secrets 관리)
# ALIEXPRESS_ACCESS_TOKEN, ALIEXPRESS_API_KEY, ALIEXPRESS_API_SECRET 등

# --- 서명 생성 함수 ---
def generate_signature(params, app_secret):
    sorted_params = sorted(params.items())
    canonicalized_query_string = ''
    for k, v in sorted_params:
        canonicalized_query_string += f"{k}{v}"
    sign = hmac.new(app_secret.encode('utf-8'),
                    canonicalized_query_string.encode('utf-8'),
                    hashlib.sha256).hexdigest().upper()
    return sign

# --- Google Sheet 관련 함수 ---
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

def get_today_keywords():
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

def get_existing_product_ids(keyword):
    try:
        sheet = connect_to_google_sheet(RESULT_SHEET_NAME)
        records = sheet.get_all_records()
        today = datetime.today().strftime('%Y-%m-%d')
        # 결과 시트에 오늘 날짜와 해당 키워드에 대해 저장된 product_id 목록 추출
        product_ids = [str(row["product_id"]) for row in records 
                       if str(row.get("date", '')) == today and row.get("keyword", "").strip() == keyword and row.get("product_id")]
        logging.info(f"[{keyword}] 구글 시트에 이미 저장된 상품 ID 수: {len(product_ids)}")
        return product_ids
    except Exception as e:
        logging.error(f"[{keyword}] 기존 상품 ID 가져오기 실패: {e}")
        traceback.print_exc()
        return []

def save_results_to_sheet(results):
    try:
        sheet = connect_to_google_sheet(RESULT_SHEET_NAME)
        sheet.clear()
        sheet.append_row(['date', 'keyword', 'product_id', 'product_title', 'target_sale_price', 'affiliate_link'])
        for row in results:
            sheet.append_row(row)
        logging.info(f"구글 시트에 결과 저장 완료: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    except Exception as e:
        logging.error(f"결과 저장 실패: {e}")
        traceback.print_exc()

# --- AliExpress Affiliate API 함수 --- 
def get_product_detail_api(product_id):
    params = {
        "access_token": os.getenv("ALIEXPRESS_ACCESS_TOKEN"),
        "app_key": os.getenv("ALIEXPRESS_API_KEY"),
        "product_id": product_id,
        "countryCode": "KR",
        "currency": "KRW",
        "fields": "product_id,product_title,target_sale_price,product_main_image_url,detail_url",
        "local": "ko_KR",
        "method": "aliexpress.affiliate.productdetail.get",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "sign_method": "hmac-sha256"
    }
    params["sign"] = generate_signature(params, os.getenv("ALIEXPRESS_API_SECRET"))
    logging.info(f"[{product_id}] 요청 파라미터 (productdetail): {json.dumps(params, indent=2, ensure_ascii=False)}")
    response = requests.get("https://api-sg.aliexpress.com/sync", params=params)
    logging.info(f"[{product_id}] productdetail 응답 코드: {response.status_code}")
    response.raise_for_status()
    data = response.json()
    detail = data.get("aliexpress_affiliate_productdetail_get_response", {}).get("result", {})
    logging.info(f"[{product_id}] 상품 상세 정보: {json.dumps(detail, indent=2, ensure_ascii=False)}")
    return detail

def generate_affiliate_link_api(product_id):
    params = {
        "access_token": os.getenv("ALIEXPRESS_ACCESS_TOKEN"),
        "app_key": os.getenv("ALIEXPRESS_API_KEY"),
        "product_id": product_id,
        "local": "ko_KR",
        "method": "aliexpress.affiliate.link.generate",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "sign_method": "hmac-sha256"
    }
    params["sign"] = generate_signature(params, os.getenv("ALIEXPRESS_API_SECRET"))
    logging.info(f"[{product_id}] 요청 파라미터 (link.generate): {json.dumps(params, indent=2, ensure_ascii=False)}")
    response = requests.get("https://api-sg.aliexpress.com/sync", params=params)
    logging.info(f"[{product_id}] link.generate 응답 코드: {response.status_code}")
    response.raise_for_status()
    data = response.json()
    link = data.get("aliexpress_affiliate_link_generate_response", {}).get("result", {})
    logging.info(f"[{product_id}] 제휴 링크 정보: {json.dumps(link, indent=2, ensure_ascii=False)}")
    return link

# --- Main orchestration ---
def main():
    logging.info("[START] 프로그램 시작")
    keywords = get_today_keywords()
    if not keywords:
        logging.error("오늘 날짜의 키워드가 없습니다. 프로그램 종료.")
        return
    results = []
    today = datetime.today().strftime('%Y-%m-%d')
    for keyword in keywords:
        logging.info(f"[PROCESS] '{keyword}' 작업 시작")
        existing_ids = get_existing_product_ids(keyword)
        # 여기서는 기존에 저장된 상품 ID가 없을 경우에만 진행합니다.
        if not existing_ids:
            # 만약 API를 통해 상품 검색 기능이 별도로 필요하면 추가 작성합니다.
            # 예를 들어, 여기에 상위 5개의 상품 ID를 조회하는 API 호출 함수를 구현하거나,
            # 기존에 검색된 ID를 사용할 수 있으면 그대로 진행
            # 여기서는 임의의 상품 ID를 예시로 진행합니다.
            # 실제 구현 시에는 추가적인 검색 API 함수를 만들어야 합니다.
            logging.info(f"[{keyword}] 기존 결과 없음, 임의의 상품 ID 사용 (예시)")
            # 예시: 기존에 여러분이 테스트한 상품 ID, 실제 구현 시 대체 필요
            pids = ["1005008742459910", "1005005120738913", "1005006955548562", "1005006388837801", "1005005967496979"]
        else:
            pids = existing_ids[:5]
            logging.info(f"[{keyword}] 기존 상품 ID 사용: {pids}")
        
        for pid in pids:
            try:
                detail = get_product_detail_api(pid)
                affiliate_link = generate_affiliate_link_api(pid)
                # 최종 결과에 날짜, 키워드, 상품ID, 제품명, 판매가, 제휴 링크 저장
                product_title = detail.get("product_title", "")
                target_sale_price = detail.get("target_sale_price", "")
                results.append([today, keyword, pid, product_title, target_sale_price, affiliate_link.get("promotion_link", "")])
            except Exception as e:
                logging.error(f"[{pid}] 상품 정보 처리 중 오류 발생: {e}")
                traceback.print_exc()
        logging.info(f"[{keyword}] 작업 종료, 2초 대기")
        time.sleep(2)
    if results:
        save_results_to_sheet(results)
    else:
        logging.warning("최종 결과가 없습니다.")
    logging.info("[END] 프로그램 종료")

if __name__ == '__main__':
    main()
