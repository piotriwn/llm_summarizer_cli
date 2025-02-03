from typing import Dict, Union, List
import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import selenium
from selenium import webdriver
import time
from openai import OpenAI
import argparse  # Added import for argparse

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

    def scrape_using_requests(self) -> Dict[str, str]:
        response = requests.get(self.url)
        response.raise_for_status()  # Raises HTTPError, if one occurred.
        return self.__beautify(response.content)  # Content of the response, in bytes.

    def scrape_using_selenium(self) -> Dict[str, str]:
        # Set Chrome options for headless mode
        options = selenium.webdriver.chrome.options.Options()
        options.add_argument("--headless")  # Run without opening a window
        options.add_argument("--disable-gpu")  # Required for some headless environments
        options.add_argument("--window-size=1920x1080")  # Ensures full page rendering
        options.add_argument("--no-sandbox")  # Bypass OS security model
        options.add_argument("--disable-dev-shm-usage")  # Prevents memory issues
        options.binary_location = self.chrome_binary_path  # Path to Chrome binary

        service = selenium.webdriver.chrome.service.Service(self.chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)

        driver.get(self.url)
        time.sleep(5)
        page_bytes = driver.page_source.encode("utf-8")
        driver.quit()

        return self.__beautify(page_bytes)

    def summarize(self) -> str:
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

        openai = OpenAI()
        response = openai.chat.completions.create(
            model=self.model,
            messages=generate_prompt(self.title, self.text),
        )
        self.summarized = response.choices[0].message.content
        return response.choices[0].message.content

    def scrape_and_summarize(self, scrape_method: str) -> None:
        if scrape_method == "requests":
            self.scrape_using_requests()
        elif scrape_method == "selenium":
            self.scrape_using_selenium()
        else:
            raise ValueError("Invalid scrape method")
        self.summarize()
        return


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


def main() -> None:
    load_dotenv()
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

    args = parse_arguments()

    for url in args.urls:
        wb = Website(url, args.chromedriver_path, args.chrome_binary_path, args.model)
        wb.scrape_and_summarize(args.scrape_method)
        print(f"Summary for {wb.url}:\n{wb.summarized}\n")


if __name__ == "__main__":
    main()
