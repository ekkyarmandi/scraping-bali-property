# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import json
import scrapy
import re

from datetime import datetime, timedelta

from itemloaders.processors import MapCompose, TakeFirst, Join
from w3lib.html import remove_tags

### Custom Functions


def to_number(value):
    if type(value) == str:
        value = re.sub(",", "", value)
        result = re.findall(r"[0-9.]+", value)
        dots = len(re.findall(r"\.", value))
        if len(result) > 0:
            result = "".join(result)
            dec = len(result.split(".")[-1]) if dots == 1 else 0
            if dots > 1 or dec > 2:
                result = result.replace(".", "")
            return eval(result)
        else:
            return ""
    return value


def get_uploaded_date(src, pattern=r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"):
    result = re.search(pattern, src)
    if result:
        try:
            year = result.group("year")
            month = result.group("month")
            day = result.group("day")
            date = datetime(year=int(year), month=int(month), day=int(day))
            return date.strftime("%m/%d/%y")
        except:
            return None


def get_background_image(value):
    result = re.search(r"background\-image\:url\((?P<src>.*)\)\;", value)
    if result:
        return result.group("src")
    return value


def remove_whitespace(value):
    return re.sub("\s+", " ", value).strip()


def price_request_to_zero(value):
    if type(value) == str and "price request" in value.lower():
        return 0
    return value


def time_ago_to_datetime(text):
    current_date = datetime.now()
    interval = to_number(text)
    if "year" in text:
        delta = current_date - timedelta(days=interval * 365)
    elif "month" in text:
        delta = current_date - timedelta(days=interval * 30)
    elif "week" in text:
        delta = current_date - timedelta(days=interval * 7)
    elif "day" in text:
        delta = current_date - timedelta(days=interval)
    else:
        return text
    return delta.strftime("%m/%d/%y")


def dot_to_comma(value):
    return value.replace(".", ",")


def remove_show_more_less(value):
    return value.replace("Show More", "").replace("Show Less", "")


def is_sold(value):
    if value.lower() == "sold":
        return "Sold"
    return "Available"


def safe_number(value):
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return None  # Invalid input

    if isinstance(value, (int, float)):
        try:
            if value.is_integer():
                return int(value)
            else:
                rounded = round(value, 2)
                return rounded
        except AttributeError:
            return value
    else:
        return None  # Invalid input


def are_to_sqm(value):
    if type(value) == str:
        if "are" in value.lower():
            value = to_number(value) * 100
            return safe_number(value)
        else:
            return to_number(value)
    return value


def find_lease_years(description):
    description = description.lower()
    paragraph = description.split("\n")
    sentences = []
    for p in paragraph:
        sentences.extend(p.split("."))
    for s in sentences:
        if "years" in s or "lease" in s:
            years = re.findall(r"\b\d{2,4}\b", s)
            years = list(filter(lambda d: len(d) == 2 or len(d) == 4, years))
            years = sorted(years, key=lambda d: len(d))
            if len(years) > 0:
                today = datetime.now()
                years = years[0]
                if len(years) == 4 and int(years) >= today.year:
                    return int(years) - today.year
                elif len(years) == 2:
                    return int(years)


def get_lease_years(text):
    text = text.lower()
    if "years" in text or "lease" in text or re.search(r"\d{4}", text):
        years = re.findall(r"\b\d{4}\b|\d{2} years", text)
        years = list(map(lambda d: re.search(r"\d{2,4}", d).group(), years))
        years = list(filter(lambda d: len(d) == 2 or len(d) == 4, years))
        years = sorted(years, key=lambda d: len(d))
        years = list(map(int, years))
        if len(years) > 0:
            years = years[0]
            if len(str(years)) == 4:
                today = datetime.now()
                return int(years) - today.year
            elif len(str(years)) == 2:
                return int(years)
        # developed based on rajavilla case
        elif "years" in text:
            results = re.findall(r"[0-9.,]+", text)
            results = list(map(to_number, results))
            if len(results) > 0:
                return min(results)


def dimension_remover(src):
    patterns = [
        r"(-\d+x\d+)\.jpg",
        r"(-\d+x\d+)\.jpeg",
        r"(-\d+x\d+)\.png",
        r"(-\d+x\d+)\.webp",
    ]
    result = re.search("|".join(patterns), src)
    if result:
        for i in range(1, 4):
            dim = result.group(i)
            if dim:
                src = src.replace(dim, "")
    return src


def find_published_date(script):
    result = re.search(r'"datePublished":"(?P<date>[T0-9\-\:\+]+)"', script)
    if result:
        date = result.group("date")
        return datetime.fromisoformat(date).strftime("%m/%d/%y")
    return ""


def define_property_type(title: str) -> str:
    types = ["villa", "apartement", "hotel", "land", "house", "home"]
    for t in types:
        if t in title.lower():
            if t in ["house", "home"]:
                return "House"
            else:
                return t.title()
    return "Villa"  # the default is Villa


class FindLeaseYears:
    def __call__(self, values):
        for v in values:
            result = get_lease_years(v)
            if type(result) == int:
                return result


class AnySold(TakeFirst):
    def __call__(self, values):
        is_sold = lambda f: "sold" in f.lower()
        any_sold = any(list(map(is_sold, values)))
        if any_sold:
            return "Sold"
        return "Available"


class SplitOn(TakeFirst):
    def __init__(self, splitter: str = "-", index: int = 0):
        self.splitter = splitter
        self.index = index

    def __call__(self, values: list):
        for value in values:
            if type(value) == str:
                return value.split(self.splitter)[self.index].strip()
            elif type(value) == int:
                return value


class TakeNth:
    def __init__(self, position):
        self.position = position

    def __call__(self, values):
        new_values = []
        for v in values:
            if type(v) == str:
                v = v.strip()
            new_values.append(v)
        try:
            return new_values[self.position]
        except IndexError:
            return None


class Max(TakeFirst):
    def __call__(self, values):
        return max(values)


class JoinAndStrip(Join):
    def __call__(self, values):
        values = list(map(str.strip, values))
        values = list(filter(lambda v: v != "", values))
        return self.separator.join(values)


### Item Classes


class PropertyItem(scrapy.Item):
    source = scrapy.Field(output_processor=TakeFirst())
    id = scrapy.Field(
        input_processor=MapCompose(str.strip), output_processor=TakeFirst()
    )
    is_off_plan = scrapy.Field(output_processor=TakeFirst())
    scrape_date = scrapy.Field(output_processor=TakeFirst())
    list_date = scrapy.Field(output_processor=TakeFirst())
    title = scrapy.Field(
        input_processor=MapCompose(str.strip), output_processor=TakeFirst()
    )
    location = scrapy.Field(
        input_processor=MapCompose(str.strip), output_processor=TakeFirst()
    )
    leasehold_freehold = scrapy.Field(
        input_processor=MapCompose(str.strip), output_processor=JoinAndStrip(" ")
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
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    price_usd = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    property_link = scrapy.Field(output_processor=TakeFirst())
    image = scrapy.Field(output_processor=TakeFirst())
    availability = scrapy.Field(output_processor=TakeFirst())
    description = scrapy.Field(output_processor=lambda values: "".join(values).strip())


class BaliExceptionItem(PropertyItem):
    source = scrapy.Field(output_processor=TakeFirst())
    id = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip),
        output_processor=TakeFirst(),
    )
    is_off_plan = scrapy.Field(output_processor=TakeFirst())
    scrape_date = scrapy.Field(output_processor=TakeFirst())
    list_date = scrapy.Field(output_processor=TakeFirst())
    title = scrapy.Field(output_processor=TakeFirst())
    location = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip), output_processor=Join(", ")
    )
    leasehold_freehold = scrapy.Field(output_processor=Join(" "))
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
    price = scrapy.Field(output_processor=TakeFirst())
    price_usd = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    property_link = scrapy.Field(output_processor=TakeFirst())
    image = scrapy.Field(
        input_processor=MapCompose(get_background_image), output_processor=TakeFirst()
    )
    availability = scrapy.Field(output_processor=TakeFirst())
    description = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip),
        output_processor=JoinAndStrip("\n"),
    )


