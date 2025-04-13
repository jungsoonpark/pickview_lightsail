def generate_buying_guide(keyword):
    try:
        # GPT에게 구매 가이드를 요청
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user", 
                    "content": f"다음 키워드에 대해, 상품을 구매하는 데 알아야 할 정보를 3개의 주요 섹션으로 작성해주세요.\n\n"
                               "1. 제품 선택 포인트: 상품 구매시 핵심적인 특징을 300자 내외로 설명해 주세요. "
                               "구체적인 제품의 장점, 사용 용도에 맞는 선택 포인트를 명확히 제시해 주세요.\n"
                               "2. 구매 전 체크리스트: 구매 전 확인해야 할 항목들을 200자 내외로 설명해주세요. "
                               "제품을 선택할 때의 체크리스트를 제공해주세요.\n"
                               "3. 자주 묻는 질문: 제품을 구매할 때 자주 묻는 질문과 답변을 300자 내외로 작성해주세요.\n"
                               "글은 블로그 스타일로, **친근하고 쉽게 이해할 수 있는 말투**로 **전문적으로** 작성해 주세요. 마치 독자에게 직접 이야기하는 느낌으로 작성해주세요. 고객들이 궁금해할만한 사항도 함께 작성해 주세요.\n"
                               f"키워드: {keyword}"
                }
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





