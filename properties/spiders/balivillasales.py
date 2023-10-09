import scrapy

from scrapy.loader import ItemLoader
from itemloaders.processors import MapCompose
from properties import utils
from properties.items import get_lease_years, get_uploaded_date
from properties.property_items.balivillasales import BaliVillaSalesPropertyItem
from datetime import datetime
import re


def extract_price(response, selector):
    price = response.css(selector).get()
    idr = ""
    usd = ""
    lease_years = None
    is_sold_out = False
    p = price.strip().lower().split("/")
    if len(p) > 1:
        lease_years = p[-1]
    if "idr" in p[0]:
        idr = p[0]
    elif "usd" in p[0]:
        usd = p[0]
    elif "sold" in p[0]:
        is_sold_out = p[0]
    return idr, usd, is_sold_out, lease_years


class BaliVillaSalesSpider(scrapy.Spider):
    name = "balivillasales"
    allowed_domains = ["balivillasales.com"]
    start_urls = ["https://www.balivillasales.com"]

    def parse(self, response):
        remove_sqm = lambda str: str.replace("m2", "") if "m2" in str else str
        # collect items
        items = response.css("#top .container .product-types")
        for item in items:
            url = item.css("a::attr(href)").get()
            loader = ItemLoader(item=BaliVillaSalesPropertyItem(), selector=item)
            idr, usd, is_sold_out, lease_years = extract_price(
                response=item, selector=".price::text"
            )
            if lease_years:
                contract_type = "Leasehold"
            else:
                contract_type = response.css('span[class*="key"]::text').get()
            loader.add_css("id", ".mid span.villa-code::text")
            loader.add_css("bedrooms", 'span[class*="bed"]::text')
            loader.add_css(
                "land_size", 'span[title="Land Size"]::text', MapCompose(remove_sqm)
            )
            loader.add_css(
                "build_size",
                'span[title="Building Size"]::text',
                MapCompose(remove_sqm),
            )
            loader.add_css("image", "a img::attr(src)")
            loader.add_css(
                "list_date", "a img::attr(src)", MapCompose(get_uploaded_date)
            )
            loader.add_value("availability", "Sold" if is_sold_out else "Available")
            loader.add_value("leasehold_freehold", [contract_type, "Villa"])
            loader.add_value("years", lease_years, MapCompose(get_lease_years))
            loader.add_value("price", idr)
            loader.add_value("price_usd", usd)
            loader.add_value("property_link", url)
            meta = dict(loader=loader)
            yield response.follow(url, callback=self.parse_detail, meta=meta)
        # go to next url
        next_url = response.css("#wp_page_numbers ul li:last-child a::attr(href)").get()
        if next_url and next_url != response.url:
            yield response.follow(next_url, callback=self.parse)

    def parse_detail(self, response):
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        i = response.meta
        loader = i.get("loader")
        loader.selector = response
        loader.add_value("source", "Villas of Bali")
        loader.add_value("scrape_date", now)
        loader.add_css("bathrooms", ".details span:contains(Bathroom)::text")
        loader.add_css("title", "h1#stitle::text")
        loader.add_css("location", ".code-location span span::text")
        loader.add_css(
            "description", [".the_content p::text", ".the_content div::text"]
        )
        item = loader.load_item()
        idr = item.get("price", 0)
        usd = item.get("price_usd", 0)

        # find off-plan
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
        )
        if idr > 0 or usd > 0:
            yield item
