import os
from playwright.sync_api import sync_playwright
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

IMAGES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docs', 'images')
os.makedirs(IMAGES, exist_ok=True)

BASE = 'http://127.0.0.1:8000'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 900})
    page = context.new_page()
    page.goto(BASE + '/users/login/')
    page.fill('input[name="username"]', 'demo')
    page.fill('input[name="password"]', 'demopass')
    page.click('button[type="submit"]')
    page.wait_for_timeout(300)
    page.goto(BASE + '/')
    page.wait_for_timeout(300)
    page.screenshot(path=os.path.join(IMAGES, '05-dashboard.png'), full_page=False)
    print('Saved 05-dashboard.png')
    browser.close()
