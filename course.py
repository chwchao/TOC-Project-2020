from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
import datetime

browser = webdriver.Chrome("./chromedriver")
browser.get('http://course-query.acad.ncku.edu.tw/qry/qry001.php?dept_no=A9')

print(browser.find_element_by_xpath("//tr[1]//td[17]").text)

browser.stop_client()
browser.close()
#if (browser.find_element_by_xpath("//tr[163]//td[17]").text != "額滿"):
        