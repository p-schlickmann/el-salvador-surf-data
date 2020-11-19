"""file responsible for scraping data from surfguru.com.br"""

import re
from time import sleep
from datetime import timedelta, date

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from utils.conn import DatabaseConnection
from utils.secrets import EMAIL, PASSWORD


class Scraper:
    """This class is responsible for scraping data"""

    def __init__(self, target):
        self.database_path = ''
        self.driver = webdriver.Chrome('../chromedriver.exe')
        self.target = target
        self.email = EMAIL
        self.password = PASSWORD

    def _login(self):
        bot = self.driver

        # accept cookies
        WebDriverWait(bot, 20).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '#aceitar_cookies_conteudo button'))).click()

        # login
        bot.find_element_by_xpath('//*[@id="deslogado"]/ul/li[1]/a').click()
        email_field = bot.find_element_by_id("UsuarioEmail")
        email_field.clear()
        email_field.send_keys(self.email)
        password_field = bot.find_element_by_id("UsuarioSenha")
        password_field.clear()
        password_field.send_keys(self.password)
        bot.find_element_by_css_selector('#menu_login input[type="submit"]').click()

    @staticmethod
    def _save_results(date, time, size, period):
        with DatabaseConnection('./data.db') as cursor:
            try:
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS results (date TEXT, time INTEGER, size FLOAT, period FLOAT)")

                cursor.execute("INSERT INTO results VALUES (?, ?, ?, ?)", (date, time, size, period))
            except:
                print(f'[-] Problem while saving info for {date} at {time}h')

    @staticmethod
    def reset_db():
        """Resets the database, but check if the user is sure first"""

        reset_db = input("Are you sure you want to reset DB? [y/N]: ")
        if reset_db == 'y':
            with DatabaseConnection('./data.db') as cursor:
                cursor.execute("DROP TABLE IF EXISTS results")

    def exit_ad(self):
        """If we get redirected out of main page"""

        bot = self.driver
        if bot.current_url() != self.target:
            bot.execute_script("window.history.go(-1)")

    def extract_data(self):
        """Responsible for extracting the data and passing to save_results function"""

        bot = self.driver
        self.exit_ad()

        year = self.get_current_year()

        for _ in range(1, 6):  # 5 days
            for _ in range(1, 9):  # 8 charts in 1 day
                retries = 0
                while True:  # try 5 times
                    if retries > 4:
                        self._save_results(f"Erro", 0, 0, 0)
                        break
                    try:
                        chart = bot.find_element_by_id(f'title_dia{i}_hora{j}')
                        hover = ActionChains(bot).move_to_element(chart)
                        hover.perform()

                        day, month = bot.find_element_by_css_selector("#data b").text.split('/')
                        raw_time = bot.find_element_by_id("hora").text
                        expression = '[0-9]+:'
                        matches = re.search(expression, raw_time)
                        time = matches.group(0)[:-1]
                        wave_size = bot.find_element_by_id("tot_alt").text[:-2]
                        wave_period = bot.find_element_by_id("tot_per").text[:-2]
                    except Exception:
                        print("Trying again...")
                        retries += 1
                        continue
                    else:
                        self._save_results(f"{day}-{month}-{year}", time, wave_size, wave_period)
                        break

    def get_current_year(self):
        """Returns current year and scrolls the page so we can simulate mouse hover"""

        bot = self.driver

        for _ in range(5):  # try 5 times
            try:
                page = WebDriverWait(bot, 10).until(
                     EC.element_to_be_clickable((By.TAG_NAME, 'body')))
                page.send_keys(Keys.PAGE_DOWN)
                *_, year = WebDriverWait(bot, 10).until(
                    EC.presence_of_element_located((By.ID, 'datepicker'))).get_attribute(
                        "value").split(" - ")
            except:
                continue
            else:
                return year

    def _open_date_picker(self):
        WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable(
                (By.ID, 'datepicker'))).click()

    def _select_year(self, year):
        year_choices = Select(self.driver.find_element_by_css_selector(
            "#ui-datepicker-div > div > div > select.ui-datepicker-year"))
        year_choices.select_by_value(year)

    def _select_month(self, month_number):
        month_choices = Select(self.driver.find_element_by_css_selector(
            "#ui-datepicker-div > div > div > select.ui-datepicker-month"))
        month_choices.select_by_value(month_number)

    def _select_day(self, day):
        bot = self.driver
        for _ in range(5):  # try 5 times
            try:
                bot.find_element_by_css_selector(
                    '#ui-datepicker-div > table > tbody').find_element_by_xpath(
                        f'.//a[contains(text(), "{day}")]').click()
                bot.find_element_by_id("btn-ver").click()
                break
            except Exception:
                sleep(0.5)
                continue

    @staticmethod
    def date_range(start_date, end_date):
        """Python Generator that yields time interval"""

        range_days = int((end_date - start_date).days)
        for day in range(0, range_days, 5):  # 5 days in between
            yield start_date + timedelta(day)

    def scrape(self):
        """Logins and scrapes the surf data on the given date range"""

        bot = self.driver
        try:
            bot.get(self.target)
            self._login()

            current_year = None
            current_month = None
            start_date = date(2019, 12, 7)
            end_date = date(2020, 12, 1)

            for day in self.date_range(start_date, end_date):
                self.exit_ad()
                self._open_date_picker()

                # check if year has changed
                year_number = day.strftime("%Y")
                if year_number != current_year:
                    current_year = year_number
                    self._select_year(year_number)

                # transform to integer to subtract 1 (surfguru page uses january as 0)
                month_number = str(int(day.strftime("%m")) - 1)

                # check if month has changed
                if month_number != current_month:
                    current_month = month_number
                    self._select_month(month_number)

                day_number = str(int(day.strftime("%d")))
                self._select_day(day_number)

                self.extract_data()

        except IndentationError:
            pass


scraper = Scraper("https://www.surfguru.com.br/previsao/el-salvador/la-libertad/la-libertad")
scraper.scrape()
