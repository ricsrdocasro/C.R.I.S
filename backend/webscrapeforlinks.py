from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import pandas as pd
import html.parser


driver = webdriver.Chrome(executable_path='C:\Python39\Scripts\chromedriver')

urlsList=[]
newUrlList = []

driver.get("https://ordemparanormal.fandom.com/wiki/Personagens#Organiza%C3%A7%C3%B5es" )
content = driver.page_source
soup = BeautifulSoup(content, 'html.parser')

for a in soup.findAll('div', attrs={'class':'moldura-container'}):
    for b in a.findAll('a', href=True):
        print(b["href"])
        urlsList.append(b["href"])

for url in urlsList:
    newUrl = 'https://ordemparanormal.fandom.com' + url
    newUrlList.append(newUrl)

newUrlList=list(set(newUrlList))
print(newUrlList)