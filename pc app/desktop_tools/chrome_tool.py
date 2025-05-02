from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from numpy import random

class ChromeTool:
    def __init__(self, system:str):
        # win32 (Windows), darwin (macOS), or other (Linux)
        self.system = system 
        self.chrome_driver = None
        
    def open_chrome(self, url:str) -> tuple[int, str]:
        self.chrome_driver = webdriver.Chrome()  
        try:
            self.chrome_driver.get(url)

            return (0, "Success!")
        except Exception as e:
            return (1, "Encountered exception on opening chrome: " + e)
        
    def close_chrome(self) -> tuple[int, str]:
        if self.chrome_driver:
            try:
                self.chrome_driver.quit()
                self.chrome_driver = None
                return (0, "Chrome browser closed successfully.")
            except Exception as e:
                return (1, "Encountered exception on closing chrome: " + e)
        else:
            return (2, "No Chrome Browser instance to close.")
        
    def fetch_chrome_html(self) -> tuple[int, str]:
        if self.chrome_driver:
            try:
                return (0, self.chrome_driver.page_source)
            except Exception as e:
                return (1, "Encountered exception on fetching HTML: " + e)
        else:
            return (2, "No Chrome Browser instance to close.")
        
    def search_google_chrome(self, input:str) -> tuple[int, str]:
        try:
            self.chrome_driver = webdriver.Chrome()
            self.chrome_driver.get("https://google.com")
            
            search_box = self.chrome_driver.find_element(By.NAME, "q")  # Locate search bar
            time.sleep(random.random() / 5)
            
            for c in input:
                search_box.send_keys(c)   
                time.sleep(random.random() / 5)
            
            return (0, "Success!")
        except:
            return (1, "Could not find form to interact with.")
        
        
    def form_submit_chrome(self, name:str) -> tuple[int, str]:
        if self.chrome_driver:
            try:
                search_box = self.chrome_driver.find_element(By.NAME, name)  # Locate form
                search_box.send_keys(Keys.RETURN) # Submit  
                
                # Wait for the page to load
                time.sleep(0.5)
                
                # Check for CAPTCHA elements on the page
                if "captcha" in self.chrome_driver.page_source.lower():
                    return (3, "CAPTCHA detected. Please complete the CAPTCHA manually.")
                else:
                    return (0, "Success!")
                 
            except:
                return (1, "Could not find form to interact with.")
        else:
                return (2, "No Chrome Browser instance to close.")
        
        
if __name__ == "__main__":
    pc = ChromeTool("win32")
    time.sleep(2)
    pc.search_google_chrome("New Laptops")
    time.sleep(2)
    res = pc.form_submit_chrome("q")
    
    if res[0] == 3: print(res[1])
    time.sleep(10 if res[0] == 3 else 2) # Wait for users to do captcha if required
    
    pc.close_chrome()