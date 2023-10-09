# Undone yet
import scrapy
from datetime import datetime
from itemloaders.processors import MapCompose, TakeFirst
from properties.items import (
    get_lease_years,
    remove_tags,
    to_number,
    JoinAndStrip,
)
import re


def empty_as_none(value):
    if value == "":
        return None
    else:
        return value


class BaliSelectItem(scrapy.Item):
    source = scrapy.Field(output_processor=TakeFirst())
    id = scrapy.Field(output_processor=TakeFirst())
    is_off_plan = scrapy.Field(output_processor=TakeFirst())
    scrape_date = scrapy.Field(output_processor=TakeFirst())
    list_date = scrapy.Field(output_processor=TakeFirst())
    title = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip, empty_as_none),
        output_processor=TakeFirst(),
    )
    location = scrapy.Field(output_processor=TakeFirst())
    leasehold_freehold = scrapy.Field(output_processor=JoinAndStrip(" "))
    years = scrapy.Field(
        input_processor=MapCompose(get_lease_years), output_processor=TakeFirst()
    )
    bedrooms = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    bathrooms = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    land_size = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    build_size = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    price = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    price_usd = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    property_link = scrapy.Field(output_processor=TakeFirst())
    image = scrapy.Field()
    availability = scrapy.Field(output_processor=TakeFirst())
    description = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip),
        output_processor=JoinAndStrip("\n"),
    )


class BaliselectSpider(scrapy.Spider):
    name = "baliselect"
    allowed_domains = ["baliselect.com"]
    start_urls = ["https://www.baliselect.com/villas-for-sale/"]

    def parse(self, response):
        # lambda function
        is_property_url = lambda u: re.search(r"/property/", u)
        # find all urls
        urls = response.css(".iw-property-item a[href]::attr(href)").getall()
        urls = list(filter(is_property_url, urls))
        for url in urls:
            yield response.follow(url, callback=self.parse_detail)

    def parse_detail(self, response):
        def rows(key):
            rows = response.css(f'.iwp-item:contains("{key}") ::text').getall()
            rows = list(map(str.strip, rows))
            rows = list(filter(lambda t: t.strip() != "", rows))
            return rows[-1]

        now = datetime.now().replace(day=1).strftime(r"%m/%d/%Y")
        loader = scrapy.loader.ItemLoader(item=BaliSelectItem(), selector=response)
        loader.add_css("title", "h1::text")
        loader.add_value("source", "Bali Select")
        loader.add_value("scrape_date", now)
        loader.add_value("property_link", response.url)
        loader.add_value("id", rows("Property ID"))
        loader.add_value("leasehold_freehold", rows("Type of Holding"))
        loader.add_value("location", rows("Location"))
        loader.add_value("bedrooms", rows("Bedroom"))
        loader.add_value("bathrooms", rows("Bathroom"))
        loader.add_value("land_size", rows("Land Size"))
        loader.add_value("build_size", rows("Build Size"))
        item = loader.load_item()
        yield item
