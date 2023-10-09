from math import ceil
import scrapy
from scrapy.loader import ItemLoader
from properties import utils
from properties.property_items.balipropertydirect import BaliPropertyDirectItem
from datetime import datetime
from pprint import pprint
import re


class BalipropertydirectSpider(scrapy.Spider):
    name = "balipropertydirect"
    allowed_domains = ["balipropertydirect.com"]
    start_urls = [
        "https://balipropertydirect.com/wp-admin/admin-ajax.php?type%5B%5D=villa&houzez_save_search_ajax=7ed0bab2d4&action=houzez_half_map_listings&paged=0&sortby=a_date&item_layout=v1"
    ]
    current_page = 0

    def parse(self, response):
        try:
            data = response.json()
        except:
            data = {}
        properties = data.get("properties", [])
        for prop in properties:
            url = prop.get("url")
            location = prop.get("address", "")
            loader = ItemLoader(item=BaliPropertyDirectItem(), selector=response)
            loader.add_value("property_link", url)
            loader.add_value("id", f'BPD-{prop.get("property_id")}')
            loader.add_value("title", prop.get("title"))
            loader.add_value("image", prop.get("thumbnail"))
            loader.add_value("price", prop.get("pricePin"))
            loader.add_value("location", location)
            meta = {
                "loader": loader,
                "property_type": prop.get("property_type"),
            }
            yield response.follow(url, callback=self.parse_detail, meta=meta)

        # go to next url
        total_properties = data.get("total_results", 0)
        max_page = (
            ceil(total_properties / len(properties)) if total_properties > 0 else 1
        )
        if self.current_page <= max_page:
            prev_page = self.current_page
            if self.current_page == 0:
                self.current_page += 2
            else:
                self.current_page += 1
            next_url = response.url.replace(
                f"paged={prev_page}", f"paged={self.current_page}"
            )
            yield response.follow(next_url, callback=self.parse)

    def parse_detail(self, response):
        i = response.meta
        # get the published date in the script application/ld+json
        script = response.css("script[type='application/ld+json']::text").get()
        result = re.search(r'"datePublished":"(?P<date>[T0-9\-\:\+]+)"', script)
        if result:
            date = result.group("date")
            list_date = datetime.fromisoformat(date).strftime("%m/%d/%y")
        else:
            list_date = ""

        # get property details
        d = {}
        tokey = lambda str: str.lower().strip().replace(" ", "_")
        details = response.css("#property-detail-wrap .detail-wrap ul > li")
        for li in details:
            key = li.css("strong::Text").get().replace(":", "")
            if "bedroom" in key:
                key = "bedrooms"
            elif "bathroom" in key:
                key = "bathrooms"
            value = li.css("span::Text").get()
            d.update({tokey(key): value})

        contract_type = d.get("property_status", "")
        property_type = i.get("property_type")

        loader = i.get("loader")
        loader.selector = response
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        loader.add_value("source", "Bali Property Direct")
        loader.add_value("availability", "Available")
        loader.add_value("scrape_date", now)
        loader.add_value("list_date", list_date)
        loader.add_value("land_size", d.get("land_area"))
        loader.add_value("build_size", d.get("floor_space"))
        loader.add_value("bedrooms", d.get("bedrooms", ""))
        loader.add_value("bathrooms", d.get("bathrooms", ""))
        loader.add_value("leasehold_freehold", [contract_type, property_type])
        loader.add_value("years", d.get("lease_duration", ""))
        loader.add_css(
            "description", "#property-description-wrap .block-content-wrap ::Text"
        )
        # price_usd
        item = loader.load_item()
        item['is_off_plan'] = utils.find_off_plan(
            item['title'],
            item['description'],
        )
        yield item
