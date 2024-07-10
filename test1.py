import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
from io import BytesIO
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, WebDriverException, ElementNotInteractableException
)

# Initialize Chrome WebDriver
driver = webdriver.Chrome()  # Ensure that the ChromeDriver is in your PATH or specify the path here

# Your 2Captcha API key
API_KEY = '269dfa478e96b9f7aee704a07c902539'

# Fixed password for all accounts
PASSWORD = 'YOUR_OWN_PASS'

# Base username
BASE_USERNAME = 'YOUR_USERNAME' 

# Path to the file to store the tried usernames
TRIED_USERNAMES_FILE = 'tried_usernames.txt'

# Load tried usernames from file
def load_tried_usernames():
    try:
        with open(TRIED_USERNAMES_FILE, 'r') as file:
            return set(line.strip() for line in file)
    except FileNotFoundError:
        return set()

# Save a username to the tried usernames file
def save_tried_username(username):
    with open(TRIED_USERNAMES_FILE, 'a') as file:
        file.write(f"{username}\n")

# Function to solve the CAPTCHA using 2Captcha API
def solve_captcha(captcha_image_url):
    print("Solving CAPTCHA...")
    try:
        # Download the CAPTCHA image
        response = requests.get(captcha_image_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        # Verify the image content
        if b'<!DOCTYPE html>' in response.content:
            print("Received HTML instead of image. Possible CAPTCHA bypass or error.")
            return None
        
        img = Image.open(BytesIO(response.content))
        img.save('captcha.png')
        
        # Send the CAPTCHA to 2Captcha for solving
        files = {'file': open('captcha.png', 'rb')}
        response = requests.post(f"http://2captcha.com/in.php?key={API_KEY}&method=post", files=files)
        response.raise_for_status()
        captcha_id = response.text.split('|')[1]
        
        # Retrieve the CAPTCHA solution
        while True:
            response = requests.get(f"http://2captcha.com/res.php?key={API_KEY}&action=get&id={captcha_id}")
            response.raise_for_status()
            if response.text == 'CAPCHA_NOT_READY':
                time.sleep(5)
            else:
                break
        
        captcha_solution = response.text.split('|')[1]
        print(f"CAPTCHA solved: {captcha_solution}")
        return captcha_solution
    
    except requests.RequestException as e:
        print(f"Request exception occurred: {e}")
    except Exception as e:
        print(f"An error occurred while solving CAPTCHA: {e}")
    
    return None  # Return None if CAPTCHA solving fails

# Check if the username is already taken
def is_username_taken(driver, username):
    print(f"Checking if the username '{username}' is taken...")
    try:
        driver.get("https://www.roblox.com/CreateAccount")
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "MonthDropdown")))
        time.sleep(1)  # Short delay to allow any initial page loads

        # Set birthdate
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "MonthDropdown"))).send_keys("Apr")  # Select month
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "DayDropdown"))).send_keys("1")  # Select day
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "YearDropdown"))).send_keys("2000")  # Select year

        # Enter username and password
        username_field = driver.find_element(By.ID, "signup-username")
        password_field = driver.find_element(By.ID, "signup-password")
        username_field.clear()
        username_field.send_keys(username)  # Enter username
        password_field.clear()
        password_field.send_keys(PASSWORD)  # Enter password

        # Select the male gender option
        try:
            male_button = driver.find_element(By.ID, "MaleButton")
            male_button.click()
        except NoSuchElementException:
            print("Male gender option not found.")

        # Click the Sign Up button
        try:
            sign_up_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "signup-button")))
            driver.execute_script("arguments[0].scrollIntoView(true);", sign_up_button)
            sign_up_button.click()
        except (NoSuchElementException, TimeoutException) as e:
            print(f"Error during sign up button click: {e}")
            return True  # Assume the username is taken or some other issue occurred

        # Check for CAPTCHA presence
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'modal-modern-challenge-captcha')]")))
            captcha_frame = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, '/arkose/iframe')]")))
            captcha_image_url = captcha_frame.get_attribute("src")
            captcha_solution = solve_captcha(captcha_image_url)
            if captcha_solution:
                driver.switch_to.default_content()  # Switch back to the main content
                captcha_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, "captchaSolution")))
                captcha_input.send_keys(captcha_solution)  # Enter CAPTCHA solution
                sign_up_button.click()
                WebDriverWait(driver, 10).until(EC.url_changes(driver.current_url))  # Wait for the page to change
                print(f"CAPTCHA solved and submitted for username: {username}")
                return is_username_taken(driver, username)  # Check again if the username is taken
        except NoSuchElementException:
            print("No CAPTCHA found, proceeding with sign-up.")
        except Exception as e:
            print(f"An error occurred while solving CAPTCHA: {e}")

        # Check if the Sign Up button is enabled (which indicates that the username is available)
        try:
            sign_up_button = driver.find_element(By.ID, "signup-button")
            if sign_up_button.is_enabled():
                print(f"Username '{username}' is available.")
                return False  # If the Sign Up button is enabled, the username is available
        except NoSuchElementException:
            print(f"Could not find the Sign Up button for the username '{username}'")
            return True

        print(f"Username '{username}' might be taken or another error occurred.")
        return True

    except WebDriverException as e:
        print(f"WebDriverException occurred: {e}")
    except Exception as e:
        print(f"An error occurred while checking the username '{username}': {e}")

    return True  # Assume the username is taken or some other issue occurred

