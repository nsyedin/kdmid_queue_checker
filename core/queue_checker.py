import numpy as np
import pytesseract
import time
import datetime
import os
import json

import selenium
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from webdriver_manager.chrome import ChromeDriverManager

import base64
from io import BytesIO
from PIL import Image

import logging

logging.basicConfig(filename='queue.log',
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)


class QueueChecker:
    def __init__(self, kdmid_subdomain, order_id, code):
        self.kdmid_subdomain = kdmid_subdomain
        self.order_id = order_id
        self.code = code
        self.url = 'http://' + self.kdmid_subdomain + '.kdmid.ru/queue/OrderInfo.aspx?id=' + self.order_id + '&cd=' + self.code
        self.image_name = 'captcha_processed.png'
        self.screen_name = "screenshot0.png"
        self.button_dalee = "//input[@id='ctl00_MainContent_ButtonA']"
        self.button_inscribe = "//input[@id='ctl00_MainContent_ButtonB']"
        self.main_button_id = "//input[@id='ctl00_MainContent_Button1']"
        self.text_form = "//input[@id='ctl00_MainContent_txtCode']"
        self.checkbox = "//input[@id='ctl00_MainContent_RadioButtonList1_0']"
        self.error_code = "//span[@id='ctl00_MainContent_Label_Message']"
        # self.error_code = "//div[@class='error_msg']"
        self.captcha_error = "//span[@id='ctl00_MainContent_lblCodeErr']"

    def write_success_file(self, text, status):
        d = {'status': status, 'message': text}
        if d['status'] == 'success':
            with open(self.order_id + "_" + self.code + "_success.json", 'w', encoding="utf-8") as f:
                json.dump(d, f)
        elif d['status'] == 'error':
            with open(self.order_id + "_" + self.code + "_error.json", 'w', encoding="utf-8") as f:
                json.dump(d, f)

    def check_exists_by_xpath(self, xpath, driver):
        mark = False
        try:
            driver.find_element(By.XPATH, xpath)
            mark = True
            return mark
        except NoSuchElementException:
            return mark

    def recognize_captcha(self, driver, error_screen=None):
        driver.save_screenshot("screenshot.png")

        screenshot = driver.get_screenshot_as_base64()
        img = Image.open(BytesIO(base64.b64decode(screenshot)))

        element = driver.find_element(By.XPATH, '//img[@id="ctl00_MainContent_imgSecNum"]')
        loc = element.location
        size = element.size

        left = loc['x']
        top = loc['y']
        right = (loc['x'] + size['width'])
        bottom = (loc['y'] + size['height'])
        screenshot = driver.get_screenshot_as_base64()
        # Get size of the part of the screen visible in the screenshot
        screensize = (driver.execute_script("return document.body.clientWidth"),
                      driver.execute_script("return window.innerHeight"))
        img = img.resize(screensize)

        box = (int(left) + 200, int(top), int(right) - 200, int(bottom))
        area = img.crop(box)
        area.save(self.screen_name, 'PNG')
        os.remove("screenshot.png")

        from twocaptcha import TwoCaptcha
        api_key = os.environ['API_KEY']
        solver = TwoCaptcha(api_key)
        try:
            result = solver.normal(self.screen_name)
        except Exception as e:
            print('{} - Error recognizing captcha'.format(e))
            return ''
        return result['code']

    def check_queue(self):
        message = ''
        status = ''
        print('{} Checking queue for: {} - {}'.format(datetime.date.today(), self.order_id, self.code))
        logging.info('Checking queue for: {} - {}'.format(self.order_id, self.code))
        # chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(ChromeDriverManager().install())
        driver.maximize_window()
        driver.get(self.url)

        error = True
        error_screen = False
        # iterate until captcha is recognized 
        while error:
            digits = self.recognize_captcha(driver)
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, self.text_form))).send_keys(
                str(digits))

            time.sleep(1)
            # if the security code is wrong, expired or not from this order, stop the process
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, self.error_code))
                )
                status = 'error'
                message = 'The security code {} is written wrong, has expired or is not from this order. Theck it and try again.'.format(
                    self.code)

                self.write_success_file(str(message), str(status))
                logging.warning(f'{message}')
                break
            except:
                pass

            if self.check_exists_by_xpath(self.button_dalee, driver):
                driver.find_element(By.XPATH, self.button_dalee).click()

            if self.check_exists_by_xpath(self.button_inscribe, driver):
                driver.find_element(By.XPATH, self.button_inscribe).click()

            window_after = driver.window_handles[0]
            driver.switch_to.window(window_after)

            error = False

            try:
                driver.find_element(By.XPATH, self.main_button_id)
            except:
                error = True
                error_screen = True

                try:
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, self.text_form))
                    )
                except:
                    print("Element not found")

                driver.find_element(By.XPATH, self.text_form).clear()

        try:
            if self.check_exists_by_xpath(self.checkbox, driver):
                driver.find_element(By.XPATH, self.checkbox).click()
                check_box = driver.find_element(By.XPATH, self.checkbox)
                val = check_box.get_attribute("value")
                message = 'Appointment date: {}, time: {}, purpose: {}'.format(
                    val.split('|')[1].split('T')[0],
                    val.split('|')[1].split('T')[1],
                    val.split('|')[-1]
                )
                logging.info(message)
                WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, self.main_button_id))).click()
                status = 'success'
                self.write_success_file(message, str(status))

            else:
                message = '{} - no free timeslots for now'.format(datetime.date.today())
                status = 'in process'
                print(message)
                logging.info(message)
        except:
            message = '{} --- no free timeslots for now'.format(datetime.date.today())
            logging.info(message)

        driver.quit()
        if os.path.exists(self.screen_name):
            os.remove(self.screen_name)
        if os.path.exists(self.image_name):
            os.remove(self.image_name)

        return message, status
