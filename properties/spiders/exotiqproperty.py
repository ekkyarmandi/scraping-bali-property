import scrapy
from scrapy.loader import ItemLoader
from datetime import datetime
from properties import utils
from properties.property_items.exotiqproperty import ExotiqPropertyItem
import re


class ExotiqpropertySpider(scrapy.Spider):
    name = "exotiqproperty"
    allowed_domains = ["exotiqproperty.com"]
    start_urls = ["https://www.exotiqproperty.com/villas-for-sale/bali"]

    def parse(self, response):
        # collect the items and pass the metadata
        items = response.css("div[role=list] div[role=listitem].listing_item")
        for item in items:
            url = item.css("a::attr(href)").get()
            meta = {
                "id": item.css("div.listing-id::text").get(),
                "title": item.css("h4::text").get(),
                "image": item.css("img::attr(src)").get(),
                "location": item.css("div.listing-location_wrapper div::text").get(),
                "land_size": item.css(
                    "div[fs-cmsfilter-field=building-size]::text"
                ).get(),
                "build_size": item.css("div[fs-cmsfilter-field=land-size]::text").get(),
                "bedrooms": item.css("div[fs-cmsfilter-field=bedrooms]::text").get(),
                "bathrooms": item.css("div[fs-cmsfilter-field=bathrooms]::text").get(),
                "contract_type": item.css("div.price_item div:first-child::text").get(),
                "price": item.css("div.price_item span::text").get(),
            }
            yield response.follow(
                response.urljoin(url), callback=self.parse_detail, meta=meta
            )

    def parse_detail(self, response):
        i = response.meta
        contract_type = i.get("contract_type", "")
        property_type = response.css(
            'div.info_title:contains("Type of property") + div::text'
        ).get()

        # grab lease years
        lease_years = ""
        if "lease" in contract_type.lower():
            result = re.search(r"\d{2}", contract_type)
            lease_years = result.group(0)
            contract_type = "Leasehold"

        # assign data into item loader
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        loader = ItemLoader(item=ExotiqPropertyItem(), selector=response)
        loader.add_value("scrape_date", now)
        loader.add_value("source", "Exotiq Property")
        loader.add_value("property_link", response.url)
        loader.add_value("leasehold_freehold", [contract_type, property_type])
        loader.add_value("years", lease_years)
        loader.add_value("availability", "Available")
        loader.add_value("id", i.get("id"))
        # loader.add_value("list_date", "")
        loader.add_value("title", i.get("title"))
        loader.add_value("location", i.get("location"))
        loader.add_value("bedrooms", i.get("bedrooms"))
        loader.add_value("bathrooms", i.get("bathrooms"))
        loader.add_value("land_size", i.get("land_size"))
        loader.add_value("price", i.get("price"))
        loader.add_value("build_size", i.get("build_size"))
        # loader.add_value("price_usd", "")
        loader.add_value("image", i.get("image"))
        loader.add_css("description", "div.listing_description p")
        # filter the item by price
        item = loader.load_item()

        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
        )
        if item["price"] > 0:
            yield item
