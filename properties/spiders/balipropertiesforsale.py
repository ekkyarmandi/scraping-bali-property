import scrapy
import urllib.parse
from scrapy.loader import ItemLoader
from itemloaders.processors import MapCompose
from properties import utils
from properties.items import PropertyItem, dimension_remover, find_lease_years
from datetime import datetime
from math import ceil
import html2text

md_converter = html2text.HTML2Text()


def url(page_num):
    params = {
        "page": page_num,
        "posts_per_page": 12,
        "search_by_id": True,
        "sortby": "a_price",
        "status[0]": "leasehold",
        "touched": False,
        "type[0]": "Villa",
    }
    query_string = urllib.parse.urlencode(params)
    return (
        "https://balipropertiesforsale.com/wp-json/properties/v1/list/?" + query_string
    )


def to_mmddyy(str):
    input_datetime = datetime.strptime(str, "%Y-%m-%d %H:%M:%S")
    return input_datetime.strftime("%m/%d/%y")


class BalipropertiesforsaleSpider(scrapy.Spider):
    name = "balipropertiesforsale"
    allowed_domains = ["balipropertiesforsale.com"]
    start_urls = [url(1)]
    visited = []

    def parse(self, response):
        # get the json response
        try:
            data = response.json()
        except:
            data = {}
        # iterate the property data
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        urljoin = lambda str: f"https://balipropertiesforsale.com/property/{str}/"
        items = data.get("results")
        for i in items:
            contract_type = i["overlay"]["property_status"]
            property_type = i["overlay"]["property_type"]
            desc = md_converter.handle(i["post"]["post_content"])
            loader = ItemLoader(item=PropertyItem(), selector=i)
            loader.add_value("source", "Bali Properties for Sale")
            loader.add_value("scrape_date", now)
            loader.add_value("list_date", i["post"]["post_date"], MapCompose(to_mmddyy))
            loader.add_value("title", i["post"]["post_title"])
            loader.add_value("id", i["overlay"]["property_id"])
            loader.add_value("price", i["overlay"]["prices"]["IDR"]["price"])
            loader.add_value("price_usd", i["overlay"]["prices"]["USD"]["price"])
            loader.add_value(
                "image", i["overlay"]["images"][0], MapCompose(dimension_remover)
            )
            loader.add_value("location", i["overlay"]["area"])
            loader.add_value("land_size", i["overlay"]["area_size"])
            loader.add_value("build_size", i["overlay"]["building_size"])
            loader.add_value("bedrooms", i["overlay"]["bedrooms"])
            loader.add_value("bathrooms", i["overlay"]["bathrooms"])
            loader.add_value(
                "availability", "Sold" if i["overlay"]["is_sold"] else "Available"
            )
            loader.add_value("leasehold_freehold", [contract_type, property_type])
            loader.add_value("property_link", urljoin(i["post"]["post_name"]))
            loader.add_value("description", desc)
            loader.add_value("years", desc, MapCompose(find_lease_years))
            item = loader.load_item()

            labels = i["overlay"]["labels"]["labels"]
            labels = [l["label"]["name"] for l in labels]
            item["is_off_plan"] = utils.find_off_plan(
                item["title"],
                item["description"],
                labels,
            )
            yield item

        # go to next url
        count = data.get("count", 1)
        max_page = ceil(count / 12)
        for i in range(2, max_page + 1):
            next_url = url(i)
            if next_url not in self.visited:
                self.visited.append(next_url)
                yield response.follow(next_url, callback=self.parse)
