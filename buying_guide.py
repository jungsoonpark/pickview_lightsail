import gspread
from google.oauth2.service_account import Credentials
import openai
import logging
import time
from datetime import datetime
import json
import os
import re
 
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
        sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)  # 수정된 부분
        logging.info(f'Google Sheet "{sheet_name}" 연결 성공')
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

# GPT 응답 처리 함수
def process_gpt_response(guide):
    # 응답을 기준으로 각 항목을 추출
    selection_points = ""
    checklist = ""
    faq = ""
    
    # 응답 내용이 예상대로 나누어졌는지 확인
    logging.info(f"GPT 응답 내용: {guide}")
    
    # 1. 제품 선택 포인트 추출
    selection_points_match = re.search(r'1\.\s*제품 선택 포인트\s*[:\s]*(.*?)(?=\n\s*2\.|$)', guide, re.DOTALL)
    if selection_points_match:
        selection_points = selection_points_match.group(1).strip()
    
    # 2. 구매 전 체크리스트 추출
    checklist_match = re.search(r'2\.\s*구매 전 체크리스트\s*[:\s]*(.*?)(?=\n\s*3\.|$)', guide, re.DOTALL)
    if checklist_match:
        checklist = checklist_match.group(1).strip()
    
    # 3. 자주 묻는 질문 추출
    faq_match = re.search(r'3\.\s*자주 묻는 질문\s*[:\s]*(.*)', guide, re.DOTALL)
    if faq_match:
        faq = faq_match.group(1).strip()

    # 디버깅 로그 추가
    logging.info(f"선택 포인트: {selection_points}")
    logging.info(f"구매 전 체크리스트: {checklist}")
    logging.info(f"자주 묻는 질문: {faq}")

    # 기본값 처리 (만약 응답이 없다면)
    selection_points = selection_points if selection_points else "선택 포인트 정보를 확인하세요."
    checklist = checklist if checklist else "체크리스트 정보를 확인하세요."
    faq = faq if faq else "자주 묻는 질문을 확인하세요."

    return selection_points, checklist, faq


# GPT 응답을 받아 HTML 템플릿 생성 함수
def generate_buying_guide(keyword, guide):
    # 응답을 처리하여 각 항목을 추출
    selection_points, checklist, faq = process_gpt_response(guide)
    
    # 결과 HTML 템플릿 구성
    buying_guide = f"""
        <h2>{keyword} 구매 가이드</h2>
        <p><strong>1. 제품 선택 포인트</strong>: {selection_points}</p>
        <p><strong>2. 구매 전 체크리스트</strong>: {checklist}</p>
        <p><strong>3. 자주 묻는 질문</strong>: {faq}</p>
    """

    # 결과를 반환
    return buying_guide

# 구글 시트에 결과 저장하는 함수
def save_results_to_sheet(results):
    try:
        sheet = connect_to_google_sheet('list')  # 'list' 시트에서 키워드 옆 C열에 결과 입력
        for row in results:
            keyword = row[1]
            buying_guide = row[2]
            cell = sheet.find(keyword)  # 키워드 위치 찾기

            logging.info(f"Keyword '{keyword}' 찾기 시도") # 찾은 셀의 상태 로깅
            if cell:
                logging.info(f"Found keyword '{keyword}' at row {cell.row}, col {cell.col}")
                logging.info(f"Updating cell with buying guide: {buying_guide}")
                sheet.update_cell(cell.row, cell.col + 1, buying_guide)  # C열에 구매 가이드 추가
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
        buying_guide_html = generate_buying_guide(keyword, "여기에 GPT 응답 문자열을 넣어주세요.")
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
