import scrapy
from scrapy.loader import ItemLoader
from properties import utils
from properties.items import define_property_type, find_lease_years
from properties.property_items.lazudi import LazudiPropertyItem
from datetime import datetime
import re


class LazudiSpider(scrapy.Spider):
    name = "lazudi"
    allowed_domains = ["lazudi.com"]
    start_urls = [
        "https://lazudi.com/id-en/properties/for-sale/bali",
    ]

    def parse(self, response):
        urls = response.css("#properties_list a::attr(href)").getall()
        for url in urls:
            yield response.follow(url, callback=self.parse_detail)
        next_page = response.css(
            "#properties_pagination li a[rel*=next]::attr(href)"
        ).get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def property_detail(self, rows):
        def find_number(s):
            return re.search(r"\d+", s).group(0)

        output = {"hold_state": "Leasehold"}
        for row in rows:
            row = row.strip()
            if ":" in row:
                key, value = list(map(str.strip, row.split(":")))
                key = key.lower()
                if key == "created":
                    output[key] = datetime.strptime(value, "%Y-%m-%d").strftime(
                        "%m/%d/%y"
                    )
                else:
                    output[key] = value
            elif "freehold" in row.lower():
                output["hold_state"] = "Freehold"
        return output

    def parse_detail(self, response):
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")

        rows = response.css("div#property_detail div.property-details::text").getall()
        details = self.property_detail(rows)

        loader = ItemLoader(item=LazudiPropertyItem(), selector=response)
        loader.add_value("property_link", response.url)
        loader.add_value("source", "Lazudi")
        loader.add_value("scrape_date", now)
        loader.add_value("list_date", details.get("created", ""))
        loader.add_value("id", details.get("property id", ""))
        loader.add_css("title", "h1")
        loader.add_css("location", "h2 span")
        loader.add_value("leasehold_freehold", details.get("hold_state", "Leasehold"))
        loader.add_css(
            "bedrooms", "div.prop-spec-detail div div:contains(Bed) span ::text"
        )
        loader.add_css(
            "bathrooms", "div.prop-spec-detail div div:contains(Bath) span ::text"
        )
        loader.add_value("land_size", details.get("plot", ""))
        loader.add_value("build_size", details.get("interior", ""))
        loader.add_css("price", "div.prop-detail-price div div:contains(Rp) ::text")
        loader.add_css("image", "#img-0 a::attr(href)")
        loader.add_value("availability", "Available")
        loader.add_css("description", "#property-detail-content ::text")
        item = loader.load_item()
        if "Lease" in item["leasehold_freehold"]:
            item["years"] = find_lease_years(item["description"])
        else:
            item["leasehold_freehold"] = "Freehold"
        property_type = define_property_type(item["title"])
        item["leasehold_freehold"] += " " + property_type

        # check for off-plan
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
        )

        # tolerate the mising beds as long as it's land property
        zero_bedrooms = item.get("bedrooms") == None
        zero_bathrooms = item.get("bathrooms") == None
        is_land = "land" in property_type.lower()
        missing_bed_bath = not is_land and zero_bathrooms and zero_bedrooms

        # look for missing bedrooms
        if zero_bathrooms:
            item["bedrooms"] = utils.search_bedrooms(item["description"])

        # TODO: verify this two block below, make sure it grab the right value on
        # in the description

        # look for missing land_size
        zero_land_size = item.get("land_size") == None
        if zero_land_size:
            item["land_size"] = utils.landsize_extractor(item["description"])

        # look for missing build_size
        zero_build_size = item.get("build_size") == None
        if zero_build_size:
            item["build_size"] = utils.buildsize_extractor(item["description"])

        # check for beds less than 20 and price is positive
        beds = item.get("bedrooms")
        price_not_zero = item.get("price", 0) > 0
        less_beds = type(beds) == int and beds <= 20
        if price_not_zero and less_beds and not missing_bed_bath:
            yield item
