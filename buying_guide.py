import gspread
from google.oauth2.service_account import Credentials
import openai
import logging
import time
from datetime import datetime
import json
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
 



# 구글 시트 연결 함수
def connect_to_google_sheet(sheet_name):
    try:
        scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(JSON_KEY_PATH, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID.worksheet(READ_SHEET_NAME))
        logging.info(f'Google Sheet "{READ_SHEET_NAME}" 연결 성공')
        return sheet
    except Exception as e:
        logging.error(f"구글 시트 연결 실패: {e}")
        raise

# 구글 시트에서 키워드 가져오기
def get_keywords_from_google_sheet():
    try:
        sheet = connect_to_google_sheet('list')  # list 시트에서 키워드 가져오기
        data = sheet.get_all_records()
        today = datetime.today().strftime('%Y-%m-%d')
        keywords = [row['keyword'] for row in data if row.get('date') == today]
        logging.info(f"오늘 날짜({today}) 키워드 수집 완료: {keywords}")
        return keywords
    except Exception as e:
        logging.error(f"키워드 수집 실패: {e}")
        return []

# GPT를 통해 구매 가이드 생성
def generate_buying_guide(keyword):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"다음 키워드에 대해, 상품을 구매하는 데 알아야 할 정보를 3개의 주요 섹션으로 작성해주세요.\n\n1. 제품 선택 포인트: 상품 구매시 핵심 특징과 무엇을 고려해야 하는지 300자 내외로 설명해 주세요. \n2. 구매 전 체크리스트: 구매 전 확인해야 할 항목들을 200자 내외로 설명해주세요\n3. 자주 묻는 질문: 제품을 구매할 때 자주 묻는 질문에 대해 300자 내외로 답해주세요.\n\n키워드: {keyword}"}
            ],
            timeout=30
        )

        guide = response['choices'][0]['message']['content'].split("\n")  # 항목 구분을 위해 줄바꿈으로 나눔

        # 각 항목을 개별적으로 추출하고, 없으면 기본값을 설정
        selection_points = guide[0].split(':')[1].strip() if len(guide) > 0 and ':' in guide[0] else "이 상품의 핵심적인 장점을 고려하세요."
        checklist = guide[1].split(':')[1].strip() if len(guide) > 1 and ':' in guide[1] else "구매 전 체크리스트를 확인하세요."
        faq = guide[2].split(':')[1].strip() if len(guide) > 2 and ':' in guide[2] else "자주 묻는 질문을 확인하세요."

        # 더 풍성한 설명을 추가하기 위해 기본값 추가
        if "이 상품의 핵심적인 장점을 고려하세요." in selection_points:
            selection_points = "구매 시 핵심적으로 고려할 사항은 기능, 가격, 디자인입니다. 고객 리뷰도 참고해 주세요."
        
        if "구매 전 체크리스트를 확인하세요." in checklist:
            checklist = "가격 비교를 하여 최적의 가격을 선택하고, 제품의 품질을 확인한 후 구매 결정을 내리세요."
        
        if "자주 묻는 질문을 확인하세요." in faq:
            faq = "제품의 내구성, 보증기간, 사용법에 대한 정보를 확인하세요."

        # HTML 형식으로 변환
        buying_guide_html = f"""
            <h2>{keyword} 구매 가이드</h2>
            <p><strong>1. 제품 선택 포인트</strong>: {selection_points}</p>
            <p><strong>2. 구매 전 체크리스트</strong>: {checklist}</p>
            <p><strong>3. 자주 묻는 질문</strong>: {faq}</p>
        """

        return buying_guide_html

    except Exception as e:
        logging.error(f"GPT 요청 중 오류 발생: {e}")
        return None


# 구글 시트에 결과 저장하는 함수
def save_results_to_sheet(results):
    try:
        sheet = connect_to_google_sheet('list')  # 'list' 시트에서 키워드 옆 C열에 결과 입력
        for row in results:
            keyword = row[1]
            buying_guide = row[2]
            cell = sheet.find(keyword)  # 키워드 위치 찾기
            if cell:
                sheet.update_cell(cell.row, cell.col + 2, buying_guide)  # C열에 구매 가이드 추가
        logging.info("구매 가이드 결과가 구글 시트에 성공적으로 저장되었습니다.")
    except Exception as e:
        logging.error(f"결과 저장 실패: {e}")


# 메인 함수
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
        
        # 구매 가이드 생성
        buying_guide_html = generate_buying_guide(keyword)
        if buying_guide_html:
            results.append([today, keyword, buying_guide_html])  # 결과에 HTML 형식으로 저장
        else:
            logging.warning(f"[{keyword}] 구매 가이드 생성 실패")
    
    if results:
        save_results_to_sheet(results)  # 결과를 Google Sheets에 저장
    else:
        logging.warning("최종 결과가 없습니다.")

    logging.info("[END] 프로그램 종료")


# 프로그램 실행
if __name__ == '__main__':
    main()  # main() 함수 호출
