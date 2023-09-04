import re
import json
import urllib.parse
import time
import os
import signal
import configuration

import scrapy
from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from DB_elements import Keyword
from twisted.internet import reactor
from urllib.parse import urlparse, unquote
from classified_item import Classified_item
from processing import Processing_items

Base = declarative_base()


def sleep(_, duration=configuration.FREQUENCY):
    print(f'sleeping for: {duration}')
    time.sleep(duration)


def crawl(runner):
    d = runner.crawl(CarousellSpider)
    d.addBoth(sleep)
    d.addBoth(lambda _: crawl(runner))
    return d


def loop_crawl():
    print("loop_crawl")
    runner = CrawlerRunner(get_project_settings())
    crawl(runner)
    reactor.run()


def getKeywordFromDB(session):
    # Get keywords from DB
    db_keywords = [
        keyword_obj.keyword_str for keyword_obj in session.query(Keyword).all()]

    print('getKeywordFromDB')
    print(db_keywords)

    return db_keywords


class CarousellSpider(scrapy.Spider):
    name = 'carousell_search'
    allowed_domains = ['www.carousell.sg/']

    engine = create_engine('sqlite:///Database/marabou_alert.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Remove unused keywords in DB
    db_keywords = session.query(Keyword).filter(~Keyword.chats.any()).all()
    for keyword_obj in db_keywords:
        session.delete(keyword_obj)
    session.commit()
    print('----------------------' + 'CarousellSpider')

    def generate_search_urls(session):
        base_url = ("https://www.carousell.sg/search/")
        params = {'addRecent': 'false', 'canChangeKeyword': 'false',
                  'includeSuggestions': 'false', 'sort_by': '3'}
        urls = []
        for search in getKeywordFromDB(session):
            query_url = base_url + \
                urllib.parse.quote(search) + "?" + \
                urllib.parse.urlencode(params)
            urls.append(query_url)

        print("generate_search_urls")

        return urls

    def start_requests(self):
        # Set signals to be able to kill the application
        signal.signal(signal.SIGINT, self.custom_terminate_spider)  # CTRL+C
        # sent by scrapyd
        signal.signal(signal.SIGTERM, self.custom_terminate_spider)

        print('++++++++++++++++++++++++++++++++++++++++++++++++++start_requests')
        print(self.start_urls)

        if (self.start_urls):
            # Parse the keywords in DB to search in Carousell
            for url in self.start_urls:
                yield scrapy.FormRequest(url, self.response_parser, headers=configuration.HEADERS)

    def custom_terminate_spider(self, sig, frame):
        self.logger.info(self.crawler.stats.get_stats()
                         )  # print stats if you want

        reactor.stop()
        os.kill(os.getpid(), signal.SIGKILL)

    def response_parser(self, response):
        responseExtract = re.search(
            r'<script type="application/json">.*?</script>', response.text)
        if (responseExtract is None):
            print("ERROR: The format of the HTML response might have changed, look into pycaroussel.py in parse function")
        else:
            responseExtract = responseExtract[0]
            responseExtract = responseExtract.replace(
                "<script type=\"application/json\">", "")
            responseExtract = responseExtract.replace("</script>", "")

            json_obj = json.loads(responseExtract)

            searchItems = json_obj['SearchListing']['listingCards']
            if (searchItems):
                for item in searchItems:
                    # Select only the items which are NOT promoted by Carousell
                    if not 'promoted' in item and item['listingID'] > 0:
                        is_item_valid = False
                        for search_keyword in getKeywordFromDB(self.session):
                            search_keyword = search_keyword.lower()
                            title = item['title'].lower()

                            if any(word in title for word in search_keyword.split()):
                                is_item_valid = True
                                yield item
                                break

                        if is_item_valid == False:
                            # print ('<<<<<<<<<<<<<<<<<<<<<<<<<<< ' + search_keyword + ' NOT in title')
                            # print (title)
                            item['title'] = '? ' + item['title']
                            # print (response.request)
                            yield item

    def create_item_url(self, item_id, item_title):
        base_url = "https://www.carousell.sg/p/"
        title_url = item_title.replace(" ", "-")
        title_url = urllib.parse.quote(title_url)
        return base_url + title_url + '-' + item_id

    def item_scraped(self, item, response):
        # Get keyword from URL
        path = urlparse(response.url).path
        path = unquote(path)
        search_keyword = path.split('/')[2]

        # Create the listing object
        listing_item = Classified_item()
        listing_item.platform = 'Carousell'
        listing_item.title = item['title']
        listing_item.price = item['price']
        listing_item.url = self.create_item_url(
            str(item['listingID']), item['title'])
        listing_item.listing_id = str(item['listingID'])
        listing_item.seller = item['seller']['username']
        if 'photoItem' in item['media'][0]:
            listing_item.image = item['media'][0]['photoItem']['url']
        elif 'videoItem' in item['media'][0]:
            listing_item.image = item['media'][0]['videoItem']['thumbnail']['url']

        # Process the item to send a notification
        process = Processing_items()
        process.start_process_items(listing_item, search_keyword)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(CarousellSpider, cls).from_crawler(
            crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed,
                                signal=signals.spider_closed)
        crawler.signals.connect(spider.item_scraped,
                                signal=signals.item_scraped)
        return spider

    def spider_closed(self, spider):
        spider.logger.info('Spider closed: %s', spider.name)
        print('spider_closed')

    start_urls = generate_search_urls(session)


class CarousellSearch():
    def __init__(self, results=30):
        loop_crawl()
