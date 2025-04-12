# wordpress_uploader.py

import requests

def upload_post_to_wordpress(title, content, wordpress_url, username, password):
    # WordPress REST API 엔드포인트
    api_url = f"{wordpress_url}/wp-json/wp/v2/posts"
    
    # 인증 정보
    credentials = (username, password)
    
    # 포스트 데이터
    post_data = {
        "title": title,
        "content": content,
        "status": "publish"  # 'draft'로 설정하면 초안으로 저장
    }
    
    try:
        # API 요청
        response = requests.post(api_url, json=post_data, auth=credentials)
        response.raise_for_status()  # 요청이 성공하지 않으면 예외 발생
        
        print("포스트가 성공적으로 업로드되었습니다:", response.json())
    except requests.exceptions.RequestException as e:
        print(f"WordPress API 요청 중 오류 발생: {e}")

# 사용 예시
if __name__ == "__main__":
    title = "예시 제품 포스트"
    content = "<h1>예시 제품</h1><p>이 제품은 매우 좋습니다.</p>"  # HTML 포스트 내용
    wordpress_url = "https://yourwordpresssite.com"  # 실제 WordPress URL로 변경
    username = "your_username"  # WordPress 사용자 이름
    password = "your_password"  # WordPress 비밀번호
    
    upload_post_to_wordpress(title, content, wordpress_url, username, password)
