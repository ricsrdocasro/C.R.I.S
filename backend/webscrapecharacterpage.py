from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import pandas as pd
from win32com.client import Dispatch
import html.parser

driver = webdriver.Chrome(executable_path='C:\Python39\Scripts\chromedriver')

namesList=[] #List to store name of the product
descriptionList=[] #List to store price of the product
categoryList=[]
imagesList=[] #List to store rating of the product

for url in newUrlList:
    driver.get(url)
    content = driver.page_source
    soup = BeautifulSoup(content, 'html.parser')

    name=soup.find('h1', attrs={'id':'firstHeading'})

    image=soup.find('img', attrs={'class':'pi-image-thumbnail'})

    for a in soup.findAll('div', attrs={'class':'mw-parser-output'}):
        last_links = a.find('class'=="aff-unit__disclaimer-message")
        last_links.decompose()
        description+=a.find_all('p')

    for a in soup.findAll('div', attrs={'class':'page-header__categories-links'}):
        try:
            category1=a.find('a', attrs={'data-tracking':'categories-top-0'})
            category2=a.find('a', attrs={'data-tracking':'categories-top-1'})
            category = str(category1.get_text()) + ": " + str(category2.get_text())

        except:
            category=a.find('a', attrs={'data-tracking':'categories-top-0'})

    print(category)

    for a in description:
        wholedescription = ''
        a=a.get_text()
        wholedescription += a

    descriptionList.append(wholedescription)
    namesList.append(name.text)
    categoryList.append(category)
    print(namesList)

    print(imagesList)

    data = {'Name': namesList, 'Category': categoryList, 'Description': descriptionList}

    df = pd.DataFrame(data=data)
    df.sort_values(by='Category')
    df.to_excel("all.xlsx")