def page_text(page): return page.inner_text("body")
def click(page,selector): page.locator(selector).click()
def fill(page,selector,text): page.locator(selector).fill(text)
