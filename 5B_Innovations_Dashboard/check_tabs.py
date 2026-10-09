import requests
import re
url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTXPCvDoC8AqzKUhwmqT_1FeannEle2Bu0558uHXdSdzpQhc0oYXS-Zrl-w6C0bt-21M1Tk0i0Jr9L4/pubhtml'
r = requests.get(url)
matches = re.findall(r'<li id=\"sheet-button-(.*?)\".*?><a.*?>(.*?)</a></li>', r.text)
for gid, name in matches:
    print(f'GID: {gid}, Name: {name}')
if not matches:
    print("No tabs found.")
