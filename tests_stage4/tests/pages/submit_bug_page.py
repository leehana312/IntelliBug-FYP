"""Page Object for the Submit Bug page."""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SubmitBugPage:
    TITLE = (By.ID, "title")
    PRODUCT = (By.ID, "product")
    ENVIRONMENT = (By.ID, "environment")
    DESCRIPTION = (By.ID, "description")
    SCREENSHOT_INPUT = (By.ID, "screenshot-input")
    SUBMIT_BUTTON = (By.ID, "submit-btn")
    RESULT_PANEL = (By.ID, "result-panel")
    SEVERITY_BADGE = (By.ID, "severity-badge")
    FLOW_STEPS = (By.CSS_SELECTOR, "#recommendation-flow .rec-step")
    ERROR_MESSAGE = (By.ID, "error-msg")

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

    def open(self):
        self.driver.get(self.base_url + "/submit")
        WebDriverWait(self.driver, 15).until(
            EC.visibility_of_element_located(self.TITLE)
        )

    def fill_form(self, title, product, environment, description):
        self.driver.find_element(*self.TITLE).send_keys(title)
        self.driver.find_element(*self.PRODUCT).send_keys(product)
        self.driver.find_element(*self.ENVIRONMENT).send_keys(environment)
        self.driver.find_element(*self.DESCRIPTION).send_keys(description)

    def attach_screenshot(self, file_path):
        # The real file input is hidden behind the dropzone, and Selenium
        # cannot type into a hidden element. Show it first, then send the path.
        file_input = self.driver.find_element(*self.SCREENSHOT_INPUT)
        self.driver.execute_script(
            "arguments[0].hidden = false; arguments[0].style.display = 'block';",
            file_input,
        )
        file_input.send_keys(file_path)

    def submit(self):
        self.driver.find_element(*self.SUBMIT_BUTTON).click()

    def wait_for_result(self):
        # The server calls the model and Claude, so allow up to 30 seconds.
        return WebDriverWait(self.driver, 30).until(
            EC.visibility_of_element_located(self.RESULT_PANEL)
        )

    def get_severity(self):
        return self.driver.find_element(*self.SEVERITY_BADGE).text

    def count_flow_steps(self):
        return len(self.driver.find_elements(*self.FLOW_STEPS))

    def wait_for_error(self):
        return WebDriverWait(self.driver, 15).until(
            EC.visibility_of_element_located(self.ERROR_MESSAGE)
        )

    def is_result_visible(self):
        return self.driver.find_element(*self.RESULT_PANEL).is_displayed()

    def is_missing(self, locator):
        """True when the browser's own 'required' check flags this field as empty."""
        field = self.driver.find_element(*locator)
        return self.driver.execute_script("return arguments[0].validity.valueMissing;", field)