class UnrealBaliPorpertyItem(PropertyItem):
    source = scrapy.Field(output_processor=TakeFirst())
    id = scrapy.Field(output_processor=TakeFirst())
    is_off_plan = scrapy.Field(output_processor=TakeFirst())
    scrape_date = scrapy.Field(output_processor=TakeFirst())
    list_date = scrapy.Field(
        input_processor=MapCompose(time_ago_to_datetime), output_processor=TakeFirst()
    )
    title = scrapy.Field(output_processor=TakeFirst())
    location = scrapy.Field(output_processor=TakeFirst())
    leasehold_freehold = scrapy.Field(output_processor=TakeFirst())
    years = scrapy.Field(
        input_processor=MapCompose(remove_tags, to_number), output_processor=TakeFirst()
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
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    build_size = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    price = scrapy.Field(output_processor=TakeFirst())
    price_usd = scrapy.Field(
        input_processor=MapCompose(to_number), output_processor=TakeFirst()
    )
    property_link = scrapy.Field(output_processor=TakeFirst())
    image = scrapy.Field(output_processor=TakeFirst())
    availability = scrapy.Field(output_processor=Join(","))
    description = scrapy.Field(
        input_processor=MapCompose(remove_tags, str.strip),
        output_processor=JoinAndStrip("\n"),
    )
