from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
# from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

URL = "https://games.mercadolivre.com.br/para-playstation-4-gamepads-e-joysticks/controle-ps4_PriceRange_60-200_PublishedToday_YES_NoIndex_True"
PATH = "C:\Program Files (x86)\chromedriver.exe"
s = Service(PATH)
driver = webdriver.Chrome(service=s)
driver.get(URL)

precos: list = driver.find_elements(By.CLASS_NAME, "ui-search-result__wrapper")
# driver.page_source
# print(precos)
for e in precos:
    e: WebElement
    price: WebElement = e.find_element(By.CLASS_NAME, "price-tag-amount")
    print(price.text)

time.sleep(5)
driver.quit()