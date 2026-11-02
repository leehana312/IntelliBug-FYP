"""Page Object for logging in.

IntelliBug only has Google sign-in, and Selenium cannot pass Google's
checks. So the tests use the test-only route /_test_login, which exists
only when the app is started with TESTING=1.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LoginPage:
    SIDEBAR = (By.ID, "sidebar")
    LOGOUT_LINK = (By.CSS_SELECTOR, ".rail-logout")

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

    def login_as_demo(self):
        self.login_as("demo")

    def login_as(self, name):
        """Logs in as name@example.com (created on first use)."""
        self.driver.get(self.base_url + "/_test_login?user=" + name)
        WebDriverWait(self.driver, 15).until(
            EC.visibility_of_element_located(self.SIDEBAR)
        )

    def logout(self):
        self.driver.find_element(*self.LOGOUT_LINK).click()
        WebDriverWait(self.driver, 15).until(EC.url_contains("/login"))
