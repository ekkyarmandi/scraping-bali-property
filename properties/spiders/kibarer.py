import scrapy
from scrapy.loader import ItemLoader
from properties.items import KibarerPropertyItem
from datetime import datetime
import re


class KibarerSpider(scrapy.Spider):
    name = "kibarer"
    allowed_domains = ["villabalisale.com"]
    # start_urls = [
    #     "https://www.villabalisale.com/property/villas-for-sale/exclusive-7-bedroom-freehold-real-estate-with-amazing-ocean-ricefield-views-in-cemagi"
    # ]
    start_urls = [
        "https://www.villabalisale.com/search/villas-for-sale/",
        "https://www.villabalisale.com/search/villas-for-rent/",
    ]

    def parse(self, response):
        urls = response.css("#box div.property-item a")
        for url in urls:
            url = url.attrib.get("href")
            if url not in self.start_urls:
                yield response.follow(url, callback=self.parse_detail)
        next_url = response.css("div#pagination ul li a[rel*=next]::attr(href)").get()
        if next_url:
            yield response.follow(next_url, callback=self.parse)

    def get_property_details(self, response, selector):
        def getkey(tr):
            key = tr.css("::text").get().strip()
            key = re.sub(r" ", "_", key).lower()
            key = key.replace(":", "")
            return key

        def getvalue(tr):
            try:
                value = tr.css("strong::text").get()
                return re.sub(r"\s+", " ", value).strip()
            except:
                return ""

        output = {
            getkey(r): getvalue(r)
            for r in response.css(selector)
            if ":" in r.css("::text").get()
        }
        return output

    def parse_detail(self, response):
        now = datetime.now().strftime("%m/%d/%y")
        details = self.get_property_details(
            response, "div.property-description-column.flexbox p"
        )
        status = details.get("status", "")
        location = details.get("location")
        img_info = response.css("div.left-side div.available p").re(r"\d+")
        if location:
            loader = ItemLoader(item=KibarerPropertyItem(), selector=response)
            loader.add_value("property_link", response.url)
            loader.add_value("source", "Kibarer")
            loader.add_value("scrape_date", now)
            loader.add_value("list_date", "")
            loader.add_value("id", details.get("code", ""))
            loader.add_css("title", "h1#property-name")
            loader.add_value("location", location)
            loader.add_value("years", img_info[-1] if "lease" in status else "")
            loader.add_value(
                "leasehold_freehold",
                status,
            )
            loader.add_value("bedrooms", img_info[0])
            loader.add_value("bathrooms", img_info[1])
            loader.add_value(
                "land_size",
                details.get("land_size", ""),
            )
            loader.add_value(
                "build_size",
                details.get("building_size", ""),
            )
            loader.add_css("price", "div.price div.regular-price")
            loader.add_css(
                "image", "div.left-side div.property_detail_slide figure img::attr(src)"
            )
            loader.add_value("availbility", "Available")
            loader.add_css("description", "#property-description-container p")
            yield loader.load_item()
