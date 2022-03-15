import keyword
import signal
import re
import json
import os
import urllib.parse
import time
from DB_elements import Keyword
import arrow
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy import signals
from twisted.internet.task import deferLater
from scrapy.crawler import CrawlerRunner
from twisted.internet import reactor, defer
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from classified_item import Classified_item
from processing import Processing_items
from configuration import FREQUENCY
from urllib.parse import urlparse, unquote

Base = declarative_base()

class CarousellSpider(scrapy.Spider):
    name = 'carousell_search'
    allowed_domains = ['www.carousell.sg/']
    start_urls = None

    db_keywords = []

    def __init__(self, urls, keywords):
        self.start_urls = urls
        self.db_keywords = keywords

    def start_requests(self):
        # Set signals to be able to kill the application
        signal.signal(signal.SIGINT, self.custom_terminate_spider) #CTRL+C
        signal.signal(signal.SIGTERM, self.custom_terminate_spider) #sent by scrapyd

        # yield scrapy.Request(self.start_urls, self.parse)
        return [scrapy.FormRequest(self.start_urls, self.parse)]

    def custom_terminate_spider(self, sig, frame):
        self.logger.info(self.crawler.stats.get_stats()) #print stats if you want
    
        #dangerous line, it will just kill your scrapy spider running immediately
        os.kill(os.getpid(), signal.SIGKILL)

    def parse(self, response):
        responseExtract = re.search(r'window.initialState=.*</script>', response.text)[0]
        responseExtract = responseExtract.replace("window.initialState=", "")
        data = responseExtract.replace("</script>", "")
        json_obj = json.loads(data)
        searchItems = json_obj['SearchListing']['listingCards']

        if (searchItems):
            for item in searchItems:
                # Select only the items which are not promoted by Carousell
                if not 'promoted' in item:
                    is_item_valid = False
                    for search_keyword in self.db_keywords:
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

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(CarousellSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.item_scraped, signal=signals.item_scraped)
        return spider

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
        listing_item.url = self.create_item_url(str(item['listingID']), item['title'])
        listing_item.listing_id = str(item['listingID'])            
        listing_item.seller = item['seller']['username']
        if 'photoItem' in item['media'][0]:
            listing_item.image = item['media'][0]['photoItem']['url']
        elif 'videoItem' in item['media'][0]:
            listing_item.image = item['media'][0]['videoItem']['thumbnail']['url']

        # Process the item to send a notification
        process = Processing_items()
        process.start_process_items(listing_item, search_keyword)
        
class CarousellSearch(object):
    engine = create_engine('sqlite:///Database/marabou_alert.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def __init__(self, results=30):

        db_keywords = []
    
        runner = CrawlerRunner()
        

        def generate_search_urls():
            self.base_url = ("https://www.carousell.sg/search/")
            params = {'addRecent': 'false', 'canChangeKeyword': 'false', 'includeSuggestions': 'false', 'sort_by': '3'}

            # Get keywords from DB
            self.db_keywords = [keyword_obj.keyword_str for keyword_obj in self.session.query(Keyword).all()]
            
            urls = []
            for search in self.db_keywords:
                query_url = self.base_url + urllib.parse.quote(search) + "?" + urllib.parse.urlencode(params)
                urls.append(query_url)

            return urls

        @defer.inlineCallbacks
        def crawl():

            # Remove unused keywords in DB
            db_keywords = self.session.query(Keyword).filter(~Keyword.chats.any()).all()
            for keyword_obj in db_keywords:
                self.session.delete(keyword_obj)
            self.session.commit()

            # Parse the keywords in DB to search in Carousell
            for url in generate_search_urls():
                # print ("========================== Start spider")
                # print ("url: " + url)

                # Time stamp
	            # time = arrow.get(item['time_indexed']).format('DD/MM/YYYY HH:MM')
                date = arrow.now()
                # print ("Call loop at " + str(date))
                yield runner.crawl(CarousellSpider, urls = url, keywords = self.db_keywords)
            # reactor.stop()
            # print ("Waiting for next search in " + FREQUENCY + " seconds...")
            time.sleep(FREQUENCY)
            # time.sleep(int(os.getenv('SLEEP_TIME')))
            crawl()
            
        crawl()
        reactor.run()