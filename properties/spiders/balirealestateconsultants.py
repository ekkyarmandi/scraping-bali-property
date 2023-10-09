import scrapy
from scrapy.loader import ItemLoader
from properties import utils
from properties.property_items.balirealestateconsultants import (
    BaliRealEstatePropertyItem,
)
from datetime import datetime
from pprint import pprint

# import pandas as pd
import re


class BaliRealEstateConsultantsSpider(scrapy.Spider):
    name = "balirealestateconsultants"
    allowed_domains = ["balirealestateconsultants.com"]
    start_urls = [
        "https://balirealestateconsultants.com/properties/?tab=for-sale&tax=property_status"
    ]

    def parse(self, response):
        # collect property items
        items = response.css("#module_properties > .card")
        for item in items:
            url = item.css("h2 a::attr(href)").get()
            lease_years = item.css(".item-body div.item-address::text").get()
            if lease_years:
                contract_type = "Leasehold"
            else:
                contract_type = "Freehold"
            meta = {
                "image": item.css(".listing-thumb a img::attr(src)").get(),
                "property_type": item.css(
                    "ul.item-amenities li:last-child span::text"
                ).get(),
                "contract_type": contract_type,
                "lease_years": lease_years,
            }
            yield response.follow(url, callback=self.parse_detail, meta=meta)

        # go to the next page
        next_url = response.css("ul.pagination li a[aria-label=Next]::attr(href)").get()
        if next_url:
            yield response.follow(next_url, callback=self.parse)

    def parse_detail(self, response):
        i = response.meta
        w = lambda str: re.search(r"\w+", str).group()

        contract_type = i.get("contract_type")
        property_type = w(i.get("property_type", ""))

        # get details
        to_key = lambda str: str.strip().lower().replace(" ", "_")
        d = {}
        details = response.css("#property-overview-wrap ul")
        for ul in details:
            key = ul.css("li:nth-child(2)::text").get()
            if key == "m²":
                key = "land_size"
            key = to_key(key.replace("m²", ""))
            if "bathroom" in key:
                key = "bathrooms"
            elif "bedroom" in key:
                key = "bedrooms"
            value = ul.css("li:nth-child(1) strong::text").get()
            d.update({key: value})
        # print("DETAILS")
        # pprint(d)

        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        loader = ItemLoader(item=BaliRealEstatePropertyItem(), selector=response)
        loader.add_value("source", "Bali Real Estate Consultants")
        loader.add_value("scrape_date", now)
        loader.add_value("property_link", response.url)
        # loader.add_value("list_date", "")
        loader.add_value("leasehold_freehold", [contract_type, property_type])
        loader.add_value("years", i.get("lease_years"))
        loader.add_value("image", i.get("image"))
        loader.add_value("id", d.get("property_id"))
        loader.add_value("bedrooms", d.get("bedrooms"))
        loader.add_value("bathrooms", d.get("bathrooms"))
        loader.add_value("land_size", d.get("land_size"))
        loader.add_value("build_size", d.get("lot"))
        # loader.add_css("price", "")
        loader.add_css("availability", "div.property-labels-wrap a")
        loader.add_css("price_usd", "li.item-price")
        loader.add_css("title", "h1")
        loader.add_css("location", "address.item-address")
        loader.add_css(
            "description", ".property-description-wrap .block-content-wrap p"
        )

        item = loader.load_item()

        # find off-plan
        labels = response.css("div.property-labels-wrap a::text").getall()
        labels = list(map(str.strip, labels))
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
            labels,
        )

        # filter the entries by price
        idr = item.get("price", 0)
        usd = item.get("price_usd", 0)
        try:
            if idr > 0 or usd > 0:
                yield item
        except:
            print(f"ERROR: price='{idr}' price_usd='{usd}'")
