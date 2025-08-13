import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import os

CHROME_DRIVER_PATH = os.path.join(os.path.dirname(__file__), "..", "chromedriver")

chrome_options = Options()
chrome_options.add_argument("--headless")

service = Service(executable_path=CHROME_DRIVER_PATH)

driver = webdriver.Chrome(service=service, options=chrome_options)

driver.get("http://www.google.com/")
time.sleep(2)

search_box = driver.find_element(By.NAME, "q")
search_box.send_keys("ChromeDriver")
search_box.submit()

time.sleep(2) 

driver.quit()
