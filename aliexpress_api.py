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

import openai
openai.api_key = os.getenv("OPENAI_API_KEY")  # GitHub Secrets에서 주입

# GitHub Secrets로부터 환경 변수 설정
ALIEXPRESS_ACCESS_TOKEN = os.getenv("ALIEXPRESS_ACCESS_TOKEN")
ALIEXPRESS_API_KEY = os.getenv("ALIEXPRESS_API_KEY")
ALIEXPRESS_API_SECRET = os.getenv("ALIEXPRESS_API_SECRET")
SHEET_ID = os.getenv("SHEET_ID")
READ_SHEET_NAME = os.getenv("READ_SHEET_NAME", "list")
RESULT_SHEET_NAME = os.getenv("RESULT_SHEET_NAME", "result")
# GOOGLE_JSON_KEY에 서비스 계정 JSON 문자열을 직접 넣어두었음
# GitHub 시크릿에서 JSON 키 가져오기
GOOGLE_JSON_KEY = os.getenv('GOOGLE_JSON_KEY')

# 시크릿을 메모리에 로드
creds = Credentials.from_service_account_info(
    json.loads(GOOGLE_JSON_KEY),
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)



# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# -----------------------------------------
# Utility: 서명 생성 함수
# -----------------------------------------
def generate_signature(params, app_secret):
    sorted_params = sorted(params.items())
    canonicalized_query_string = ''.join(f"{k}{v}" for k, v in sorted_params)
    sign = hmac.new(
        app_secret.encode('utf-8'),
        canonicalized_query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()
    return sign

# -----------------------------------------
# Google Sheet 관련 함수 (GOOGLE_JSON_KEY 직접 사용)
# -----------------------------------------
def get_google_creds():
    try:
        scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        google_key_content = os.getenv("GOOGLE_JSON_KEY")
        if not google_key_content:
            raise ValueError("GOOGLE_JSON_KEY 환경 변수가 설정되어 있지 않습니다.")
        info = json.loads(google_key_content)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return creds
    except Exception as e:
        logging.error(f"Google Credentials 생성 실패: {e}")
        traceback.print_exc()
        raise

def connect_to_google_sheet(sheet_name):
    logging.info("Google Sheet 연결 시도...")
    try:
        creds = get_google_creds()
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
        logging.info(f'Google Sheet "{sheet_name}" 연결 성공')
        return sheet
    except Exception as e:
        logging.error(f"구글 시트 연결 실패: {e}")
        traceback.print_exc()
        raise

def get_product_rows_from_sheet():
    """RESULT 시트에서 오늘 날짜의 모든 행(상품 ID 포함)을 가져옵니다."""
    try:
        sheet = connect_to_google_sheet(RESULT_SHEET_NAME)
        records = sheet.get_all_records()
        today = datetime.today().strftime('%Y-%m-%d')
        rows = [record for record in records if str(record.get("date", "")) == today and record.get("product_id")]
        logging.info(f"오늘 날짜({today}) 구글 시트에서 {len(rows)}행의 상품 데이터 읽어옴")
        return rows
    except Exception as e:
        logging.error(f"구글 시트 데이터 가져오기 실패: {e}")
        traceback.print_exc()
        return []

def save_results_to_sheet(results):
    try:
        sheet = connect_to_google_sheet(RESULT_SHEET_NAME)
        sheet.clear()
        # 헤더 설정
        sheet.append_row(['date', 'keyword', 'product_id', 'product_info'])
        for row in results:
            sheet.append_row(row)
        logging.info(f"구글 시트에 결과 저장 완료: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    except Exception as e:
        logging.error(f"결과 저장 실패: {e}")
        traceback.print_exc()

# -----------------------------------------
# AliExpress Affiliate API 함수
# -----------------------------------------
def get_product_detail(product_id):
    params = {
        "access_token": ALIEXPRESS_ACCESS_TOKEN,
        "app_key": ALIEXPRESS_API_KEY,
        "product_id": product_id,
        "countryCode": "KR",
        "currency": "KRW",
        "fields": "product_id,product_title,target_sale_price,detail_url,evaluate_rate,total_sales_volume,product_main_image_url",
        "local": "ko_KR",
        "method": "aliexpress.affiliate.productdetail.get",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "sign_method": "hmac-sha256"
    }
    params["sign"] = generate_signature(params, ALIEXPRESS_API_SECRET)
    logging.info(f"[{product_id}] productdetail 요청 파라미터: {json.dumps(params, indent=2, ensure_ascii=False)}")
    response = requests.get("https://api-sg.aliexpress.com/sync", params=params)
    logging.info(f"[{product_id}] productdetail 응답 코드: {response.status_code}")
    response.raise_for_status()
    data = response.json()
    detail = data.get("aliexpress_affiliate_productdetail_get_response", {}).get("result", {})
    logging.info(f"[{product_id}] 제품 상세 데이터: {json.dumps(detail, indent=2, ensure_ascii=False)}")
    return detail

def generate_affiliate_link(product_id):
    params = {
        "access_token": ALIEXPRESS_ACCESS_TOKEN,
        "app_key": ALIEXPRESS_API_KEY,
        "product_id": product_id,
        "local": "ko_KR",
        "method": "aliexpress.affiliate.link.generate",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "sign_method": "hmac-sha256"
    }
    params["sign"] = generate_signature(params, ALIEXPRESS_API_SECRET)
    logging.info(f"[{product_id}] link.generate 요청 파라미터: {json.dumps(params, indent=2, ensure_ascii=False)}")
    response = requests.get("https://api-sg.aliexpress.com/sync", params=params)
    logging.info(f"[{product_id}] link.generate 응답 코드: {response.status_code}")
    response.raise_for_status()
    data = response.json()
    link_result = data.get("aliexpress_affiliate_link_generate_response", {}).get("result", {})
    logging.info(f"[{product_id}] 제휴 링크 데이터: {json.dumps(link_result, indent=2, ensure_ascii=False)}")
    return link_result

# -----------------------------------------
# Main orchestration
# -----------------------------------------
def main():
    logging.info("[START] 프로그램 시작")
    rows = get_product_rows_from_sheet()
    if not rows:
        logging.error("오늘 날짜의 제품 데이터가 구글 시트에 없습니다. 프로그램 종료.")
        return

    updated_results = []
    today = datetime.today().strftime('%Y-%m-%d')
    for record in rows:
        product_id = str(record.get("product_id"))
        keyword = record.get("keyword", "")
        try:
            detail = get_product_detail(product_id)
            affiliate_data = generate_affiliate_link(product_id)
            product_info = {
                "product_title": detail.get("product_title", ""),
                "target_sale_price": detail.get("target_sale_price", ""),
                "detail_url": detail.get("detail_url", ""),
                "evaluate_rate": detail.get("evaluate_rate", ""),
                "total_sales_volume": detail.get("total_sales_volume", ""),
                "product_main_image_url": detail.get("product_main_image_url", ""),
                "affiliate_link": affiliate_data.get("promotion_link", "")
            }
            product_info_json = json.dumps(product_info, ensure_ascii=False)
            updated_results.append([today, keyword, product_id, product_info_json])
            logging.info(f"[{product_id}] 최종 결과: {product_info_json}")
        except Exception as e:
            logging.error(f"[{product_id}] 처리 중 오류: {e}")
            traceback.print_exc()
    if updated_results:
        save_results_to_sheet(updated_results)
    else:
        logging.warning("최종 업데이트할 결과가 없습니다.")
    logging.info("[END] 프로그램 종료")

if __name__ == '__main__':
    main()
