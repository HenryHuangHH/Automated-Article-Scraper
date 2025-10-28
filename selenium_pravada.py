from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By 
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
import requests
import csv
import time

import json

#from functions import functionname, functionanme
#.\pravda\Scripts\Activate.ps1

def scrape(link,driver):
    source = requests.get(link).text
    soup = BeautifulSoup(source ,'lxml')
    article = soup.find('article')
    tag = article.find('div',class_="article__breadcrumb article__breadcrumb_active").a.i.text  
    # print(tag, end="\n\n")
    dates = article.find('div',class_='article__time').time.text
    # print(type(dates)) str
    # print(dates, end="\n\n")
    title = article.h1.text
    # print(title, end="\n\n")

    paragraph = article.find('div',class_='article__text').text
    # print(paragraph, end="\n\n")

    source = article.find('div',class_='article__source').text
    # print(source)

    dataframe = {
        driver.current_url: {
            "tag": tag,
            "date":dates,
            "title":title,
            "paragraph":paragraph,
            "source":source
        }
    }

    return dataframe
    


service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome()

driver.get("https://news-pravda.com/")


links = driver.find_elements(By.CLASS_NAME, "news-item__title")
time.sleep(2)


result = []

for i in range(1,3):
    url = links[i].get_attribute("href")
    links[i].click()

    result.append(scrape(url,driver))
    time.sleep(2)

    
    driver.back()

with open('./scraped_data.json', 'w') as f:
    # dump convert py data to json
    json.dump(result,f, indent=4)
    

driver.quit()