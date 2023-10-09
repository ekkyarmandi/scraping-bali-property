import scrapy
from scrapy.loader import ItemLoader
from datetime import datetime
from properties import utils
from properties.items import dimension_remover, find_lease_years, get_uploaded_date
from properties.property_items.svahaproperty import SvahaPropertyItem
import re


class SvahaPropertySpider(scrapy.Spider):
    name = "svahaproperty"
    allowed_domains = ["svahaproperty.com"]
    start_urls = [
        "https://www.svahaproperty.com/listing-category/villa/page/1/?s&filters%5Bad_type%5D=sell"
    ]

    def parse(self, response):
        # collect the items
        items = response.css("div.listing-item")
        for item in items:
            url = item.css("h3 a::attr(href)").get()
            loader = ItemLoader(item=SvahaPropertyItem(), selector=item)
            loader.add_css("title", "h3.item-title ::text")
            loader.add_css("location", "ul.entry-meta li::text")
            loader.add_css("image", "div.product-thumb img::attr(src)")
            loader.add_css("list_date", "div.product-thumb img::attr(src)")
            meta = dict(
                loader=loader,
                price=item.css("div.product-price span ::text").getall(),
                property_type=item.css("div.property-category a::text").get(),
            )
            yield response.follow(url, callback=self.parse_detail, meta=meta)

        # pagination
        next_url = response.css("nav.rtcl-pagination ul li a.next::attr(href)").get()
        if next_url:
            yield response.follow(next_url, callback=self.parse)

    def parse_detail(self, response):
        i = response.meta
        loader = i.get("loader")
        loader.selector = response

        # get property details
        d = {}
        details = response.css("div.product-details ul li")
        remove_bracket = lambda str: re.sub(r"\((.*)\)", "", str)
        for li in details:
            key = li.css("span:first-child::text").get().strip()
            value = li.css("span:nth-child(2)::text").get().strip()
            d.update({remove_bracket(key): value})

        contract_type = d.get("Status", "")
        property_type = d.get("Type", "")

        # assign data into item loader
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        loader.add_value("property_link", response.url)
        loader.add_value("scrape_date", now)
        loader.add_value("source", "Svaha Property")
        loader.add_value("availability", "Available")
        loader.add_value("price", "".join(i.get("price", [])))
        loader.add_value("leasehold_freehold", [contract_type, property_type])
        loader.add_value("id", d.get("Villa ID"))
        loader.add_value("bedrooms", d.get("Bedroom"))
        loader.add_value("bathrooms", d.get("Bath"))
        loader.add_value("land_size", d.get("Land"))
        loader.add_value("build_size", d.get("Building"))
        loader.add_css("years", "div.product-description p::Text")
        loader.add_css("description", "div.product-description p::Text")

        item = loader.load_item()

        # find is it off-plan proerty
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
        )
        # filter the item by price
        if item["price"] > 0:
            yield item
