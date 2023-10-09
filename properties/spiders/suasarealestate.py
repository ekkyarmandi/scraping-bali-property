import scrapy
import urllib.parse
from itemloaders.processors import MapCompose
from scrapy.loader import ItemLoader
from datetime import datetime
from properties import utils

from properties.items import PropertyItem, find_published_date, get_lease_years


class SuasaRealEstateSpider(scrapy.Spider):
    name = "suasarealestate"
    allowed_domains = ["suasarealestate.com"]
    start_urls = ["https://www.suasarealestate.com/wp-admin/admin-ajax.php"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    def start_requests(self):
        form_data = {
            "action": "search_property",
            "nonce": "5407175caa",
            "source": "search-form",
            "page": "1",
            "ppp": "-1,-1,20,20,20",
            "args": "paging=1&ppp=-1%2C-1%2C20%2C20%2C20&cat=sale&ref=&term=&bedroom=&curr=usd&min-budget=&max-budget=&sort-by=date-latest&ppp=20",
            "sortby[0][name]": "sort-by",
            "sortby[0][value]": "date-latest",
            "sortby[1][name]": "ppp",
            "sortby[1][value]": "20",
        }
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                method="POST",
                body=urllib.parse.urlencode(form_data),
                headers=self.headers,
            )

    def parse(self, response):
        items = response.css(".property-item")
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        for item in items:
            url = item.css(".property-content a::attr(href)").get()
            loader = ItemLoader(item=PropertyItem(), selector=item)
            loader.add_value("source", "Suasa Real Estate")
            loader.add_value("scrape_date", now)
            loader.add_value("property_link", url)
            loader.add_css("title", ".property-content a:nth-child(2)::text")
            loader.add_css(
                "location", ".property-content a p:first-child.location::text"
            )
            loader.add_css("id", ".property-content a p:nth-child(2).location::text")
            loader.add_css("image", ".lazy-wrapper img::attr(data-src)")
            loader.add_css(
                "land_size",
                '.lazy-wrapper li div:contains("Land Size") span.value::text',
            )
            loader.add_css(
                "build_size",
                '.lazy-wrapper li div:contains("Building Size") span.value::text',
            )
            loader.add_css("price_usd", ".property-content a + p.price::text")
            meta = dict(loader=loader)
            yield response.follow(url, callback=self.parse_detail, meta=meta)

    def parse_detail(self, response):
        i = response.meta
        loader = i.get("loader")
        loader.selector = response
        contract_type = response.css(
            "#main .content-table tr:contains(Term) td:nth-child(2)::text"
        ).get()
        property_type = response.url.split("/")[3].title()
        availability = response.css(
            "#main .content-table tr:contains(Available) td:nth-child(2)::text"
        ).get()
        if type(availability) == str:
            availability = availability.title()
            if "sold" in availability.lower():
                availability = "Sold"
            else:
                availability = "Available"
        else:
            availability = "Available"

        loader.add_value("availability", availability)
        loader.add_value("leasehold_freehold", [contract_type, property_type])
        loader.add_css(
            "bedrooms",
            "#main .content-table tr:contains(Bedroom) td:nth-child(2)::text",
        )
        loader.add_css(
            "bathrooms",
            "#main .content-table tr:contains(Bathroom) td:nth-child(2)::text",
        )
        loader.add_css(
            "years",
            '#main .content-table tr:contains("End of Lease") td:nth-child(2)::text',
            MapCompose(get_lease_years),
        )
        loader.add_css(
            "list_date",
            "script[type='application/ld+json']::text",
            MapCompose(find_published_date),
        )
        loader.add_css("description", "#main .prop-desc-wrapper ::text")
        item = loader.load_item()
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
        )
        if item.get("price_usd", 0) > 0:
            yield item
