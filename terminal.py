#2) 작업 폴더 이동
cd /Users/J.S.Park/Desktop/pickview_scraper

#1)서버접속

ssh -i ./pickview_scraper.pem ubuntu@ec2-3-24-217-157.ap-southeast-2.compute.amazonaws.com

#3) 가상환경 만들기 (처음 1회만)

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install pandas playwright gspread google-auth google-auth-oauthlib google-auth-httplib2
playwright install

#4) 매번 작업할 때 (터미널 껐다 켜면)

cd ~/pickview_scraper
source venv/bin/activate
python3 scraper.py


#오류난다면?
pip install pandas playwright gspread google-auth google-auth-oauthlib google-auth-httplib2
python -m playwright install