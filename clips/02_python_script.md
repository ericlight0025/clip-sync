# Python 爬蟲範例

import requests
from bs4 import BeautifulSoup

def fetch_titles(url):
    """抓取網頁標題"""
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')
    return [h2.text for h2 in soup.find_all('h2')]

if __name__ == '__main__':
    titles = fetch_titles('https://news.ycombinator.com')
    for t in titles:
        print(f'- {t}')
