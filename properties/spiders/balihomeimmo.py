import scrapy
from scrapy.loader import ItemLoader
from datetime import datetime
from properties import utils
from properties.items import define_property_type
import random
import requests

from properties.property_items.balihomeimmo import BaliHomeImmoProperty


def get(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Cookie": "gclid=undefined; cf_clearance=lcWV8cdtm5ThvCZFWO6_6R_k9dOo9L6LwwMfl.ry0cc-1696549111-0-1-26ec0f22.ce4862e0.bcfcd0ec-150.2.1696549111; twk_idm_key=NuZZjpthprHKzi9Yh13KD; XSRF-TOKEN=eyJpdiI6Im1nUGN0TitOSUFJS0NVYUtPTDNKenc9PSIsInZhbHVlIjoiWTdEMUpYOURDVW1QemFjWDBpZjZ5RDBvKzBRVDYyUGlKXC81QWMyQVNhd3JRUnltOHlMRlBpVWNaUkVpVkwxcnUiLCJtYWMiOiI4ZmE3MTAyOWNjZWZlZDU2M2YwMThkM2E1NmM3N2U3YThiYjM4ODRkNTBhMzE3NTM5N2IyYzc3MWMzOWEwZDQ1In0%3D; bali_home_immo_session=eyJpdiI6InhpNExcL0gxNk9CcDE5eHFlMUpKbmNBPT0iLCJ2YWx1ZSI6IkhcLzRoQkpKK3VZcitsSWZ0VlF5MmM5aGNPTVwvaGpjXC9GMUE3Mk5rbUQ2SFFSY2N6dzBENUVmTTRoTGtjazZjNmQiLCJtYWMiOiIyMDA1NGZlNDc0YTM3ODVmZDA2Zjg2Njk4YzJlNzAzYjUxYjBmMjYwN2I2MDMzM2E0MzJjMGFhMTM2M2UxMGJmIn0%3D; favorite_code=eyJpdiI6IjlvandpUnpDQVBhN29tczJLMFU4aGc9PSIsInZhbHVlIjoiVWMydEpod0ljUHpVbzhSTDNKRXdaSVdyYlpibmhJRmZkKzhDYzRWd1dDOHB3dnJPU1FSRm9kUStkMGk0aG5CWSIsIm1hYyI6IjU1NmQ4YjA4ODM2NTdlNzg2OWYzOGMxMmFjZGYyYzI0ODcyZmQzN2VhNThiYTIwYzBhNzBlM2IyNTJiM2Y0MWYifQ%3D%3D; TawkConnectionTime=0; twk_uuid_6110cac8d6e7610a49af4130=%7B%22uuid%22%3A%221.bJq41QkFYcTpQyMc95zkVPrswyAgheCvntq2Jly88U0fBKJy7MRUTOx03zeo7xZirQg9hJc5DTzWv2sWHbXd4mt0jPVDe69FgchIzjezmCYD8ern6hx0wlY27jQqM%22%2C%22version%22%3A3%2C%22domain%22%3A%22bali-home-immo.com%22%2C%22ts%22%3A1696576286079%7D",
    }
    response = requests.get(url, headers=headers)
    return scrapy.http.TextResponse(
        url=response.url,
        body=response.text,
        encoding="utf-8",
    )


class BaliHomeImmoSpider(scrapy.Spider):
    name = "balihomeimmo"
    allowed_domains = ["bali-home-immo.com"]

    def start_requests(self):
        self.numbers = []
        self.fakeurl = "https://jsonplaceholder.typicode.com/comments/1"
        url = "https://bali-home-immo.com/realestate-property/for-sale/villa"
        yield scrapy.Request(
            self.fakeurl,
            meta={"response": get(url)},
            dont_filter=True,
        )

    def parse(self, response):
        ## lambda functions ##
        has_leasehold = lambda strs: any(["lease" in str.lower() for str in strs])
        has_freehold = lambda strs: any(["free" in str.lower() for str in strs])
        ## main function ##
        now = datetime.now().replace(day=1).strftime(f"%m/%d/%y")
        response = response.meta.get("response")
        items = response.css(".properties-holder .property-item")
        for item in items:
            url = item.css("a::attr(href)").get()
            loader = ItemLoader(item=BaliHomeImmoProperty(), selector=item)
            loader.add_value("source", "Bali Home Immo")
            loader.add_value("property_link", url)
            loader.add_value("scrape_date", now)
            loader.add_css("id", "div[id]::attr(id)")
            loader.add_css("title", "h3")
            loader.add_css("location", ".top-desc p:has(i)::text")
            loader.add_css("image", "img::attr(src)")
            loader.add_value("availability", "Available")

            labels = item.css(".top-button-left li ::text").getall()
            if has_leasehold(labels):
                loader.add_css(
                    "years",
                    "div[id*=leasehold][class*=detail] span:contains(year) ::text",
                )
                contract_type = "Leasehold"
            elif has_freehold(labels):
                contract_type = "Freehold"
            else:
                continue

            price = 0
            if len(labels) == 1:
                price = item.css("#price-selector span::text").get()
            meta = dict(
                loader=loader,
                price=price,
                contract_type=contract_type,
                labels=labels,
                response=get(url),
            )
            yield scrapy.Request(
                self.fakeurl,
                callback=self.parse_detail,
                meta=meta,
                dont_filter=True,
            )
        # next page
        if len(items) > 0:
            if "?page" not in response.url:
                next_url = response.url + "?page=2"
            else:
                page = int(response.url.split("=")[-1])
                next_url = response.url.replace(f"page={page}", f"page={page+1}")
            yield scrapy.Request(
                self.fakeurl,
                callback=self.parse,
                meta={"response": get(next_url)},
                dont_filter=True,
            )

    def parse_detail(self, response):
        loader = response.meta.get("loader", {})
        labels = response.meta.get("labels", [])
        price = response.meta.get("price", 0)
        contract_type = response.meta.get("contract_type", "")

        response = response.meta.get("response")
        loader.selector = response

        table = response.css(".property-list-item-for-details table tr")
        details = {}
        for tr in table:
            key = tr.css("td:first-child::text").get().lower().replace(" ", "_")
            value = tr.css("td:nth-child(3)::text").get()
            details.update({key.strip(): value})

        beds = details.get("bedroom", "")
        baths = details.get("bathroom", "")
        land_size = details.get("land_size", "")
        build_size = details.get("building_size", "")

        if price == 0:
            css_selector = (
                f"span[data-price-category={contract_type.lower()}]::attr(data-price)"
            )
            price = response.css(css_selector).get()
            loader.add_css("price", css_selector)
        else:
            loader.add_value("price", price)

        loader.add_value("bedrooms", beds)
        loader.add_value("bathrooms", baths)
        loader.add_value("land_size", land_size)
        loader.add_value("build_size", build_size)
        loader.add_value("leasehold_freehold", contract_type)
        loader.add_css("description", "div.property-info-desc ::text")
        item = loader.load_item()

        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
            labels,
        )

        # find contract_type property_type
        item["leasehold_freehold"] += " " + define_property_type(item["title"])
        if item.get("price", 0) > 0:
            yield item
