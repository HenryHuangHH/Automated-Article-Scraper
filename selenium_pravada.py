from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By 
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementNotInteractableException, TimeoutException
from bs4 import BeautifulSoup
import requests
import csv
import time
import re
import json

#from functions import functionname, functionanme
#.\pravda\Scripts\Activate.ps1

def scrape(link,driver):
    # check for network errors
    try:
        source = requests.get(link, timeout=10)
        source.raise_for_status()  # Raise error if page not found
        soup = BeautifulSoup(source.text ,'lxml')
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch {link}: {e}")
        return None

    article = soup.find('article')
    if not article:
        print(f"[WARNING] No article found at {link}")
        return None

    # tag = article.find('div',class_="article__breadcrumb article__breadcrumb_active").a.i.text  
    # Avoid AttributeError
    tag_div = article.find('div',class_="article__breadcrumb article__breadcrumb_active")
    if tag_div and tag_div.a and tag_div.a.i:
        tag = tag_div.a.i.text  
    else:
        tag = "n/a"
    # print(tag, end="\n\n")

    dates_div = article.find('div',class_='article__time')
    if dates_div and dates_div.time:
        dates = dates_div.time.text
    else:
        dates = "n/a"
    # print(type(dates)) str
    # print(dates, end="\n\n")

    title = article.h1.text if article.h1 else "n/a"
    # print(title, end="\n\n")

    paragraph_div = article.find('div',class_='article__text')
    paragraph = paragraph_div.text if paragraph_div else "n/a"
    # print(paragraph, end="\n\n")

    source_div = article.find('div',class_='article__source')
    source = source_div.text if source_div else "n/a"
    # print(source)

    source_span = article.find('span', class_='article-meta__item source-link')
    if source_span:
        source_url = source_span.get('data-source-url', 'n/a')
        source_name = source_span.get_text(strip=True) or "n/a"
        if source_name.lower().startswith("telegram"):
            source_name = re.sub(r'(Telegram)\b.*', r'\1', source_name)
    else:
        source_url = "n/a"
        source_name = "n/a" 

    if "t.me/" in source_url:
        source_account = source_url.split("t.me/")[-1].strip("/")
    else:
        source_account = "n/a"

    dataframe = {
        driver.current_url: {
            "tag": tag,
            "date":dates,
            "title":title,
            "paragraph":paragraph,
            "source_name":source_name,
            "source_account":source_account,
            "source_url": source_url
        }
    }

    return dataframe
        

service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome()
#https://trump.news-pravda.com/
#https://news-pravda.com/
driver.get("https://news-pravda.com/")

links = driver.find_elements(By.CLASS_NAME, "news-item__title")
time.sleep(2)

result = []

# for i in range(0,5):
#     url = links[i].get_attribute("href")

#     links[i].click()

#     result.append(scrape(url,driver))
#     time.sleep(2)

    
#     driver.back()
for i in range(len(links)):
    try:
        url = links[i].get_attribute("href")

        driver.execute_script("arguments[0].scrollIntoView(true);", links[i])
        time.sleep(0.5)

        links[i].click()
        time.sleep(1)

        # [MODIFIED] Check if scrape returned None before appending
        data = scrape(url, driver)
        if data:
            result.append(data)
        time.sleep(2)

        driver.back()
        time.sleep(2)

    except ElementNotInteractableException:
        # warning print
        print(f"[WARNING] Element not interactable, skipping index {i}")
        continue
    except Exception as e:
        # Catch any unexpected error
        print(f"[ERROR] Unexpected error at index {i}: {e}")
        continue

with open('./scraped_trump_data.json', 'w', encoding='utf-8') as f:
    # dump convert py data to json
    json.dump(result,f, indent=4, ensure_ascii=False) 

driver.quit()
