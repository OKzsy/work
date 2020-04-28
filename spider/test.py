import requests
from requests.auth import AuthBase
from requests.auth import HTTPBasicAuth
from io import StringIO
import csv
import re
from bs4 import BeautifulSoup

url = "http://www.pythonscraping.com/pages/page3.html"
html = requests.get(url)
html_text = html.text
bs = BeautifulSoup(html_text, "html.parser")
images = bs.find_all('img',{'src':re.compile('\.\.\/img\/gifts\/img\d\.jpg')})
for image in images:
    print(image.parent.previous_sibling.get_text())
    print(image.attrs['src'])
print('end')