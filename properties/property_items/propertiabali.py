import scrapy
from itemloaders.processors import MapCompose, TakeFirst
from properties.items import (
    AnySold,
    are_to_sqm,
    dimension_remover,
    find_published_date,
    remove_tags,
    to_number,
    JoinAndStrip,
)


class PropertiaItem(scrapy.Item):
    source = scrapy.Field(output_processor=TakeFirst())
    id = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=TakeFirst()
    )
    is_off_plan = scrapy.Field(output_processor=TakeFirst())
    scrape_date = scrapy.Field(output_processor=TakeFirst())
    list_date = scrapy.Field(
        input_processor=MapCompose(find_published_date), output_processor=TakeFirst()
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
        input_processor=MapCompose(remove_tags, to_number), output_processor=TakeFirst()
    )
    bedrooms = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    bathrooms = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    land_size = scrapy.Field(
        input_processor=MapCompose(are_to_sqm), output_processor=TakeFirst()
    )
    build_size = scrapy.Field(
        input_processor=MapCompose(are_to_sqm), output_processor=TakeFirst()
    )
    price = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    price_usd = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    property_link = scrapy.Field(output_processor=TakeFirst())
    image = scrapy.Field(
        input_processor=MapCompose(dimension_remover), output_processor=TakeFirst()
    )
    availability = scrapy.Field(
        input_processor=MapCompose(remove_tags), output_processor=AnySold()
    )
    description = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip),
        output_processor=JoinAndStrip("\n"),
    )
