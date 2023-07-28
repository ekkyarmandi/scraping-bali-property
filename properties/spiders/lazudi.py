import scrapy
from scrapy.loader import ItemLoader
from properties.items import LazudiPropertyItem
from datetime import datetime
import re


class LazudiSpider(scrapy.Spider):
    name = "lazudi"
    allowed_domains = ["lazudi.com"]
    start_urls = [
        "https://lazudi.com/id-en/properties/for-sale/bali",
        "https://lazudi.com/id-en/properties/for-rent/bali"
    ]
    # start_urls = ["https://lazudi.com/id-en/tabanan/property/huge-price-reduction-!!!-17073"]

    def parse(self, response):
        urls = response.css("#properties_list a::attr(href)").getall()
        for url in urls:
            yield response.follow(url, callback=self.parse_detail)
        next_page = response.css(
            "#properties_pagination li a[rel*=next]::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def property_detail(self, rows):
        def find_number(s): return re.search(r"\d+", s).group(0)
        output = {
            "hold_state": "Leasehold"
        }
        for row in rows:
            row = row.strip()
            if ":" in row:
                key, value = list(map(str.strip, row.split(":")))
                key = key.lower()
                if key == "created":
                    output[key] = datetime.strptime(
                        value, "%Y-%m-%d").strftime("%m/%d/%y")
                elif key == "year built":
                    output['age'] = 2023 - int(value)
                else:
                    output[key] = value
            elif "beds" in row.lower():
                output['bedrooms'] = find_number(row)
            elif "baths" in row.lower():
                output['bathrooms'] = find_number(row)
            elif "freehold" in row.lower():
                output['hold_state'] = "Freehold"
        return output

    def parse_detail(self, response):
        now = datetime.now().strftime("%m/%d/%y")

        rows = response.css(
            "div#property_detail div.property-details::text").getall()
        details = self.property_detail(rows)

        loader = ItemLoader(item=LazudiPropertyItem(), selector=response)
        loader.add_value("property_link", response.url)
        loader.add_value("source", "Lazudi")
        loader.add_value("scrape_date", now)
        loader.add_value("list_date", details.get("created", ""))
        loader.add_value("id", details.get("property id", ""))
        loader.add_css("title", "h1")
        loader.add_css("location", "h2 span")
        loader.add_value("years", details.get("age", ""))
        loader.add_value("leasehold_freehold",
                         details.get("hold_state", "Leasehold"))
        loader.add_value("bedrooms", details.get("bedrooms", ""))
        loader.add_value("bathrooms", details.get("bathrooms", ""))
        loader.add_value("land_size", details.get("interior", ""))
        loader.add_value("build_size", details.get("plot", ""))
        loader.add_css("price", "div.prop-detail-price div div:contains(Rp)")
        loader.add_css("image", "#img-0 a::attr(href)")
        loader.add_value("availbility", "Available")
        loader.add_css("description", "div#property-detail-content p")
        yield loader.load_item()
