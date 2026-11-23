import chronim

browser = chronim.connect()
try:
    browser.open("https://www.google.com")
    browser.wait_for_load()
    browser.type("textarea[name=q]", "Chronim Python Chrome")
    browser.press("ENTER")
    browser.wait_for_load()
    print(browser.title())
finally:
    browser.disconnect()
