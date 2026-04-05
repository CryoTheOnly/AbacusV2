import requests

url = "https://weather.com/weather/today/l/92cba1c3903ca3481419603edf4cce05fa6181189af9e61839ba3c941b378871"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)

print(response.text)