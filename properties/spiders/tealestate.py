import scrapy
from scrapy.http import TextResponse
from scrapy.loader import ItemLoader
from properties import utils
from properties.items import get_lease_years
from datetime import datetime
import re

from properties.property_items.tealestate import TealEstatePropertyItem
from itemloaders.processors import MapCompose


class TealEstateSpider(scrapy.Spider):
    name = "tealestate"
    allowed_domains = ["tealestate.co"]
    start_urls = [
        "https://tealestate.co/wp-admin/admin-ajax.php?action=jet_smart_filters&provider=jet-engine%2fdefault&defaults%5bpost_status%5d%5b%5d=publish&defaults%5bpost_type%5d=properties&defaults%5bposts_per_page%5d=10&defaults%5bpaged%5d=1&defaults%5bignore_sticky_posts%5d=1&defaults%5borderby%5d%5bsold%5d=asc&defaults%5borderby%5d%5bdate%5d=desc&defaults%5bmeta_key%5d=sold&settings%5blisitng_id%5d=412&settings%5bcolumns%5d=2&settings%5bcolumns_tablet%5d=2&settings%5bcolumns_mobile%5d=1&settings%5bpost_status%5d%5b%5d=publish&settings%5bposts_num%5d=10&settings%5bmax_posts_num%5d=9&settings%5bnot_found_message%5d=no%2bproperty%2bmatch%2byour%2bcriteria&settings%5bequal_columns_height%5d=yes&settings%5bload_more_type%5d=click&settings%5bslides_to_scroll%5d=1&settings%5barrows%5d=true&settings%5barrow_icon%5d=fa%2bfa-angle-left&settings%5bautoplay%5d=true&settings%5bautoplay_speed%5d=5000&settings%5binfinite%5d=true&settings%5beffect%5d=slide&settings%5bspeed%5d=500&settings%5binject_alternative_items%5d&settings%5bscroll_slider_enabled%5d&settings%5bscroll_slider_on%5d%5b%5d=desktop&settings%5bscroll_slider_on%5d%5b%5d=tablet&settings%5bscroll_slider_on%5d%5b%5d=mobile&props%5bfound_posts%5d=472&props%5bmax_num_pages%5d=48&props%5bpage%5d=1&paged=1"
    ]

    def parse(self, response):
        try:
            data = response.json()
        except:
            data = {}
        content = data.get("content", "")
        content = TextResponse(url=response.url, body=content, encoding="utf-8")
        items = content.css(".jet-listing-grid__item")
        for item in items:
            _id = item.css(
                "div.jet-listing-dynamic-field__content:contains(TE)::text"
            ).get()
            url = response.urljoin("/properties/" + _id.lower() + "/")
            contract_type_selector = ",".join(
                [
                    "div.jet-listing-dynamic-field__content:contains(hold)::text",
                    "div.elementor-heading-title:contains(hold)::text",
                ]
            )
            contract_type = item.css(contract_type_selector).get()
            contract_type = contract_type.split(" ")[0]
            loader = ItemLoader(item=TealEstatePropertyItem(), selector=item)
            loader.add_value("id", _id)
            loader.add_value("property_link", url)
            loader.add_css(
                "availability",
                "div.elementor-widget-jet-listing-dynamic-field:contains(TE) + div span.elementor-heading-title::text",
            )
            loader.add_css("image", ".elementor-widget-container img::attr(src)")
            loader.add_css(
                "bedrooms", "div.jet-listing-dynamic-field__content:contains(Bed)::text"
            )
            loader.add_css(
                "bathrooms",
                "div.jet-listing-dynamic-field__content:contains(Bath)::text",
            )
            loader.add_css(
                "price", "div.jet-listing-dynamic-field__content:contains(IDR)::text"
            )
            loader.add_value("leasehold_freehold", [contract_type, "Villa"])
            loader.add_value("years", contract_type, MapCompose(get_lease_years))

            labels = item.css("div.elementor-widget span:contains(plan)::text").getall()

            meta = dict(loader=loader, labels=labels)
            yield response.follow(url, callback=self.parse_detail, meta=meta)

        # go to next url
        pagination = data.get("pagination")
        if pagination:
            prev_page = re.search(r"paged=(?P<page>\d+)", response.url).group("page")
            prev_page = int(prev_page)
            max_page = pagination.get("max_num_pages")
            if int(prev_page) <= max_page:
                next_url = response.url.replace(
                    f"paged={prev_page}", f"paged={prev_page+1}"
                )
                yield response.follow(next_url, callback=self.parse)

    def parse_detail(self, response):
        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        i = response.meta
        loader = i.get("loader")
        loader.selector = response
        loader.add_value("source", "Teal Estate")
        loader.add_value("scrape_date", now)
        loader.add_css("list_date", "script[type='application/ld+json']::text")
        loader.add_css(
            "land_size", 'h3.elementor-icon-box-title:contains("Land Size") + p::text'
        )
        loader.add_css(
            "build_size",
            'h3.elementor-icon-box-title:contains("Building Size") + p::text',
        )
        loader.add_css("title", "h3.elementor-heading-title::text")
        loader.add_css(
            "location",
            "h3.elementor-icon-box-title:contains(Location) + p::text",
            MapCompose(str.strip),
        )
        loader.add_css("description", "div:contains(Description) + div p ::text")
        item = loader.load_item()
        availability = item.get("availability")
        if not availability:
            item["availability"] = "Available"

        labels = i.get("labels", [])
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
            labels,
        )

        yield item
