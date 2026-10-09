import requests
import re
url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vT1Uk0Rh0nVQkvd8wBhFWZnjaU1WgiwQmSTU_WRuofKg3nV0LpdCbZxarQOL-EGgpUqLESKZpbSHOF_/pubhtml'
r = requests.get(url)
# Find sheet names directly from the HTML source since regex parsing html is messy
from html.parser import HTMLParser
class SheetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_sheet_list = False
        self.current_gid = None
        self.sheets = {}
        
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'li' and 'id' in attrs and attrs['id'].startswith('sheet-button-'):
            self.current_gid = attrs['id'].replace('sheet-button-', '')
            
    def handle_data(self, data):
        if self.current_gid and data.strip():
            self.sheets[self.current_gid] = data.strip()
            self.current_gid = None

parser = SheetParser()
parser.feed(r.text)
for gid, name in parser.sheets.items():
    print(f'GID: {gid}, Name: {name}')
