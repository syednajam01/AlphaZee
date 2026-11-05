import sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser('.local/test_check') as b:
    b.goto('http://localhost:13000/')
    b.wait_for_selector('.hero-section', timeout=10)
    time.sleep(2)
    print("Hero HTML snippet:")
    print(b.js('document.querySelector(".hero-section") ? document.querySelector(".hero-section").innerHTML.slice(0, 1000) : "no hero"'))

