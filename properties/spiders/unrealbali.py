import scrapy
from datetime import datetime
from scrapy.loader import ItemLoader
from properties import utils
from properties.items import UnrealBaliPorpertyItem, to_number
import re


class UnrealbaliSpider(scrapy.Spider):
    name = "unrealbali"
    allowed_domains = ["unrealbali.com"]
    start_urls = [
        "https://www.unrealbali.com/search-results/?location%5B%5D=&status%5B%5D=&type%5B%5D=villa&max-price="
    ]

    def parse(self, response):
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        items = response.css("div.item-wrap")
        for item in items:
            url = item.css("div.item-body h2.item-title a::attr(href)").get()

            loader = ItemLoader(item=UnrealBaliPorpertyItem(), selector=item)
            loader.add_value("property_link", url)
            loader.add_value("scrape_date", now)
            loader.add_value("source", "Unreal Bali")
            loader.add_css("id", "ul li.h-property-id span.hz-figure::text")
            loader.add_css("title", "div.item-body h2.item-title a::text")
            loader.add_css("location", "div.item-body address::text")
            loader.add_css("build_size", "ul li.h-area span.hz-figure::text")
            loader.add_css("land_size", "ul li.h-land-area span::text")
            loader.add_css("price_usd", "div.item-header ul li.item-price::text")
            age = item.css("div.item-footer div.item-date::text").getall()
            age = list(filter(lambda str: str.strip() != "", age))
            prop_type = item.css("ul li.h-type span::text").get()
            yield response.follow(
                url,
                callback=self.parse_detail,
                meta=dict(
                    loader=loader,
                    age=age,
                    prop_type=prop_type,
                ),
            )

    def parse_detail(self, response):
        def find_hold_state(response=response, selector: str = ""):
            lowercase = lambda tag: re.sub("\s+", "", tag).lower().strip()
            tags = response.css(selector).getall()
            tags = list(map(lowercase, tags))
            is_leasehold = any(list(map(lambda t: "lease" in t, tags)))
            is_sold = any(list(map(lambda t: "sold" in t, tags)))
            return is_leasehold, is_sold

        def grab_first(selector, css):
            try:
                first = selector.css(css).get()
                if "/" in first:
                    return first.split("/")[0]
                elif "-" in first:
                    return first.split("-")[0]
                return first
            except:
                result = selector.css(css)
                if len(result) > 0:
                    return result.group()
                else:
                    return None

        loader = response.meta.get("loader", {})
        loader.selector = response
        prop_type = response.meta.get("prop_type", "")
        is_leasehold, is_sold = find_hold_state(
            selector="div.property-labels-wrap > ::text"
        )
        state_hold = "Leasehold" if is_leasehold else "Freehold"
        availbility = "Available" if not is_sold else "Sold"
        bedrooms = grab_first(
            response,
            "div.property-overview-data ul li i.icon-hotel-double-bed-1 + strong::text",
        )

        bathrooms = grab_first(
            response,
            "div.property-overview-data ul li i.icon-bathroom-shower-1 + strong::text",
        )
        loader.add_value("list_date", response.meta.get("age"))
        loader.add_css(
            "years", "div.property-overview-data ul li i.icon-calendar-3 + strong"
        )
        loader.add_value("leasehold_freehold", " ".join([state_hold, prop_type]))
        loader.add_value("bedrooms", bedrooms)
        loader.add_value("bathrooms", bathrooms)
        loader.add_css("image", "div.property-banner div.row img::attr(src)")
        loader.add_value("availability", availbility)
        loader.add_css("description", "div.block-content-wrap p")
        item = loader.load_item()

        labels = response.css("div.property-labels-wrap > ::text").getall()
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
            labels,
        )
        yield item
