from itemloaders.processors import TakeFirst
from typing import Callable, Union
import re

from properties.items import to_number


class IsOffPlan(TakeFirst):
    def __call__(self, values: list):
        any_sold = any(list(map(find_off_plan, values)))
        return any_sold


def find_sold_out(labels: list) -> str:
    if len(labels) > 0:
        has_sold = lambda str: "sold" in str.lower()
        labels = list(map(has_sold, labels))
        if any(labels):
            return "Sold"
    return "Available"


def find_off_plan(title: str, description: str, labels: list = []) -> bool:
    # values to look
    off_plan = ["off plan", "offplan", "off-plan"]
    # lambda function
    has_off_plan = lambda str: any([i in str.strip().lower() for i in off_plan])
    # main logic
    # check off-plan word in title and description
    if has_off_plan(title) or has_off_plan(description):
        return True
    # check off-plan in labels
    if any(list(map(has_off_plan, labels))):
        return True
    return False


def search_bedrooms(text: str) -> Union[str, None]:
    if isinstance(text, str):
        res = re.search(r"(\d{1,2}) [Bb]edroom(s?)", text)
        if res:
            b = res.group(1)
            return int(b)


def extractor(pattern: str, text: str, func: Callable) -> Union[int, None]:
    results = []
    text = str(text)
    for line in text.split("\n"):
        if not func(line):
            continue
        output = re.findall(pattern, line)
        output = list(map(lambda i: to_number(i[0]), output))
        if len(output) == 1:
            return output[0]
        elif len(output) > 0:
            results.extend(output)
    if len(results) > 0:
        return max(results)


def landsize_extractor(text: str) -> Union[int, None]:
    pattern = r"\b([0-9.,]+)(\s*)(sqm|m2|are)\b"
    has_landsize = lambda str: "landsize" in str.lower() or "land size" in str.lower()
    result = extractor(pattern, text, has_landsize)
    return result


def buildsize_extractor(text):
    pattern = r"(?:[Vv]illa|[Bb]uilding)(.*?)(?P<value>[0-9.,]+)(sqm|m2|are)"
    for line in text.split("\n"):
        result = re.match(pattern, line)
        if result:
            value = result.group("value")
            return to_number(value)
