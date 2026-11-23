import chronim

browser = chronim.connect()
try:
    browser.open("https://example.com")
    browser.wait_for_load()
    print(browser.title())
    print(browser.url())
finally:
    browser.disconnect()
