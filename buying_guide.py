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


def connect_to_google_sheet(sheet_name):
    try:
        scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(JSON_KEY_PATH, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
        return sheet
    except Exception as e:
        logging.error(f"구글 시트 연결 실패: {e}")
        raise

def get_keywords_from_google_sheet():
    try:
        sheet = connect_to_google_sheet(READ_SHEET_NAME)
        data = sheet.get_all_records()
        today = datetime.today().strftime('%Y-%m-%d')
        keywords = [row['keyword'] for row in data if str(row.get('date', '')) == today]
        return keywords
    except Exception as e:
        logging.error(f"키워드 수집 실패: {e}")
        return []


def generate_buying_guide(keyword):
    try:
        # GPT로 구매 가이드 생성
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"다음 키워드에 대해 3개의 섹션으로 된 구매 가이드를 작성해주세요.\n\n1. 제품 선택 포인트\n2. 구매 전 체크리스트\n3. 자주 묻는 질문\n\n키워드: {keyword}"}
            ],
            timeout=30
        )
        
        guide = response['choices'][0]['message']['content'].strip().split('\n')

        # '1. 제품 선택 포인트'와 같은 제목으로 구분하고, 적절한 데이터 분리
        selection_points = ""
        checklist = ""
        faq = ""

        if len(guide) > 0:
            selection_points = guide[0].split(':')[1].strip() if len(guide[0].split(':')) > 1 else "선택 포인트 정보 없음"
        if len(guide) > 1:
            checklist = guide[1].split(':')[1].strip() if len(guide[1].split(':')) > 1 else "체크리스트 정보 없음"
        if len(guide) > 2:
            faq = guide[2].split(':')[1].strip() if len(guide[2].split(':')) > 1 else "FAQ 정보 없음"
        
        # 구매 가이드가 정상적으로 생성되었다면 딕셔너리 형태로 반환
        return {
            "selection_points": selection_points,
            "checklist": checklist,
            "faq": faq
        }

    except Exception as e:
        logging.error(f"GPT 요청 중 오류 발생: {e}")
        return None

def save_results_to_sheet(results):
    try:
        sheet = connect_to_google_sheet(READ_SHEET_NAME)  # 'list' 시트에 저장
        for row in results:
            keyword = row[1]  # 키워드
            buying_guide = row[2]  # 구매 가이드
            
            # HTML 형식으로 변환
            html_content = f"""
            <h2>{keyword} 구매 가이드</h2>
            <p><strong>1. 제품 선택 포인트</strong>: {buying_guide['selection_points']}</p>
            <p><strong>2. 구매 전 체크리스트</strong>: {buying_guide['checklist']}</p>
            <p><strong>3. 자주 묻는 질문</strong>: {buying_guide['faq']}</p>
            """
            
            # 'list' 시트의 C열에 HTML 저장
            sheet.update_cell(row_num, 3, html_content)  # row_num을 해당 행 번호로 설정

        logging.info(f"결과 저장 완료")
    except Exception as e:
        logging.error(f"결과 저장 실패: {e}")




def main():
    logging.info("[START] 프로그램 시작")
    keywords = get_keywords_from_google_sheet()  # Google Sheets에서 키워드 가져오기
    if not keywords:
        logging.error("오늘 날짜 키워드가 없습니다. 프로그램 종료합니다.")
        return

    results = []
    today = datetime.today().strftime('%Y-%m-%d')
    
    for keyword in keywords:
        logging.info(f"[PROCESS] '{keyword}' 키워드로 구매 가이드 작성")
        guide = generate_buying_guide(keyword)
        
        if guide:
            # 결과를 저장
            results.append([today, keyword, guide])
        else:
            logging.warning(f"[{keyword}] 구매 가이드 생성 실패")
        
        # 2초 대기
        time.sleep(2)

    if results:
        save_results_to_sheet(results)  # 결과를 Google Sheets에 저장
    else:
        logging.warning("최종 결과가 없습니다.")
    
    logging.info("[END] 프로그램 종료")

if __name__ == '__main__':
    main()  # main() 함수 호출
