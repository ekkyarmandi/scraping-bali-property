import scrapy
from scrapy.loader import ItemLoader
from datetime import datetime
import re
from properties import utils

from properties.property_items.kibarer import KibarerPropertyItem


def property_type(item):
    title = item.get("title", "").lower()
    contract_type = item.get("leasehold_freehold", "")
    types = ["villa", "apartement", "hotel", "land", "house", "home"]
    for t in types:
        if t in title:
            if t in ["house", "home"]:
                return contract_type + " House"
            else:
                return contract_type + " " + t.title()
    return contract_type + " Villa"  # the default is Villa


class KibarerSpider(scrapy.Spider):
    name = "kibarer"
    allowed_domains = ["villabalisale.com"]
    start_urls = [
        "https://www.villabalisale.com/search/villas-for-sale/",
    ]

    def parse(self, response):
        urls = response.css("#box div.property-item a::attr(href)")
        for url in urls:
            if url not in self.start_urls:
                yield response.follow(url, callback=self.parse_detail)
        next_url = response.css("div#pagination ul li a[rel*=next]::attr(href)").get()
        if next_url:
            yield response.follow(next_url, callback=self.parse)

    def parse_detail(self, response):
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        status = response.css("p.property-status strong::text").get()
        if status:
            if "lease" in status.lower():
                status = "Leasehold"
            elif "free" in status.lower():
                status = "Freehold"
            loader = ItemLoader(item=KibarerPropertyItem(), selector=response)
            loader.add_value("property_link", response.url)
            loader.add_value("source", "Kibarer")
            loader.add_value("availability", "Available")
            loader.add_value("scrape_date", now)
            loader.add_value("list_date", "")
            loader.add_css("id", ".proptitle p.code")
            loader.add_css("title", ".proptitle h1#property-name")
            loader.add_css(
                "location",
                "div.property-view-description-container p:contains(Location) strong",
            )
            loader.add_css("years", ".item p:contains(lease) + p")
            loader.add_value(
                "leasehold_freehold",
                status,
            )
            loader.add_css("bedrooms", '.item:has("i:contains(hotel)") p')
            loader.add_css("bathrooms", '.item:has("i.shower") p')
            loader.add_css(
                "land_size",
                "#land_size_data",
            )
            loader.add_css(
                "build_size",
                'p:has("#land_size_data") + p::text',
            )
            # loader.add_css("price", "div.price div.regular-price")
            loader.add_css("price_usd", "div.price div.regular-price")
            loader.add_css(
                "image", "div.left-side div.property_detail_slide figure img::attr(src)"
            )
            loader.add_css("description", "#property-description-container ::text")

            item = loader.load_item()

            # define property type
            item["leasehold_freehold"] = property_type(item)

            item["is_off_plan"] = utils.find_off_plan(
                item["title"],
                item["description"],
            )

            if type(item.get("price_usd", "")) == int:
                yield item