# Increment the username by adding or increasing a number at the end
def increment_username(username):
    base_username, index = username, 1
    if username[-1].isdigit():
        base_username = ''.join(filter(lambda x: not x.isdigit(), username))
        index = int(username[len(base_username):]) + 1

    return f"{base_username}{index}"

# Sign up with the provided username and password
def sign_up(driver, username, password):
    try:
        driver.get("https://www.roblox.com/CreateAccount")
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "MonthDropdown")))
        time.sleep(1)  # Short delay to allow any initial page loads

        # Set birthdate
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "MonthDropdown"))).send_keys("Apr")  # Select month
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "DayDropdown"))).send_keys("1")  # Select day
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "YearDropdown"))).send_keys("2000")  # Select year

        # Enter username and password
        username_field = driver.find_element(By.ID, "signup-username")
        password_field = driver.find_element(By.ID, "signup-password")
        username_field.clear()
        username_field.send_keys(username)  # Enter username
        password_field.clear()
        password_field.send_keys(PASSWORD)  # Enter password

        # Select the male gender option
        try:
            male_button = driver.find_element(By.ID, "MaleButton")
            male_button.click()
        except NoSuchElementException:
            print("Male gender option not found.")

        # Click the Sign Up button
        try:
            sign_up_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "signup-button")))
            driver.execute_script("arguments[0].scrollIntoView(true);", sign_up_button)
            sign_up_button.click()
        except (NoSuchElementException, TimeoutException) as e:
            print(f"Error during sign up button click: {e}")
            return

        # Check for CAPTCHA presence and handle it
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'modal-modern-challenge-captcha')]")))
            captcha_frame = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, '/arkose/iframe')]")))
            captcha_image_url = captcha_frame.get_attribute("src")
            captcha_solution = solve_captcha(captcha_image_url)
            if captcha_solution:
                driver.switch_to.default_content()  # Switch back to the main content
                captcha_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, "captchaSolution")))
                captcha_input.send_keys(captcha_solution)  # Enter CAPTCHA solution
                sign_up_button.click()
                WebDriverWait(driver, 10).until(EC.url_changes(driver.current_url))  # Wait for the page to change
                print(f"CAPTCHA solved and submitted for username: {username}")
                return
        except NoSuchElementException:
            driver.switch_to.default_content()  # Switch back to the main content
            print("No CAPTCHA found, proceeding with sign-up.")
        except Exception as e:
            print(f"An error occurred while solving CAPTCHA: {e}")

        # Check if the Sign Up button is enabled (which indicates that the username is available)
        try:
            sign_up_button = driver.find_element(By.ID, "signup-button")
            if sign_up_button.is_enabled():
                print(f"Sign-up process completed for username: {username}")
                return
        except NoSuchElementException:
            print(f"Could not find the Sign Up button for the username '{username}'")
        except Exception as e:
            print(f"An error occurred during sign up for username '{username}': {e}")

        print(f"Sign up process completed for username: {username}")

    except WebDriverException as e:
        print(f"WebDriverException occurred: {e}")
    except Exception as e:
        print(f"An error occurred during sign up for username '{username}': {e}")

def main():
    """
    Main function to manage the sign-up process.
    """
    tried_usernames = load_tried_usernames()
    username = BASE_USERNAME

    while True:
        if username in tried_usernames:
            print(f"Username '{username}' has already been tried. Skipping.")
            username = increment_username(username)
            continue

        if not is_username_taken(driver, username):
            print(f"Attempting to sign up with username: {username}")
            try:
                sign_up(driver, username, PASSWORD)
                print(f"Successfully signed up with username: {username}")
                break  # Exit the loop if sign-up was successful
            except Exception as e:
                print(f"An exception occurred during sign-up: {e}")
                # Continue to the next username on failure
        else:
            print(f"Username '{username}' is taken. Trying the next username.")
        
        # Increment the username and add to the tried list
        tried_usernames.add(username)
        save_tried_username(username)
        username = increment_username(username)
        time.sleep(1)  # Add a small delay between attempts to avoid being rate-limited

if __name__ == "__main__":
    main()
