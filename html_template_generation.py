# html_template_generation.py

def generate_html_post(product_info, review_summary, purchase_guide):
    html_content = f"""
    <html>
    <head>
        <title>{product_info['title']}</title>
    </head>
    <body>
        <h1>{product_info['title']}</h1>
        <p>가격: {product_info['price']}</p>
        <p>구매 링크: <a href="{product_info['affiliate_link']}">구매하기</a></p>
        
        <h2>리뷰 요약</h2>
        <p>{review_summary}</p>
        
        <h2>구매 가이드</h2>
        <p>{purchase_guide}</p>
    </body>
    </html>
    """
    return html_content

# 사용 예시
if __name__ == "__main__":
    product_info = {
        "title": "예시 제품",
        "price": "$100",
        "affiliate_link": "https://example.com/affiliate"
    }
    review_summary = "이 제품은 매우 좋습니다. 가격 대비 성능이 뛰어납니다."
    purchase_guide = "이 제품은 가성비가 뛰어나며, 추천합니다."
    
    html_post = generate_html_post(product_info, review_summary, purchase_guide)
    print(html_post)
