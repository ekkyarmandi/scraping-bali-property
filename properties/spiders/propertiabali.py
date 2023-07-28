import scrapy
from properties.items import PropertiaItem as Property
from scrapy.loader import ItemLoader

from datetime import datetime


class PropertiabaliSpider(scrapy.Spider):
    name = "propertiabali"
    allowed_domains = ["propertiabali.com"]
    start_urls = ["https://propertiabali.com/bali-villas-for-sale"]

    def parse(self, response):
        # get the urls
        urls = response.css(
            "div.wpl_property_listing_listings_container a[id*=view_detail]::attr(href)"
        ).getall()
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse_detail)
        # get the next page url
        next_url = response.css("li.next a::attr(href)").get()
        if next_url:
            yield response.follow(response.urljoin(next_url), callback=self.parse)

    def parse_detail(self, response):
        now = datetime.now().strftime("%m/%d/%y")

        loader = ItemLoader(item=Property(), selector=response)
        loader.add_value("property_link", response.url)
        loader.add_value("source", "Propertia")
        loader.add_value("scrape_date", now)
        loader.add_value("list_date", "")
        loader.add_css("id", "div#wpl-dbst-show4 span")
        loader.add_css("title", "h1.title_text")
        loader.add_css("location", "div#wpl-dbst-show3008 span")
        loader.add_css("years", "div#wpl-dbst-show3011 span")
        loader.add_css("leasehold_freehold", "div#wpl-dbst-show3 span")
        loader.add_css("bedrooms", "div.bedroom span:first-child")
        loader.add_css("bathrooms", "div.bathroom span:first-child")
        loader.add_css("land_size", "div#wpl-dbst-show11 span")
        loader.add_css("build_size", "div#wpl-dbst-show10 span")
        loader.add_css("price", "div#wpl-dbst-show6 span")
        loader.add_css(
            "image",
            "div.wpl_prp_gallery ul.wpl-gallery-pshow li:last-child::attr(data-src)",
        )
        loader.add_css(
            "availbility",
            "div.wpl_prp_gallery div.wpl-listing-tags-cnt div.wpl-listing-tag",
        )
        loader.add_css(
            "description",
            "div.wpl_category_description div.wpl_prp_show_detail_boxes_cont p",
        )
        yield loader.load_item()
