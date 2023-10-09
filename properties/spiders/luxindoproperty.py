import scrapy
from scrapy.loader import ItemLoader
from properties import utils
from properties.items import define_property_type
from properties.property_items.luxindoproperty import LuxindoPropertyItem
from datetime import datetime
import re


def div_to_dict(selector, css):
    rows = selector.css(css).getall()
    detail = list(map(lambda s: list(map(str.strip, s.split(":"))), rows))
    detail = list(filter(lambda s: len(s) == 2, detail))
    detail = {v[0]: v[1] for v in detail}
    return detail


def is_idr(value):
    if "rp" in value.lower():
        return True
    else:
        return False


def get_lease_years(ul):
    for li in ul:
        key = li.css("::text").get().replace(":", "").strip()
        value = li.css("strong::text").get()
        if value and "lease" in key.lower():
            new_value = re.search(r"(?P<years>\d+)\s+years", value)
            if new_value:
                return new_value.group("years")
    return ""


class LuxindopropertySpider(scrapy.Spider):
    name = "luxindoproperty"
    allowed_domains = ["luxindoproperty.com"]
    start_urls = [
        "https://luxindoproperty.com/properties/?sort=date_desc&limit=24&property_type%5B%5D=67"
    ]

    def parse(self, response):
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        # collect property detail and urls
        items = response.css("div.site__main div.listing__item")
        for item in items:
            url = item.css("div.properties__info a::attr(href)").get()
            detail = div_to_dict(item, "div.properties__info a p::text")
            loader = ItemLoader(item=LuxindoPropertyItem(), selector=item)
            loader.add_value("property_link", url)
            loader.add_value("scrape_date", now)
            loader.add_value("source", "Luxindo Property")
            loader.add_value("availability", "Available")
            loader.add_css("title", "div.properties__info a span::text")
            loader.add_css("image", "div.properties__thumb a img::attr(src)")
            loader.add_value("id", detail.get("REF#", ""))
            loader.add_value("location", detail.get("Location", ""))
            loader.add_value("bedrooms", detail.get("Bedroom", ""))
            loader.add_value("bathrooms", detail.get("Bathroom", ""))
            loader.add_value("land_size", detail.get("Land Size", ""))
            loader.add_value("build_size", detail.get("Building Size", ""))
            price = item.css("div.properties__offer-value strong::text").get()
            if is_idr(price):
                loader.add_value("price", price)
            else:
                loader.add_value("price_usd", price)
            meta = dict(
                loader=loader,
                contract_type=item.css("div.properties__thumb a + span::text").get(),
                property_type=item.css("div.properties__thumb span::text").get(),
            )
            yield response.follow(url, callback=self.parse_detail, meta=meta)
        # go to next url
        next_url = response.css(
            "nav.listing__pagination ul.pagination-custom li:last-child a::attr(href)"
        ).get()
        if next_url:
            yield response.follow(next_url, callback=self.parse)

    def parse_detail(self, response):
        loader = response.meta.get("loader")
        contract_type = response.meta.get("contract_type", "")
        sub_title = response.meta.get("property_type", "")

        loader.selector = response

        loader.add_css("list_date", "script[type='application/ld+json']")
        loader.add_css(
            "description",
            "div.property__description-wrap ::text",
        )
        if "lease" in contract_type:
            ul = response.css("div ul.property__params-list:first-child li")
            loader.add_value("years", get_lease_years(ul))
        loader.add_value("leasehold_freehold", contract_type)
        item = loader.load_item()
        item["leasehold_freehold"] += " " + define_property_type(sub_title)
        
        # get the description
        # description = response.css("div.property__description-wrap ::text").getall()
        # description = list(map(str.strip, description))
        # description = "\n".join()
        # description = item.get("description", description)

        # find the is off plan
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
        )
        if item.get("price", 0) > 0 or item.get("price_usd", 0) > 0:
            yield item
