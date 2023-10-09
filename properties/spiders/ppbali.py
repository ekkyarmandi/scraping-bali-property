import scrapy
from scrapy.loader import ItemLoader
from datetime import datetime
from properties import utils
from properties.items import get_lease_years
from properties.property_items.ppbali import ParadisePropertyItem
from pprint import pprint
import re


class PpbaliSpider(scrapy.Spider):
    name = "ppbali"
    allowed_domains = ["ppbali.com"]
    start_urls = [
        "https://ppbali.com/search-result/?ref_id=&property_title=&property_type=villa",
        "https://ppbali.com/search-result/page/2/?ref_id&property_title&property_type=villa",
        "https://ppbali.com/search-result/page/3/?ref_id&property_title&property_type=villa",
        "https://ppbali.com/search-result/page/4/?ref_id&property_title&property_type=villa",
        "https://ppbali.com/search-result/page/5/?ref_id&property_title&property_type=villa",
        "https://ppbali.com/search-result/page/6/?ref_id&property_title&property_type=villa",
        "https://ppbali.com/search-result/page/7/?ref_id&property_title&property_type=villa",
        "https://ppbali.com/search-result/page/8/?ref_id&property_title&property_type=villa",
    ]

    def parse(self, response):
        # collect the property items
        items = response.css("div.box-result")
        for item in items:
            url = item.css("h4 a::attr(href)").get()
            d = {}
            strip_join = lambda l: " ".join(list(map(str.strip, l))).strip()
            for i in item.css("div.listing-details > div[class^=col]"):
                key = i.css("div:nth-child(2)::text").getall()
                key = strip_join(key)
                if "price" in key.lower():
                    div = i.css("div:nth-child(3)")
                    price = ["price_usd", "price_idr"]
                    for key in price:
                        value = div.css(f"span::attr(data-{key})").get()
                        d.update({key: value})
                else:
                    value = i.css("div:nth-child(3)::text").getall()
                    value = strip_join(value)
                    if key != "" and value != "":
                        d.update({key: value})
            # print("DETAILS")
            # pprint(d)
            meta = {
                "id": d.get("Ref.ID"),
                "title": item.css("h4 a::text").get(),
                "image": item.css("div.imgwrap img::attr(src)").get(),
                "location": d.get("Location"),
                "land_size": d.get("Land size"),
                "build_size": d.get("Built size"),
                "contract_type": d.get("Status"),
                "bedrooms": d.get("Bedrooms"),
                "price_idr": d.get("price_idr"),
                "price_usd": d.get("price_usd"),
            }
            contract_type = meta.get("contract_type")
            if contract_type and "hold" in contract_type.lower():
                yield response.follow(url, callback=self.parse_detail, meta=meta)

    def parse_detail(self, response):
        i = response.meta

        # contract_type
        contract_type = i.get("contract_type")
        property_type = "Villa"
        result = re.search(r"\w+hold", contract_type)
        if result:
            contract_type = result.group().title()

        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        loader = ItemLoader(item=ParadisePropertyItem(), selector=response)
        loader.add_value("source", "Paradise Property Group")
        loader.add_value("availability", "Available")
        loader.add_value("property_link", response.url)
        loader.add_value("scrape_date", now)
        loader.add_value("title", i.get("title"))
        loader.add_value("image", i.get("image"))
        loader.add_value("id", i.get("id"))
        loader.add_value("location", i.get("location"))
        loader.add_value("bedrooms", i.get("bedrooms"))
        loader.add_value("land_size", i.get("land_size"))
        loader.add_value("build_size", i.get("build_size"))
        loader.add_value("price", i.get("price_idr"))
        loader.add_value("price_usd", i.get("price_usd"))
        loader.add_value("leasehold_freehold", [contract_type, property_type])
        loader.add_css("description", "div.maincol p[class!=breadcrumbs]")

        # bathrooms
        b = {}
        table = response.css("#mainwrapper table tr")
        for j in range(len(table)):
            key = table[1].css(f"td:nth-child({j+1})::text").get()
            value = table[0].css(f"td:nth-child({j+1}) strong::text").get()
            b.update({key: value})
        loader.add_value("bathrooms", b.get("Baths"))

        # years
        status = response.css("div.quick-facts ul li:contains(Status)::text").get()
        if not status:
            status = ""
        years = get_lease_years(status)
        loader.add_value("years", years)

        # list_date
        c = {}
        sidecol = response.css("div.sidecol ul li")
        for li in sidecol:
            key, value = li.css("::text").getall()
            if key:
                key = key.replace(":", "")
                c.update({key: value})
        avail_date = c.get("Date Available", "").strip()
        if avail_date != "":
            try:
                date = datetime.strptime(avail_date, "%d %B %Y")
                loader.add_value("list_date", date.strftime("%m/%d/%y"))
            except ValueError:
                raise ValueError(
                    f"Date Available '{avail_date}' format does not match format %d %B %Y"
                )
        item = loader.load_item()

        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
        )
        if item.get("price", 0) > 500000000:  # more than Rp 500,000,000
            yield item
