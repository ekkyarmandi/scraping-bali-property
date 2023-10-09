import scrapy
from scrapy.loader import ItemLoader
from properties import utils
from properties.items import BaliExceptionItem
from datetime import datetime
from urllib.parse import urlencode
import requests
import time
import re


def first(values):
    try:
        return values[0]
    except:
        return None


class BaliexceptionSpider(scrapy.Spider):
    name = "baliexception"
    allowed_domains = ["baliexception.com"]

    def start_requests(self):
        self.timestamp = 0
        self.page = 1
        self.start_url = "https://baliexception.com/buy/"
        yield scrapy.Request(self.start_url)

    def parse(self, response):
        meta = response.meta.get("response")
        if meta:
            response = meta
        # find the property urls
        urls = response.css("div.elementor-heading-title a")
        for url in urls:
            link = url.css("::attr(href)").get()
            title = url.css("::text").get()
            state_hold = "Leasehold" if "leasehold" in title.lower() else "Freehold"
            yield response.follow(
                link,
                callback=self.parse_detail,
                meta=dict(title=title, state_hold=state_hold),
            )

        # go to the next page
        self.page += 1
        # update the timestamp
        if self.timestamp == 0:
            self.timestamp = int(time.time())
        # configure the GET requests
        querystring = {"nocache": self.timestamp}
        payload = f"action=jet_engine_ajax&handler=listing_load_more&query%5Bpost_status%5D%5B%5D=publish&query%5Bpost_type%5D=property&query%5Bposts_per_page%5D=9&query%5Bpaged%5D=1&query%5Bignore_sticky_posts%5D=1&query%5Btax_query%5D%5B0%5D%5Btaxonomy%5D=property_status&query%5Btax_query%5D%5B0%5D%5Bfield%5D=name&query%5Btax_query%5D%5B0%5D%5Bterms%5D%5B%5D=RENT&query%5Btax_query%5D%5B0%5D%5Bterms%5D%5B%5D=Monthly&query%5Btax_query%5D%5B0%5D%5Bterms%5D%5B%5D=Yearly&query%5Btax_query%5D%5B0%5D%5Boperator%5D=NOT%2BIN&query%5Bsuppress_filters%5D=false&query%5Bjet_smart_filters%5D=jet-engine%2Fdefault&widget_settings%5Blisitng_id%5D=1501&widget_settings%5Bposts_num%5D=9&widget_settings%5Bcolumns%5D=3&widget_settings%5Bcolumns_tablet%5D=3&widget_settings%5Bcolumns_mobile%5D=1&=widget_settings%5Bis_archive_template%5D%3D&=widget_settings%5Buse_random_posts_num%5D%3D&=widget_settings%5Bequal_columns_height%5D%3D&=widget_settings%5Buse_custom_post_types%5D%3D&=widget_settings%5Bhide_widget_if%5D%3D&=widget_settings%5Bcarousel_enabled%5D%3D&=widget_settings%5Bdots%5D%3D&=widget_settings%5Bcenter_mode%5D%3D&=widget_settings%5Binject_alternative_items%5D%3D&=widget_settings%5Bscroll_slider_enabled%5D%3D&=widget_settings%5Bcustom_query_id%5D%3D&=widget_settings%5B_element_id%5D%3D&widget_settings%5Bpost_status%5D%5B%5D=publish&widget_settings%5Bmax_posts_num%5D=9&widget_settings%5Bnot_found_message%5D=No%2Bdata%2Bwas%2Bfound&widget_settings%5Bis_masonry%5D=false&widget_settings%5Buse_load_more%5D=yes&widget_settings%5Bload_more_id%5D=loadmore&widget_settings%5Bload_more_type%5D=click&widget_settings%5Bload_more_offset%5D%5Bunit%5D=px&widget_settings%5Bload_more_offset%5D%5Bsize%5D=0&widget_settings%5Bslides_to_scroll%5D=1&widget_settings%5Barrows%5D=true&widget_settings%5Barrow_icon%5D=fa%2Bfa-angle-left&widget_settings%5Bautoplay%5D=true&widget_settings%5Bautoplay_speed%5D=5000&widget_settings%5Binfinite%5D=true&widget_settings%5Beffect%5D=slide&widget_settings%5Bspeed%5D=500&widget_settings%5Bscroll_slider_on%5D%5B%5D=desktop&widget_settings%5Bscroll_slider_on%5D%5B%5D=tablet&widget_settings%5Bscroll_slider_on%5D%5B%5D=mobile&widget_settings%5Bcustom_query%5D=false&page_settings%5Bpost_id%5D=false&page_settings%5Bqueried_id%5D=false&page_settings%5Belement_id%5D=false&page_settings%5Bpage%5D={self.page}&listing_type=false&isEditMode=false&addedPostCSS%5B%5D=1501"
        headers = {
            "cookie": "search_suggestions_session_id=651fa48671c5b; PHPSESSID=651fa48671c5b",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        }
        response = requests.post(
            self.start_url, data=payload, headers=headers, params=querystring
        )
        if response.status_code == 200:
            try:
                results = response.json()
                properties_wrapper = results["data"]["html"]
                if properties_wrapper != "":
                    meta = {
                        "response": scrapy.http.TextResponse(
                            url=response.url,
                            body=properties_wrapper,
                            encoding="utf-8",
                        )
                    }
                    yield scrapy.Request(
                        self.start_url, meta=meta, dont_filter=True, callback=self.parse
                    )
            except:
                pass

    def parse_detail(self, response):
        title = response.meta.get("title")
        contract_type = title.split("|")[-1].strip().title()
        detail_selector = (
            "div[data-widget_type='heading.default']:contains('{}') + div ::text"
        )
        property_type = response.css(detail_selector.format("Type")).getall()
        property_type = first(
            list(filter(lambda str: str.strip() != "", property_type))
        )
        contract_type = [contract_type, property_type]

        now = datetime.now().replace(day=1).strftime("%m/%d/%y")
        loader = ItemLoader(item=BaliExceptionItem(), selector=response)
        loader.add_value("property_link", response.url)
        loader.add_value("source", "Bali Exception")
        loader.add_value("scrape_date", now)
        # loader.add_value("list_date", "")
        loader.add_css("id", detail_selector.format("Property ID"))
        loader.add_value("title", title)
        loader.add_value("leasehold_freehold", contract_type)
        loader.add_css("location", "div:has(div.is-svg-icon) > a")
        loader.add_css("years", detail_selector.format("Leasehold"))
        loader.add_css("bedrooms", detail_selector.format("Bedrooms"))
        loader.add_css("bathrooms", detail_selector.format("Bathrooms"))
        loader.add_css("land_size", detail_selector.format("Land Area"))
        loader.add_css("build_size", detail_selector.format("Property Size"))
        # loader.add_css("price", "")
        loader.add_css("price_usd", "div.wpprice span.wpcs_price::attr(data-amount)")
        loader.add_css(
            "image",
            "div.property-banner a[style*=background-image]::attr(style)",
        )
        loader.add_value("availability", "Available")
        loader.add_css(
            "description",
            'div[data-widget_type="theme-post-content.default"] div ::text',
        )
        item = loader.load_item()

        labels = response.css(
            ".elementor-element-populated a.jet-listing-dynamic-terms__link::text"
        ).getall()
        item["is_off_plan"] = utils.find_off_plan(
            item["title"],
            item["description"],
            labels,
        )
        yield item
