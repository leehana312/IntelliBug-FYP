"""Page Objects for the Bug Reports list and the bug detail page."""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BugReportsPage:
    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

    def open(self):
        self.driver.get(self.base_url + "/reports")
        WebDriverWait(self.driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "form.filters"))
        )

    def has_bug(self, title):
        return len(self.driver.find_elements(By.LINK_TEXT, title)) > 0

    def bug_link(self, title):
        return self.driver.find_element(By.LINK_TEXT, title).get_attribute("href")

    def open_bug(self, title):
        self.driver.find_element(By.LINK_TEXT, title).click()
        WebDriverWait(self.driver, 15).until(EC.url_contains("/reports/"))

    def row_status(self, title):
        """Status text shown in the list row of the bug with this title."""
        row_status = (
            By.XPATH,
            f"//a[normalize-space()='{title}']/ancestor::tr//span[contains(@class,'status-badge')]",
        )
        return self.driver.find_element(*row_status).text

    def wait_for_row_status(self, title, status):
        """Waits until the list row shows this status. Fails after 10 seconds
        if the page still shows an old status."""
        WebDriverWait(self.driver, 10).until(
            lambda d: self.row_status(title) == status,
            message=f"List row for '{title}' never showed status '{status}'",
        )


class BugDetailPage:
    STATUS_BADGE = (By.CSS_SELECTOR, ".status-badge")
    RESOLVE_BUTTON = (By.XPATH, "//button[normalize-space()='Mark as Resolved']")
    IN_PROGRESS_BUTTON = (By.XPATH, "//button[normalize-space()='In Progress']")

    def __init__(self, driver):
        self.driver = driver

    def mark_resolved(self):
        self.driver.find_element(*self.RESOLVE_BUTTON).click()

    def mark_in_progress(self):
        self.driver.find_element(*self.IN_PROGRESS_BUTTON).click()

    def wait_for_status(self, status):
        # The page reloads after the click, so wait for the new text.
        WebDriverWait(self.driver, 15).until(
            EC.text_to_be_present_in_element(self.STATUS_BADGE, status)
        )
        return self.driver.find_element(*self.STATUS_BADGE).text
