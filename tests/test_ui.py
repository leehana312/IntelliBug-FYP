"""IntelliBug UI tests: login, submission, required fields, status change, logout."""
import pytest
from pages.login_page import LoginPage
from pages.submit_bug_page import SubmitBugPage
from pages.bug_reports_page import BugReportsPage, BugDetailPage


def test_login_reaches_dashboard(driver, base_url):
    login_page = LoginPage(driver, base_url)
    login_page.login_as_demo()
    assert "IntelliBug" in driver.title


def test_submit_valid_bug_shows_severity_and_diagram(driver, base_url, test_image):
    LoginPage(driver, base_url).login_as_demo()

    submit_page = SubmitBugPage(driver, base_url)
    submit_page.open()
    submit_page.fill_form(
        title="Login button unresponsive on Safari",
        product="Customer Portal",
        environment="Safari 17, macOS",
        description="Expected: user reaches dashboard. Actual: nothing happens after clicking Login.",
    )
    submit_page.attach_screenshot(test_image)
    submit_page.submit()

    submit_page.wait_for_result()
    assert submit_page.get_severity() in ("Critical", "Medium", "Low")
    assert submit_page.count_flow_steps() >= 1


# ---------------------------------------------------------------
# Stage 3: required fields, status change, logout
# ---------------------------------------------------------------
FIELDS = {
    "title": SubmitBugPage.TITLE,
    "product": SubmitBugPage.PRODUCT,
    "environment": SubmitBugPage.ENVIRONMENT,
    "description": SubmitBugPage.DESCRIPTION,
}
VALUES = {
    "title": "Checkout page freezes",
    "product": "Customer Portal",
    "environment": "Chrome 126, Windows 11",
    "description": "Expected: order completes. Actual: the page freezes.",
}


def test_empty_form_is_blocked(driver, base_url):
    LoginPage(driver, base_url).login_as_demo()
    submit_page = SubmitBugPage(driver, base_url)
    submit_page.open()
    submit_page.submit()
    assert submit_page.is_missing(SubmitBugPage.TITLE)
    assert not submit_page.is_result_visible()


@pytest.mark.parametrize("empty_field", list(FIELDS))
def test_each_text_field_is_required(driver, base_url, empty_field):
    LoginPage(driver, base_url).login_as_demo()
    submit_page = SubmitBugPage(driver, base_url)
    submit_page.open()
    for name, locator in FIELDS.items():
        if name != empty_field:
            driver.find_element(*locator).send_keys(VALUES[name])
    submit_page.submit()
    assert submit_page.is_missing(FIELDS[empty_field])
    assert not submit_page.is_result_visible()


def test_missing_screenshot_shows_error(driver, base_url):
    LoginPage(driver, base_url).login_as_demo()
    submit_page = SubmitBugPage(driver, base_url)
    submit_page.open()
    submit_page.fill_form(**VALUES)
    submit_page.submit()
    error = submit_page.wait_for_error()
    assert "attach a screenshot" in error.text
    assert not submit_page.is_result_visible()


def test_mark_resolved_updates_status(driver, base_url, new_bug):
    reports_page = BugReportsPage(driver, base_url)
    reports_page.open()
    reports_page.open_bug(new_bug)

    detail_page = BugDetailPage(driver)
    detail_page.mark_resolved()
    assert detail_page.wait_for_status("Resolved") == "Resolved"


def test_list_shows_new_status_after_back_button(driver, base_url, new_bug):
    reports_page = BugReportsPage(driver, base_url)
    reports_page.open()
    assert reports_page.row_status(new_bug) == "Open"
    reports_page.open_bug(new_bug)

    detail_page = BugDetailPage(driver)
    detail_page.mark_resolved()
    detail_page.wait_for_status("Resolved")

    driver.back()
    reports_page.wait_for_row_status(new_bug, "Resolved")


def test_logout_returns_to_login_page(driver, base_url):
    login_page = LoginPage(driver, base_url)
    login_page.login_as_demo()
    login_page.logout()
    assert "/login" in driver.current_url
