import scrapy
from itemloaders.processors import TakeFirst, MapCompose
from w3lib.html import remove_tags
import re

from properties.items import (
    AnySold,
    JoinAndStrip,
    SplitOn,
    dimension_remover,
    get_lease_years,
    remove_whitespace,
    to_number,
)


def get_img_src(str):
    result = re.search("\((.*?)\)", str)
    return result.group(1)


class BaliTreasureProperties(scrapy.Item):
    source = scrapy.Field(output_processor=TakeFirst())
    id = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=TakeFirst()
    )
    is_off_plan = scrapy.Field(output_processor=TakeFirst())
    scrape_date = scrapy.Field(output_processor=TakeFirst())
    list_date = scrapy.Field(output_processor=TakeFirst())
    title = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=TakeFirst()
    )
    location = scrapy.Field(
        input_processor=MapCompose(remove_tags, remove_whitespace),
        output_processor=TakeFirst(),
    )
    leasehold_freehold = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=TakeFirst()
    )
    years = scrapy.Field(
        input_processor=MapCompose(remove_tags, get_lease_years),
        output_processor=TakeFirst(),
    )
    bedrooms = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=SplitOn("/")
    )
    bathrooms = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=SplitOn("/")
    )
    land_size = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=SplitOn("-")
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
    image = scrapy.Field(
        input_processor=MapCompose(get_img_src, dimension_remover),
        output_processor=TakeFirst(),
    )
    availability = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=AnySold()
    )
    description = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip),
        output_processor=JoinAndStrip("\n"),
    )
