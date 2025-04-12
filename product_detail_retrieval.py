import os
import requests
import hashlib
import hmac
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import logging
import traceback


# 로깅 설정
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 구글 시트 설정
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")  # GitHub Secrets에서 가져오기
JSON_KEY = os.getenv("GOOGLE_JSON_KEY")  # GitHub Secrets에서 가져오기
READ_SHEET_NAME = 'list'  # 키워드가 있는 시트; 열: [date, keyword]
creds = Credentials.from_service_account_info(json.loads(os.getenv("GOOGLE_JSON_KEY")), scopes=scopes)

def connect_to_google_sheet(sheet_name):
    logging.info("Google Sheet 연결 시도...")
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_info(json.loads(JSON_KEY), scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
        logging.info(f'Google Sheet "{sheet_name}" 연결 성공')
        return sheet
    except Exception as e:
        logging.error(f"구글 시트 연결 실패: {e}")
        traceback.print_exc()
        raise

def get_product_ids_from_google_sheet():
    try:
        sheet = connect_to_google_sheet(READ_SHEET_NAME)
        data = sheet.get_all_records()
        today = datetime.today().strftime('%Y-%m-%d')
        product_ids = [row['product_id'] for row in data if str(row.get('date', '')) == today]
        logging.info(f"오늘 날짜({today}) 상품 ID 수집 완료: {product_ids}")
        return product_ids
    except Exception as e:
        logging.error(f"상품 ID 수집 실패: {e}")
        traceback.print_exc()
        return []

# 서명 생성 함수
def generate_signature(params, app_secret):
    sorted_params = sorted(params.items())
    canonicalized_query_string = ''.join(f"{k}{v}" for k, v in sorted_params)

    sign = hmac.new(
        app_secret.encode('utf-8'),
        canonicalized_query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()

    return sign

def fetch_product_details(keyword, limit=5):
    """AliExpress Affiliate API 상품 검색"""
    try:
        params = {
            "access_token": os.getenv("ALIEXPRESS_ACCESS_TOKEN"),
            "app_key": os.getenv("ALIEXPRESS_API_KEY"),
            "countryCode": "KR",
            "currency": "KRW",
            "fields": "product_id,product_title,target_sale_price,target_original_price,product_main_image_url,promotion_link,evaluate_rate,total_sales_volume",
            "keywords": keyword,
            "method": "aliexpress.affiliate.products.search",
            "page_no": 1,
            "page_size": limit,
            "sign_method": "hmac-sha256",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 서명 생성
        params['sign'] = generate_signature(params, os.getenv("ALIEXPRESS_API_SECRET"))

        response = requests.get("https://api.aliexpress.com/sync", params=params)
        response.raise_for_status()

        data = response.json()
        return data.get('result', {}).get('products', [])

    except Exception as e:
        print(f"[에러] 상품 검색 중 오류 발생: {str(e)}")
        return []

# 테스트
if __name__ == "__main__":
    product_ids = get_product_ids_from_google_sheet()
    print(product_ids)
