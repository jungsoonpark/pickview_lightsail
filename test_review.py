from playwright.sync_api import sync_playwright

def get_reviews_with_playwright(product_id):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 로그인 페이지로 이동
        page.goto("https://www.aliexpress.com")
        # 로그인 과정 추가 (필요한 경우)

        # 리뷰 페이지로 이동
        url = f"https://feedback.aliexpress.com/pc/searchEvaluation.do?productId={product_id}&lang=ko_KR&country=KR&page=1&pageSize=10&filter=5&sort=complex_default"
        page.goto(url)

        # 리뷰 데이터 추출
        reviews = page.query_selector_all('selector-for-reviews')  # 적절한 셀렉터로 변경
        extracted_reviews = [review.inner_text() for review in reviews]
        print(extracted_reviews)
        browser.close()
        return extracted_reviews

# 사용 예시
product_id = "1005007171050895"
reviews = get_reviews_with_playwright(product_id)
print(reviews)
