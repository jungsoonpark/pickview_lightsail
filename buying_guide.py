import gspread
from google.oauth2.service_account import Credentials
import openai
import logging
from datetime import datetime
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
        sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
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

# GPT로 항목별 구매 가이드 생성 함수
def generate_section_guide(keyword, section):
    try:
        prompt = f"당신은 매우 경험이 풍부한 블로거입니다. 아래와 같은 정보들을 바탕으로 {keyword}에 대한 {section}을 작성해주세요.\n\n"

        if section == "제품 선택 포인트":
            prompt += "1. 제품 선택 포인트: 이 상품을 선택할 때 중요한 특징과 고려해야 할 사항을 300자 내외로 자세히 설명해 주세요."
        elif section == "구매 전 체크리스트":
            prompt += "2. 구매 전 체크리스트: 구매 전 확인해야 할 중요한 항목을 200자 내외로 설명해 주세요. 주요 확인 사항과 주의할 점을 강조해주세요."
        elif section == "자주 묻는 질문":
            prompt += "3. 자주 묻는 질문: 이 상품을 구매하기 전에 자주 묻는 질문에 대해 300자 내외로 답변해 주세요. 가장 일반적인 궁금증을 포함시켜 주세요."

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        guide = response['choices'][0]['message']['content']
        logging.info(f"{section} 응답 내용: {guide}")
        return guide.strip()
    except Exception as e:
        logging.error(f"{section} 생성 오류: {e}")
        return ""

# 구글 시트에 결과 저장하는 함수
def save_results_to_sheet(results):
    try:
        sheet = connect_to_google_sheet('list')  # 'list' 시트에서 키워드 옆 C, D, E열에 결과 입력
        for row in results:
            keyword = row[1]
            selection_points = row[2]
            checklist = row[3]
            faq = row[4]

            cell = sheet.find(keyword)  # 키워드 위치 찾기
            if cell:
                logging.info(f"Keyword '{keyword}' 찾기 시도")
                sheet.update_cell(cell.row, 3, selection_points)  # C열에 제품 선택 포인트 저장
                sheet.update_cell(cell.row, 4, checklist)  # D열에 구매 전 체크리스트 저장
                sheet.update_cell(cell.row, 5, faq)  # E열에 자주 묻는 질문 저장

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
        
        # 각 항목별로 GPT로 요청하고 결과 저장
        selection_points = generate_section_guide(keyword, "제품 선택 포인트")
        checklist = generate_section_guide(keyword, "구매 전 체크리스트")
        faq = generate_section_guide(keyword, "자주 묻는 질문")
        
        results.append([today, keyword, selection_points, checklist, faq])  # 각 항목의 결과 저장
    
    if results:
        save_results_to_sheet(results)  # 결과를 Google Sheets에 저장
    else:
        logging.warning("최종 결과가 없습니다.")

    logging.info("[END] 프로그램 종료")

# 프로그램 실행
if __name__ == '__main__':
    main()  # main() 함수 호출
