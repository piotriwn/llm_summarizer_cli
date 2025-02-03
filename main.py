from typing import Dict, Union, List
import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import selenium
from selenium import webdriver
import time
from openai import AsyncOpenAI
import argparse
import asyncio
import aiohttp
import logging

IRRELEVANT_TAGS = [
    "script",
    "style",
    "img",
    "input",
    "head",
    "title",
    "meta",
    "[document]",
]

SYSTEM_PROMPT = """
You are an assistant that analyzes the contents of a website
and provides a short summary, ignoring text that might be navigation related.
Respond in markdown.
"""
USER_PROMPT_TITLE_TEMPLATE = "You are looking at a website titled "
USER_PROMPT_CONTENT_TEMPLATE = """
The contents of this website is as follows;
please provide a short summary of this website in markdown.
If it includes news or announcements, then summarize these too
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Website:
    @staticmethod
    def ensure_http_format(url: str) -> str:
        if not url.startswith("http://") and not url.startswith("https://"):
            return "http://" + url
        return url

    def __init__(
        self, url: str, chromedriver_path: str, chrome_binary_path: str, model: str
    ) -> None:
        self.url = Website.ensure_http_format(url)

        self.title = None
        self.text = None
        self.summarized = None
        self.chromedriver_path = chromedriver_path
        self.chrome_binary_path = chrome_binary_path
        self.model = model

    def __beautify(self, page_source: Union[str, bytes]) -> Dict[str, str]:
        soup = BeautifulSoup(page_source, "html.parser")
        title = soup.title.string if soup.title else "No title found"
        for irrelevant in soup.body(IRRELEVANT_TAGS):
            irrelevant.decompose()
        text = soup.body.get_text(separator="\n", strip=True)
        self.title = title
        self.text = text
        return {"title": title, "text": text}

    async def scrape_using_requests(self) -> Dict[str, str]:
        logging.info(f"Starting to scrape {self.url} using requests")
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                content = await response.read()
                logging.info(f"Finished scraping {self.url} using requests")
                return self.__beautify(content)

    async def scrape_using_selenium(self) -> Dict[str, str]:
        logging.info(f"Starting to scrape {self.url} using selenium")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._scrape_using_selenium_sync)
        logging.info(f"Finished scraping {self.url} using selenium")
        return result

    def _scrape_using_selenium_sync(self) -> Dict[str, str]:
        options = selenium.webdriver.chrome.options.Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.binary_location = self.chrome_binary_path

        service = selenium.webdriver.chrome.service.Service(self.chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)

        driver.get(self.url)
        time.sleep(5)
        page_bytes = driver.page_source.encode("utf-8")
        driver.quit()

        return self.__beautify(page_bytes)

    async def summarize(self) -> str:
        def generate_prompt(
            webpage_text: str, webpage_title: str
        ) -> List[Dict[str, str]]:
            return [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"{USER_PROMPT_TITLE_TEMPLATE} {webpage_title}\n{USER_PROMPT_CONTENT_TEMPLATE}:\n{webpage_text}",
                },
            ]

        openai = AsyncOpenAI()
        logging.info(f"Starting to summarize {self.url}")
        response = await openai.chat.completions.create(
            model=self.model,
            messages=generate_prompt(self.title, self.text),
        )
        self.summarized = response.choices[0].message.content
        logging.info(f"Finished summarizing {self.url}")
        return response.choices[0].message.content

    async def scrape_and_summarize(self, scrape_method: str) -> str:
        if scrape_method == "requests":
            await self.scrape_using_requests()
        elif scrape_method == "selenium":
            await self.scrape_using_selenium()
        else:
            raise ValueError("Invalid scrape method")
        return await self.summarize()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape and summarize websites.")
    parser.add_argument(
        "urls", metavar="URL", type=str, nargs="+", help="a list of URLs to scrape"
    )
    parser.add_argument(
        "--scrape-method",
        choices=["selenium", "requests"],
        default="requests",
        help="method to use for scraping",
    )
    parser.add_argument(
        "--chromedriver-path",
        type=str,
        default="./chromedriver-linux64/chromedriver",
        help="path to the chromedriver executable",
    )
    parser.add_argument(
        "--chrome-binary-path",
        type=str,
        default="./chrome-linux64/chrome",
        help="path to the Chrome binary",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="model to use for summarization",
    )
    return parser.parse_args()


async def main() -> None:
    load_dotenv()
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

    args = parse_arguments()

    tasks = []
    for url in args.urls:
        wb = Website(url, args.chromedriver_path, args.chrome_binary_path, args.model)
        tasks.append(wb.scrape_and_summarize(args.scrape_method))

    results = await asyncio.gather(*tasks)

    print("\n" + "-" * 80 + "\n")
    for url, summary in zip(args.urls, results):
        print(f"Summary for {url}:\n{summary}\n")
        print("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
