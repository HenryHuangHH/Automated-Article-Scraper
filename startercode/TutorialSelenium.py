from selenium import webdriver
import time
PATH= "C:\Program Files (x86)\chromedriver.exe"

#instance of chrome browser 
driver = webdriver.Chrome()

driver.get("https://techwithtim.net")

# time.sleep(10)



print(driver.title)
input("Press Enter to exit...")
driver.quit()


# # by class id or other 
# input_element = driver.find.element(By.CLASS_NAME,"news-item__title")

# input_element.clear()
# # PRESS ENTER AND SERACH HI
# input_element.send_keys("HI" + keys.ENTER)



# wait for the thing to load 
# links = WebDriverWait(driver,5).until(
#     EC.presence_of_all_elements_located((By.CLASS_NAME,"news-item__title"))

# )