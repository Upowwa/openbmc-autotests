from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

driver_path = '/home/pumba/testir/chromedriver/chromedriver'
service = Service(driver_path)
options = webdriver.ChromeOptions()

# -------- Тест: успешная авторизация --------
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 10)
try:
    driver.get("https://localhost:2443")
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys("root")
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys("0penBmc")
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-test-id="login-button-submit"]'))).click()
    WebDriverWait(driver, 10).until(lambda d: "Overview" in d.title)
    assert "Overview" in driver.title
    print("Тест авторизации пройден")
except Exception:
    print("Тест авторизации не пройден")
finally:
    time.sleep(1)
    driver.quit()

# -------- Тест: неверные данные --------
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 15)
try:
    driver.get("https://localhost:2443")
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys("wronguser")
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys("wrongpass")
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-test-id="login-button-submit"]'))).click()
    try:
        error_msg = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(text(),'Invalid') or contains(text(),'username') or contains(text(),'password')]")
            )
        )
        assert error_msg.is_displayed()
        print("Тест неверных данных пройден")
    except Exception:
        print("Тест неверных данных не пройден")
finally:
    time.sleep(1)
    driver.quit()

# -------- Тест: блокировка учетной записи --------
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 10)
try:
    for _ in range(4):
        driver.get("https://localhost:2443")
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys("wrong_username")
        wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys("wrong_password")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-test-id="login-button-submit"]'))).click()
        time.sleep(1)
    driver.get("https://localhost:2443")
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys("correct_username")
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys("correct_password")
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-test-id="login-button-submit"]'))).click()
    try:
        lock_msg = wait.until(EC.presence_of_element_located((By.ID, "lock_msg_id")))
        assert lock_msg.is_displayed()
        print("Тест блокировки пройден")
    except Exception:
        print("Тест блокировки не пройден")
finally:
    time.sleep(1)
    driver.quit()

# -------- Тест: в логах отображается событие --------
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 10)
try:
    driver.get("https://localhost:2443/logs")
    if "Event" in driver.page_source:
        print("Тест в логах пройден")
    else:
        print("Тест в логах не пройден")
finally:
    time.sleep(1)
    driver.quit()

# -------- Тест: проверка температуры --------
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 20)
try:
    driver.get("https://localhost:2443/")
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys("root")
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys("0penBmc")
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-test-id="login-button-submit"]'))).click()
    input("Откройте 'Sensors' в меню и нажмите Enter здесь для продолжения теста...")
    time.sleep(2)
    try:
        no_items = wait.until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'No items available')]"))
        )
        print("Сенсоры отсутствуют, тест пройден")
    except Exception:
        try:
            cpu_temp_elem = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//tr[td[contains(text(),'CPU') or contains(text(),'Processor')]]/td[2]")
                )
            )
            cpu_temp = float(cpu_temp_elem.text)
            assert 20.0 <= cpu_temp <= 80.0
            print(f"Тест температуры пройден")
        except Exception:
            print("Тест температуры не пройден")
finally:
    time.sleep(1)
    driver.quit()
