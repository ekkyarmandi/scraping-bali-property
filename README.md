# Bali Property Data Scraping

### How to use

0. Make sure you already installed Python and Git on your computer

```bash
python --version  # output: Python x.xx
git --version  # output: git version x.xx
```

1. Git clone this repo  

```bash
git clone https://github.com/ekkyarmandi/scraping-bali-property.git (dir-path)[optional]
```

```bash
cd [dir-path]
```

2. Install dependencies  
   (optional) you can create [virtual environtment](https://python.land/virtual-environments/virtualenv) before installing all the dependencies

```bash
python -m venv <virtual-env-name>
```

activating it

```bash
source <virtual-env-name>/bin/activate # on MacOS / Linus
<virtual-env-name>/scripts/activate.bat # on WinOS
```

Installing the dependencies

```
pip install -r requirements.txt
```

> Read [this](https://pip.pypa.io/en/stable/installation) if you can't PIP

3. Run scrapy command
> On your terminal type

```bash
scrapy crawl <spider-name>
```

Spider are the scraper that will scrape the data. If you go to [spiders](properties/spiders/) directory you will find all the spiders you can use. Subtitute `spider-name` above with the file name.
You also can add `--output`, `-o` parameter to output the file as a `csv` or `json`.

```bash
scrapy crawl <spider-name> -o <filename>.csv
```

4. Google Sheet uploader  
   I also add extra file name `uploader.py` where you can append the csv file data into the google sheet

- To uploading it, you should have a Google API key that has Google Sheet API and Google Drive API added to the [Google Cloud](https://console.developers.google.com) library you create. You can search it on [Youtube](https://www.youtube.com/results?search_query=how+to+use+gspread)
- Download the Service Account key as JSON file and renamed it as `creds.json` that file will be read automatically by `uploader.py`
