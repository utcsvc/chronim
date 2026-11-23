import chronim

browser = chronim.connect()
try:
    tab = browser.new_tab("https://example.com")
    browser.wait_for_load()
    print("Opened:", tab)
    print("Tabs:", browser.get_tabs())
finally:
    browser.disconnect()
