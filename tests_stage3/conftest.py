"""Shared pytest setup: opens Chrome for each test, makes a small test
image, and attaches a screenshot to the HTML report after every test."""
import base64
import os
import struct
import uuid
import zlib
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = os.environ.get("INTELLIBUG_URL", "http://127.0.0.1:5000")


@pytest.fixture
def driver():
    options = Options()
    if os.environ.get("HEADLESS") == "1":
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,900")
    drv = webdriver.Chrome(options=options)
    yield drv
    drv.quit()


@pytest.fixture
def base_url():
    return BASE_URL


@pytest.fixture
def test_image(tmp_path):
    """Writes a tiny valid PNG and returns its path."""
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data)))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
           + chunk(b"IEND", b""))
    path = tmp_path / "issue.png"
    path.write_bytes(png)
    return str(path)


@pytest.fixture
def new_bug(driver, base_url, test_image):
    """Logs in, submits one bug with a unique title, and returns that title."""
    from pages.login_page import LoginPage
    from pages.submit_bug_page import SubmitBugPage

    title = f"Selenium test bug {uuid.uuid4().hex[:8]}"
    LoginPage(driver, base_url).login_as_demo()
    page = SubmitBugPage(driver, base_url)
    page.open()
    page.fill_form(title, "Customer Portal", "Chrome 126, Windows 11",
                   "Expected: page loads. Actual: page shows a blank screen.")
    page.attach_screenshot(test_image)
    page.submit()
    page.wait_for_result()
    return title


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    driver = item.funcargs.get("driver")
    if driver is None:
        return
    os.makedirs("screenshots", exist_ok=True)
    file_name = f"screenshots/{item.name}.png"
    driver.save_screenshot(file_name)
    try:
        from pytest_html import extras
        extra = getattr(report, "extras", [])
        with open(file_name, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        extra.append(extras.image(encoded))
        report.extras = extra
    except ImportError:
        pass
