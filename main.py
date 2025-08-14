import asyncio

from playwright.async_api import async_playwright, BrowserContext, Page


async def main() -> None:
    async with async_playwright() as playwright:
        async with await playwright.chromium.launch(
                channel='chrome',
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
        ) as browser:
            context: BrowserContext = await browser.new_context()
            page: Page = await context.new_page()
            # await page.goto('https://www.dns-shop.ru/search/?q=5615302')
            await page.goto('https://www.dns-shop.ru/product/opinion/eaa728bcf803d582/termopasta-id-cooling-frost-x45/', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            counter = 0
            while True:
                counter += 1
                print(f"Итерация №{counter}")
                is_hidden = await page.locator('.opinions-widget__pagination').is_hidden()
                if is_hidden:
                    print("Подгружены все комментарии")
                    break
                show_more_button = page.locator('button.button-ui_grey:has-text("Показать ещё")')
                await show_more_button.click()
                await page.wait_for_timeout(5000)
            load_opinions = await page.locator(".ui-link_blue.ui-link_pseudolink.ui-collapse__link").all()
            for opinion in load_opinions:
                await opinion.click()
            load_more_opinions = await page.locator(".ui-link_pseudolink[data-role='open-answers']").all()
            for i in load_more_opinions:
                await i.click()
            # await page.click('.ui-link_pseudolink')
            content = await page.content()
            names = await page.query_selector_all('.profile-info__name')
            for i in names:
                print(await i.text_content())
            # print(content)
            input()
            await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
