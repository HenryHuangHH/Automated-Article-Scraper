from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By 
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from bs4 import BeautifulSoup
import requests
import csv
#from functions import functionname, functionanme

def scrape(link):
    source = requests.get(link).text
    soup = BeautifulSoup(source ,'lxml')
    article = soup.find('article')
    tag = article.find('div',class_="article__breadcrumb article__breadcrumb_active").a.i.text  
    print(tag, end="\n\n")
    dates = article.find('div',class_='article__time').time.text
    print(dates, end="\n\n")
    title = article.h1.text
    print(title, end="\n\n")

    paragraph = article.find('div',class_='article__text').text
    print(paragraph, end="\n\n")

    source = article.find('div',class_='article__source').text
    print(source)


service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome()

driver.get("https://news-pravda.com/")


links = driver.find_elements(By.CLASS_NAME, "news-item__title")
time.sleep(2)

for i in range(1,3):
    url = links[i].get_attribute("href")
    links[i].click()
    
    scrape(url)
    time.sleep(3)
    print()
    driver.back()

driver.quit()