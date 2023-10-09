import scrapy

from scrapy.loader import ItemLoader
from datetime import datetime
import re
from properties import utils

from properties.property_items.gillesdemunter import GillesDemunterPropertyItem


class GillesdemunterSpider(scrapy.Spider):
    name = "gillesdemunter"
    allowed_domains = ["gillesdemunter.com"]
    start_urls = [
        f"https://www.gillesdemunter.com/properties.sale.list.php?search=search&p={p}"
        for p in range(1, 29)
    ]

    def parse(self, response):
        items = response.css(".container-fluid div.container div.item:has(h2.desktop)")
        for item in items:
            url = item.css("a::attr(href)").get()
            url = response.urljoin(url)
            loader = ItemLoader(item=GillesDemunterPropertyItem(), selector=item)
            is_private = item.css(".container-caption h3::text").get()
            if not is_private:
                bed, bath = (
                    item.css(
                        "div.container-caption div.row div:contains(BED) span::text"
                    )
                    .get()
                    .split("/")
                )
                contract_type = item.css(
                    "div.container-caption div.row div:contains(OWNERSHIP) span::text"
                ).get()
                loader.add_css("title", "h2 a::text")
                loader.add_css("location", "h3::text")
                loader.add_css("image", "div.container-caption > img::attr(src)")
                loader.add_css(
                    "land_size", "div.container-caption div.row div:contains(LAND) span"
                )
                loader.add_css(
                    "build_size",
                    "div.container-caption div.row div:contains(LIVING) span",
                )
                loader.add_css(
                    "price_usd",
                    "div.container-caption div.row div:contains(\$) span::text",
                )
                loader.add_value("leasehold_freehold", [contract_type, "Villa"])
                loader.add_value("bedrooms", bed)
                loader.add_value("bathrooms", bath)
                loader.add_value("property_link", url)
                loader.add_value("availability", "Available")
                meta = dict(loader=loader)
                yield response.follow(url, callback=self.parse_detail, meta=meta)

    def parse_detail(self, response):
        i = response.meta
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        _id = re.search(r"id=(?P<id>\d+)", response.url).group("id")
        loader = i.get("loader")
        loader.selector = response
        loader.add_value("source", "GD&ASSOCIATES")
        loader.add_value("scrape_date", now)
        loader.add_value("id", _id)
        loader.add_css("years", ".price span:contains(years)::text")
        loader.add_css("description", "div[class*=col] p.font3.f12::text")
        item = loader.load_item()
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
        )
        if item.get("price_usd", 0) > 0:
            yield item
