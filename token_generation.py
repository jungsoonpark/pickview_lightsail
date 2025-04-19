import hashlib
import time
import requests

# App key, secret, and authorization code (hardcoded for now)
app_key = "513774"  # 실제 app_key
app_secret = "Uzy0PtFg3oqmIFZtXrrGEN9s0speXaXl"  # 실제 app_secret
authorization_code = "3_513774_b38kGp17gUB9Kq1mFDYfL60v3668"  # 사용자 인증 후 받은 실제 코드

# Generate timestamp
timestamp = str(int(time.time() * 1000))  # Millisecond timestamp

# Define sign method
sign_method = "sha256"

# Parameters to send in the request
params = {
    "code": authorization_code,
    "app_key": app_key,
    "sign_method": sign_method,
    "timestamp": timestamp
}

# Sort parameters alphabetically (ASCII order)
sorted_params = sorted(params.items())

# Concatenate the sorted parameters into a string
param_string = ''.join(f"{key}{value}" for key, value in sorted_params)

# Construct the string to sign (append API path and app_secret on both ends)
api_path = "/rest/auth/token/create"
string_to_sign = f"{api_path}{param_string}{app_secret}"

# Create signature using md5 or sha256
signature = hashlib.sha256(string_to_sign.encode('utf-8')).hexdigest().upper()

# Add the signature to the parameters
params['sign'] = signature

# Build the final request URL (ensure all parameters are joined by &)
url = f"https://api-sg.aliexpress.com{api_path}?{'&'.join([f'{key}={value}' for key, value in params.items()])}"

# Send the POST request
response = requests.post(url, data=params)

# Print the response status and content
print(f"Response Status Code: {response.status_code}")
print(f"Response Body: {response.text}")

# Check if the access token was received
if response.status_code == 200:
    access_token = response.json().get('access_token')
    print(f"Access Token: {access_token}")
else:
    print("Failed to obtain access token")
