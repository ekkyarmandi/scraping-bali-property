import scrapy
from scrapy.loader import ItemLoader
from properties import utils
from properties.items import find_lease_years
from properties.property_items.balirealty import BaliRealtyPropertyItem
from datetime import datetime
import re


def find_contract_type(value: str):
    result = re.search(r"leasehold|freehold", value.lower())
    if result:
        return result.group().title()
    return value


def grab_price(price):
    idr = None
    usd = None
    price = price.lower()
    if "idr" in price:
        idr = price
    elif "usd" in price:
        usd = price
    return idr, usd


class BaliRealtySpider(scrapy.Spider):
    name = "balirealty"
    allowed_domains = ["balirealty.com"]
    start_urls = [
        "https://www.balirealty.com/properties/?filter-contract=SALE&filter-location=&filter-property-type=75"
    ]

    def parse(self, response):
        items = response.css("div.content div.row div.property-content-list")
        for item in items:
            url = item.css("h3 a::attr(href)").get()
            d = {}
            details = item.css("div.property-attributes div")
            for div in details:
                key = div.css("p::text").get()
                value = div.css("h4::text").get()
                d.update({key: value})
            price = item.css("div.property-price span::text").get()
            idr, usd = grab_price(price)
            meta = {
                "title": item.css("h3 a::text").get(),
                "price_idr": idr,
                "price_usd": usd,
                "bedrooms": d.get("Bedrooms"),
                "bathrooms": d.get("Bathrooms"),
            }
            yield response.follow(url, callback=self.parse_detail, meta=meta)

        # go to the next url
        next_url = response.css("nav.pagination div a.next::attr(href)").get()
        if next_url:
            yield response.follow(next_url, callback=self.parse)

    def parse_detail(self, response):
        def construct_description(selector, response=response):
            p = response.css(selector).getall()
            p = list(map(str.strip, p))
            p = list(filter(lambda f: f != "", p))
            p = "\n".join(p).strip()
            return p

        i = response.meta

        # get the published date in the script application/ld+json
        script = response.css("script[type='application/ld+json']::text").get()
        result = re.search(r'"datePublished":"(?P<date>[T0-9\-\:\+]+)"', script)
        if result:
            date = result.group("date")
            list_date = datetime.fromisoformat(date).strftime("%m/%d/%y")
        else:
            list_date = ""

        # get property detail information
        details = response.css("div.property-overview ul li")
        d = {}
        for li in details:
            k = li.css("span::text").get()
            v = li.css("strong ::text").getall()
            v = " ".join(list(map(str.strip, v)))
            d.update({k: v})
        availability = "Sold" if d.get("Sold", "") != "No" else "Available"
        contract_type = find_contract_type(d.get("Status"))
        property_type = d.get("Type")

        # get description
        desc = construct_description("div.property-description ::Text")
        lease_years = find_lease_years(desc)

        # grab id from title
        result = re.search(r"(?P<id>\d{3,}$)", i.get("title", ""))
        if result:
            id = result.group("id")
        else:
            id = None

        # assign value into the item loader
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        loader = ItemLoader(item=BaliRealtyPropertyItem(), selector=response)
        loader.add_value("source", "Bali Realty")
        loader.add_value("scrape_date", now)
        loader.add_value("list_date", list_date)
        loader.add_value("availability", availability)
        loader.add_value("property_link", response.url)
        loader.add_value("description", desc)
        loader.add_value("years", lease_years)
        loader.add_value("title", i.get("title"))
        loader.add_css("image", "div.carousel-inner div.item img::attr(data-src)")
        loader.add_value("price", i.get("price_idr"))
        loader.add_value("price_usd", i.get("price_usd"))
        loader.add_value("bedrooms", i.get("bedrooms"))
        loader.add_value("bathrooms", i.get("bathrooms"))
        loader.add_value("id", id)
        loader.add_value("location", d.get("Location"))
        loader.add_value("land_size", d.get("Land Size"))
        loader.add_value("build_size", d.get("Building Size"))
        loader.add_value("leasehold_freehold", [contract_type, property_type])

        item = loader.load_item()

        # find off-plan
        item['is_off_plan'] = utils.find_off_plan(
            item['title'],
            item['description'],
        )

        # filter the entry by price
        idr = item.get("price", 0)
        usd = item.get("price_usd", 0)
        if idr > 0 or usd > 0:
            yield item
