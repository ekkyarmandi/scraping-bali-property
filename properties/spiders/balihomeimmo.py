import scrapy
from scrapy.loader import ItemLoader
from properties.items import HomeImmoPropertyItem
from datetime import datetime


class BalihomeimmoSpider(scrapy.Spider):
    name = "balihomeimmo"
    allowed_domains = ["bali-home-immo.com"]
    start_urls = ["https://bali-home-immo.com/realestate-property/for-sale/villa"]

    def parse(self, response):
        # get all property urls
        urls = response.css(
            "div.properties-holder div.property-item div.top-desc a::attr(href)"
        ).getall()
        for url in urls:
            yield response.follow(url, callback=self.parse_detail)
        # next page
        if len(urls) > 0:
            if "?page" not in response.url:
                next_url = response.url + "?page=2"
            else:
                page = int(response.url.split("=")[-1])
                next_url = response.url.replace(f"page={page}", f"page={page+1}")
            yield scrapy.Request(next_url, callback=self.parse)

    def parse_detail(self, response):
        now = datetime.now().strftime("%m/%d/%y")

        table = response.css(".property-list-item-for-details table tr")
        details = {}
        for tr in table:
            key = tr.css("td:first-child::text").get().lower().replace(" ", "_")
            value = tr.css("td:nth-child(3)::text").get()
            details.update({key: value})

        beds = details.get("bedroom", "")
        baths = details.get("bathroom", "")
        land_size = details.get("land_size", "")
        build_size = details.get("building_size", "")
        leashold_period = details.get("leasehold_period", "")

        prop_id = response.css("button[data-property-id]").attrib.get(
            "data-property-id", ""
        )

        loader = ItemLoader(item=HomeImmoPropertyItem(), selector=response)
        loader.add_value("property_link", response.url)
        loader.add_value("source", "Bali Home Immo")
        loader.add_value("scrape_date", now)
        loader.add_value("list_date", "")
        loader.add_value("id", prop_id)
        loader.add_css("title", "h2.title")
        loader.add_css("location", "div.property-price span")
        loader.add_value("years", leashold_period)
        loader.add_css(
            "leasehold_freehold",
            "div.property-list-item-for-details::attr(data-price-category)",
        )
        loader.add_value("bedrooms", beds)
        loader.add_value("bathrooms", baths)
        loader.add_value("land_size", land_size)
        loader.add_value("build_size", build_size)
        loader.add_css("price", "#price-selector span")
        loader.add_css("image", "div.swiper-slide img::attr(src)")
        loader.add_value("availbility", "Available")
        loader.add_css("description", "div.property-info-desc")
        yield loader.load_item()
