import scrapy
from scrapy.loader import ItemLoader
from properties import utils
from properties.items import get_lease_years

from properties.property_items.heritagebali import HeritageBaliPropertyItem
from datetime import datetime
import re


class HeritageBaliSpider(scrapy.Spider):
    name = "heritagebali"
    allowed_domains = ["heritagebali.com"]
    start_urls = ["https://www.heritagebali.com/property-listing/villas"]

    def parse(self, response):
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        # collect property items
        items = response.css(".property_listing")
        for item in items:
            url = item.css("h4 a::attr(href)").get()
            loader = ItemLoader(item=HeritageBaliPropertyItem(), selector=item)
            loader.add_value("source", "Heritage Bali")
            loader.add_value("property_link", url)
            loader.add_value("scrape_date", now)
            loader.add_value("availability", "Available")
            loader.add_css("title", "h4 a::text")
            yield response.follow(
                url, callback=self.parse_detail, meta=dict(loader=loader)
            )

        # go to the next url
        next_url = response.css("ul.pagination li.roundright a::attr(href)").get()
        if next_url and next_url != response.url:
            yield response.follow(next_url, callback=self.parse)

    def parse_detail(self, response):
        i = response.meta

        # get price and lease years
        price = response.css('div.listing_detail:contains("Price") ::text').getall()
        is_leasehold = False
        if len(price) > 2:
            is_leasehold = "lease" in price[-1].lower()

        contract_type = "Leasehold" if is_leasehold else "Freehold"

        loader = i.get("loader")
        loader.selector = response
        loader.add_css("id", "#propertyid_display ::text")
        loader.add_css("bathrooms", 'div.listing_detail:contains("Bathrooms") ::text')
        loader.add_css("bedrooms", 'div.listing_detail:contains("Bedrooms") ::text')
        loader.add_value("price", price[1] if len(price) > 0 else "")
        loader.add_value("years", price[-1] if len(price) > 0 else "")
        loader.add_css(
            "land_size", 'div.listing_detail:contains("Property Lot Size") ::text'
        )
        loader.add_css(
            "build_size", 'div.listing_detail:contains("Property Size") ::text'
        )
        loader.add_css("description", ".property_custom_detail_wrapper ::text")
        loader.add_value("leasehold_freehold", [contract_type, "Villa"])
        loader.add_css("image", ".carousel-inner img::attr(src)")
        loader.add_css(
            "location",
            '.wpestate_estate_property_design_intext_details:contains("Bali") a:last-child::text',
        )
        item = loader.load_item()
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
        )
        if item.get("price", 0) > 0:
            yield item
