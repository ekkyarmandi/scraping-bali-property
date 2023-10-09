import scrapy
from scrapy.loader import ItemLoader
from datetime import datetime
import re
from properties import utils
from properties.items import find_lease_years, get_lease_years

from properties.property_items.rajavillaproperty import RajaVillaPropertyItem


class RajaVillaPropertySpider(scrapy.Spider):
    name = "rajavillaproperty"
    allowed_domains = ["rajavillaproperty.com"]
    start_urls = ["https://rajavillaproperty.com/villa-for-sale/"]

    def parse(self, response):
        # target = [
        # ]
        items = response.css("#main div.col-property-box")
        for item in items:
            url = item.css("h3 a::attr(href)").get()
            # if url not in target:
            #     continue
            loader = ItemLoader(item=RajaVillaPropertyItem(), selector=item)
            loader.add_value("property_link", url)
            loader.add_css("title", "h3 a::text")
            loader.add_css("id", ".property-code::text")
            loader.add_css(
                "bedrooms",
                '.property-box-meta div:contains("Bedroom").field-item span::text',
            )
            loader.add_css(
                "bathrooms",
                '.property-box-meta div:contains("Bathroom").field-item span::text',
            )
            loader.add_css("location", ".property-row-location a::text")
            loader.add_css("price_usd", ".property-box-price::text")
            yield response.follow(
                url, callback=self.parse_detail, meta=dict(loader=loader)
            )
        # go to next page
        next_url = response.css("nav.pagination a.next::attr(href)").get()
        if next_url:
            yield response.follow(next_url, callback=self.parse)

    def parse_detail(self, response):
        i = response.meta
        title = response.css("h1::text").get()
        if "leasehold" in title.lower():
            contract_type = "Leasehold"
        else:
            contract_type = "Freehold"

        # get the published date in the script application/ld+json
        script = response.css("script[type='application/ld+json']::text").get()
        result = re.search(r'"datePublished":"(?P<date>[T0-9\-\:\+]+)"', script)
        if result:
            date = result.group("date")
            list_date = datetime.fromisoformat(date).strftime("%m/%d/%y")
        else:
            list_date = ""

        years = response.css(
            '.property-overview li:contains("Lease Period")::text'
        ).get()
        desc = (
            response.css(".property-description").css("p ::text, div ::text").getall()
        )

        price_tag = response.css("div.price::text").get()
        if price_tag:
            lease_years = get_lease_years(price_tag)

        if not lease_years and years:
            lease_years = get_lease_years(years)

        if not lease_years:
            desc = "\n".join(list(map(str.strip, desc)))
            lease_years = find_lease_years(desc)

        # check property availability
        labels = response.css(".property-gallery .property-badge::text").getall()
        availability = utils.find_sold_out(labels)

        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        loader = i.get("loader")
        loader.selector = response
        loader.add_value("source", "Raja Villa Property")
        loader.add_value("scrape_date", now)
        loader.add_value("list_date", list_date)
        loader.add_value("leasehold_freehold", [contract_type, "Villa"])
        loader.add_css(
            "build_size", '.property-overview li:contains("Home area")::text'
        )
        loader.add_css("land_size", '.property-overview li:contains("Lot area")::text')
        loader.add_css("image", "div.property-gallery-preview-owl img::attr(src)")
        loader.add_value("availability", availability)
        loader.add_value("years", lease_years)
        loader.add_value("description", desc)
        item = loader.load_item()

        # find off-plan
        item["is_off_plan"] = utils.find_off_plan(
            title=item["title"],
            description=item["description"],
            labels=labels,
        )

        # remove lease years from price tag
        price_usd = str(item.get("price_usd", 0))
        result = re.search(f"{lease_years}$", price_usd)
        if result and result.end() == len(price_usd):
            price_usd = re.sub(f"{lease_years}$", "", price_usd)
            item["price_usd"] = int(price_usd)
            print(lease_years, item["price_usd"])

        if item.get("price_usd", 0) > 0:
            yield item
