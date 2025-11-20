from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome(service=service)

# Open the Pravda domain
driver.get("https://news-pravda.com/")

# Set to store unique links
all_links = set()
duplicate_count = 0  # [ADDED] Counter for duplicate links

# Get initial scroll height
last_height = driver.execute_script("return document.body.scrollHeight")

while True:
    # Grab all article elements currently loaded
    new_elements = driver.find_elements(By.CLASS_NAME, "news-item__title")
    
    # Extract href from each element and add to set to avoid duplicates
    for elem in new_elements:
        href = elem.get_attribute("href")
        if href:
            if href in all_links:
                duplicate_count += 1  # [ADDED] Increment duplicate counter
            all_links.add(href)
    
    # Scroll to bottom to load more articles
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)  # wait for new content to load

    # Check if page height has changed
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        # No more articles loaded
        break
    last_height = new_height

# Print how many links were found
print(f"Total article links found: {len(all_links)}")
print(f"Duplicate links encountered (ignored): {duplicate_count}")  # [ADDED]

# Optional: print first few links
for i, link in enumerate(list(all_links)[:10], 1):
    print(f"{i}: {link}")

driver.quit()
