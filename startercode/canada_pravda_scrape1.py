from bs4 import BeautifulSoup
import requests
import csv

#.\pravda\Scripts\Activate.ps1

# source saves all the html elements of the webiste 
source = requests.get('https://news-pravda.com/world/2025/10/29/1816959.html').text

#https://canada.news-pravda.com/russia/2025/10/15/28473.html
#https://news-pravda.com/world/2025/10/16/1779190.html


#makes it format in nice format 
soup = BeautifulSoup(source ,'lxml')

# w is write 
csv_file = open('firstscrape.csv','w')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Date published','Title','Article','Source'])

# first step find the tag that encompassess one article then we can loop it later 

# find the keyword of article
article = soup.find('article')

#tag of the article 
tag = article.find('div',class_="article__breadcrumb article__breadcrumb_active").a.i.text  
print(tag, end="\n\n")

# time article published    find the first time tag in div 
dates = article.find('div',class_='article__time').time.text
print(dates, end="\n\n")


title = article.h1.text
print(title, end="\n\n")


paragraph = article.find('div',class_='article__text').text
print(paragraph, end="\n\n")

source = article.find('div',class_='article__source').text
print(source)


source_span = article.find('span', class_='article-meta__item source-link')
if source_span:
    source_url = source_span.get('data-source-url')
    source_name = source_span.get_text(strip=True)
else:
    source_url = None
    source_name = None 


# print(article.prettify())
csv_writer.writerow([dates,title,paragraph,source])

csv_file.close()