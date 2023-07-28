# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
import re

from itemloaders.processors import MapCompose, TakeFirst, Join
from w3lib.html import remove_tags

### Custom Functions


def to_number(value):
    value = re.sub(",", "", value)
    result = re.findall(r"[0-9.]+", value)
    if len(result) > 0:
        return eval("".join(result))
    return value


def price_request_to_zero(value):
    if type(value) ==str and "price request" in value.lower():
        return 0
    return value


def dot_to_comma(value):
    return value.replace(".", ",")


def remove_show_more_less(value):
    return value.replace("Show More", "").replace("Show Less", "")


def is_sold(value):
    if value.lower() == "sold":
        return "Sold"
    return "Available"


def usd_to_idr(value):
    return value * 15000


def are_to_sqm(value):
    return value * 100


def any_sold(values):
    bools = [True if v.lower() == "sold" else False for v in values]
    if any(bools):
        return "Sold"
    return "Available"


class AnySold(TakeFirst):
    def __call__(self, values):
        bools = [True if v.lower() == "sold" else False for v in values]
        if any(bools):
            return "Sold"
        return "Available"


### Item Classes


class PropertyItem(scrapy.Item):
    source = scrapy.Field(output_processor=TakeFirst())
    id = scrapy.Field(output_processor=TakeFirst())
    scrape_date = scrapy.Field(output_processor=TakeFirst())
    list_date = scrapy.Field(output_processor=TakeFirst())
    title = scrapy.Field(output_processor=TakeFirst())
    location = scrapy.Field(output_processor=TakeFirst())
    leasehold_freehold = scrapy.Field(output_processor=TakeFirst())
    years = scrapy.Field(output_processor=TakeFirst())
    bedrooms = scrapy.Field(output_processor=TakeFirst())
    bathrooms = scrapy.Field(output_processor=TakeFirst())
    land_size = scrapy.Field(output_processor=TakeFirst())
    build_size = scrapy.Field(output_processor=TakeFirst())
    price = scrapy.Field(output_processor=TakeFirst())
    property_link = scrapy.Field(output_processor=TakeFirst())
    image = scrapy.Field(output_processor=TakeFirst())
    availbility = scrapy.Field(output_processor=TakeFirst())
    description = scrapy.Field(output_processor=TakeFirst())


class PropertiaItem(PropertyItem):
    id = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=TakeFirst()
    )
    title = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=TakeFirst()
    )
    location = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=TakeFirst()
    )
    leasehold_freehold = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=TakeFirst()
    )
    years = scrapy.Field(
        input_processor=MapCompose(remove_tags, to_number),
        output_processor=TakeFirst(),
    )
    bedrooms = scrapy.Field(
        input_processor=MapCompose(remove_tags, to_number),
        output_processor=TakeFirst(),
    )
    bathrooms = scrapy.Field(
        input_processor=MapCompose(remove_tags, to_number),
        output_processor=TakeFirst(),
    )
    land_size = scrapy.Field(
        input_processor=MapCompose(remove_tags, to_number),
        output_processor=TakeFirst(),
    )
    build_size = scrapy.Field(
        input_processor=MapCompose(remove_tags, to_number),
        output_processor=TakeFirst(),
    )
    price = scrapy.Field(
        input_processor=MapCompose(remove_tags, to_number),
        output_processor=TakeFirst(),
    )
    availbility = scrapy.Field(
        input_processor=MapCompose(remove_tags, is_sold), output_processor=AnySold()
    )
    description = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=Join("\n")
    )


class LazudiPropertyItem(PropertyItem):
    source = scrapy.Field(output_processor=TakeFirst())
    id = scrapy.Field(output_processor=TakeFirst())
    scrape_date = scrapy.Field(output_processor=TakeFirst())
    list_date = scrapy.Field(output_processor=TakeFirst())
    title = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip), output_processor=TakeFirst()
    )
    location = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip), output_processor=TakeFirst()
    )
    leasehold_freehold = scrapy.Field(output_processor=TakeFirst())
    years = scrapy.Field(output_processor=TakeFirst())
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
        input_processor=MapCompose(remove_tags, str.strip, to_number),
        output_processor=TakeFirst(),
    )
    property_link = scrapy.Field(output_processor=TakeFirst())
    image = scrapy.Field(output_processor=TakeFirst())
    availbility = scrapy.Field(output_processor=TakeFirst())
    description = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip, remove_show_more_less),
        output_processor=Join("\n"),
    )


class KibarerPropertyItem(PropertyItem):
    title = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=TakeFirst()
    )
    leasehold_freehold = scrapy.Field(
        input_processor=MapCompose(
            remove_tags, lambda x: re.sub(r"\s+", "", x), str.title
        ),
        output_processor=TakeFirst(),
    )
    years = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    bedrooms = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    bathrooms = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    land_size = scrapy.Field(
        input_processor=MapCompose(to_number, are_to_sqm), output_processor=TakeFirst()
    )
    build_size = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    price = scrapy.Field(
        input_processor=MapCompose(remove_tags, to_number, price_request_to_zero, usd_to_idr),
        output_processor=TakeFirst(),
    )
    description = scrapy.Field(
        input_processor=MapCompose(remove_tags, lambda s: s if s != "\n" else s),
        output_processor=Join("\n"),
    )


class HomeImmoPropertyItem(PropertyItem):
    title = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip), output_processor=TakeFirst()
    )
    location = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip), output_processor=TakeFirst()
    )
    leasehold_freehold = scrapy.Field(
        input_processor=MapCompose(str.title), output_processor=TakeFirst()
    )
    years = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
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
        input_processor=MapCompose(remove_tags, dot_to_comma, to_number),
        output_processor=TakeFirst(),
    )
    description = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip), output_processor=TakeFirst()
    )
