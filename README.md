# Summary

This application summarizes web pages. It has option to do using both web APIs of LLMs (Open AI and GPT in this case) as well as using locally running model (I used Lllama).

It's able to scrape traditional HTML pages as well as those JS-heavy that require Selenium scraping.

# Requirements

- OpenAI API Key to send requests to GPT. Include it in the `.env` file, like `OPENAI_API_KEY=abcdef`.
- [Chrome Driver](https://googlechromelabs.github.io/chrome-for-testing/). For example run:
```
wget https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.159/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
wget https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.159/linux64/chrome-linux64.zip
unzip chrome-linux64.zip
```
- Python >= 3.10 (may as well work with prior versions), `venv`.

# How to run

Run a virtual env:

```
python3 -m venv venv
source venv/bin/activate
```

Install requirements:

```
python3 -m pip install -r requirements.txt
```

Use `python -h` to check the arguments, an example is:

```
python main.py bbc.com www.cnn.com https://wikipedia.org http://reddit.com  --model gpt-4o
```

To run using local llama3.2:

```
python main.py bbc.com --model llama3.2 --use-local-endpoint
```


# FAQ

## Beatuful Soup vs Selenium

(written by GPT 4o)

The key difference between BeautifulSoup and Selenium is how they handle JavaScript-generated content.

### BeautifulSoup (with requests/urllib) – Static Scraping

- How it works: BeautifulSoup parses HTML from a web page as it is received from the server. It does not execute JavaScript.
- Best used for: Pages that have all their content fully loaded in the initial HTML response.
- Limitations: If a webpage uses JavaScript to fetch and display content after loading, BeautifulSoup will not see this data because it's not present in the raw HTML.
- Example: Scraping a blog, Wikipedia, or a website where all content is present in the page source.

### Selenium – Dynamic Scraping

- How it works: Selenium automates a web browser (e.g., Chrome, Firefox) and renders JavaScript just like a real user.
- Best used for:
    - Pages that load content dynamically via JavaScript (e.g., Single Page Applications (SPAs) built with React, Vue, Angular).
    - Websites requiring user interaction (e.g., clicking buttons, scrolling, logging in).
- Limitations:
    - Slower than BeautifulSoup because it has to open a browser and interact with the page.
    - Resource-heavy, as it uses an actual browser (or headless mode).

### When to Use Selenium Instead of BeautifulSoup

- JavaScript-Generated Content: If you inspect the page source (Ctrl + U) and don’t see the data, but it appears when you inspect elements (F12), the page is using JavaScript to render content.
- Data Appears After a Delay: If the data loads after scrolling or clicking a button, it's likely fetched via JavaScript (AJAX requests).
- Interactivity is Required: If the website requires logins, dropdown selections, button clicks, or other interactions to show content.
- Infinite Scrolling or Pagination: If new content is loaded as you scroll (e.g., Twitter feed, Instagram).