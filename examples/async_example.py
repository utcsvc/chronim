import asyncio
import chronim

async def main():
    browser = await chronim.connect_async()
    try:
        await browser.open("https://example.com")
        await browser.wait_for_load()
        print(await browser.title())
    finally:
        await browser.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
