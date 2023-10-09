import scrapy
import re
from scrapy.loader import ItemLoader
from properties import utils
from properties.items import define_property_type
from properties.property_items.balitreasureproperties import BaliTreasureProperties
from datetime import datetime


def find_page_number(url):
    result = re.search(r"cpage=(?P<cpage>\d+)", url)
    if result:
        return int(result.group("cpage"))
    else:
        return 0


def get_icons(icons):
    details = {}
    for i in icons:
        k = i.split(":")[0].lower().strip().replace(" ", "_")
        v = i.split(":")[-1].lower().strip().replace("m2", "")
        details.update({k: v})
    return details


class BaliTreasurePropertiesSpider(scrapy.Spider):
    name = "balitreasureproperties"
    allowed_domains = ["balitreasureproperties.com"]
    start_urls = [
        "https://balitreasureproperties.com/properties/freehold-leasehold-villa-for-sale/"
    ]
    current_page = 1

    def parse(self, response):
        urls = response.css("div.list-products h2 a::attr(href)").getall()
        for url in urls:
            yield response.follow(url, callback=self.parse_detail)
        # go to next page
        pagination = set(response.css("a.prev.page-numbers::attr(href)").getall())
        for p in pagination:
            page_number = find_page_number(p)
            if page_number > self.current_page:
                self.current_page = page_number
                yield scrapy.Request(p, callback=self.parse)

    def parse_detail(self, response):
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        has_leasehold = lambda strs: any(["lease" in str.lower() for str in strs])
        contract_types = response.css(".second_line a[rel*=property_id]::text").getall()
        icons = get_icons(
            response.css(
                "div.p-property div.le_icons div.facility_icons::attr(title)"
            ).getall()
        )

        loader = ItemLoader(item=BaliTreasureProperties(), selector=response)
        if has_leasehold(contract_types):
            loader.add_value("leasehold_freehold", "Leasehold")
            loader.add_css(
                "years",
                ".price_part span:contains(Years)::text,.price_part span:contains(years)::text",
            )
            loader.add_css(
                "price",
                ".price_part .price span.show_curency_IDR.show_type_Lease::text",
            )
            loader.add_css(
                "price_usd",
                ".price_part .price span.show_curency_USD.show_type_Lease::text",
            )
        else:
            loader.add_value("leasehold_freehold", "Freehold")
            loader.add_css(
                "price",
                ".price_part .price span.show_curency_IDR.show_type_Sale::text",
            )
            loader.add_css(
                "price_usd",
                ".price_part .price span.show_curency_USD.show_type_Sale::text",
            )

        # get the first value from bedrooms with "+"
        bedrooms = icons.get("bedrooms", "")
        if "+" in bedrooms:
            bedrooms = bedrooms.split("+")[0]

        loader.add_value("source", "Bali Treasure Properties")
        loader.add_value("property_link", response.url)
        loader.add_value("scrape_date", now)
        loader.add_css("id", "div.p-property span.leCode strong")
        loader.add_css("title", "h1")
        loader.add_css("location", "div.p-property h1 + span.area strong")
        loader.add_value("bedrooms", bedrooms)
        loader.add_value("bathrooms", icons.get("bathrooms", ""))
        loader.add_value("land_size", icons.get("land_size", ""))
        loader.add_css(
            "image",
            "div.p-property div.images_container div div:first-child::attr(style)",
        )
        loader.add_css("availability", "div.second_line div.availability strong")
        loader.add_css(
            "description", "div#goto-highlight div.property-description ::text"
        )
        item = loader.load_item()
        labels = response.css("div.second_line div.availability strong::text").getall()
        labels = list(filter(lambda str: str != "", map(str.strip, labels)))
        item["leasehold_freehold"] += " " + define_property_type(item["title"])
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
            labels,
        )
        yield item
