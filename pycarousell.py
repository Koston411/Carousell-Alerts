import re
import json
import urllib.parse
import time

import scrapy
import scrapy.crawler as crawler
from scrapy.utils.log import configure_logging
from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.signalmanager import dispatcher
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from DB_elements import Keyword
from configuration import FREQUENCY
from multiprocessing import Process, Queue
from twisted.internet import reactor

Base = declarative_base()


def sleep(_, duration=FREQUENCY):
    print(f'sleeping for: {duration}')
    time.sleep(duration)


def crawl(runner):
    d = runner.crawl(CarousellSpider)
    d.addBoth(sleep)
    d.addBoth(lambda _: crawl(runner))
    return d


def loop_crawl():
    runner = CrawlerRunner(get_project_settings())
    crawl(runner)
    reactor.run()    

class CarousellSpider(scrapy.Spider):
    name = 'carousell_search'
    allowed_domains = ['www.carousell.sg/']
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    engine = create_engine('sqlite:///Database/marabou_alert.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Remove unused keywords in DB
    db_keywords = session.query(Keyword).filter(~Keyword.chats.any()).all()
    for keyword_obj in db_keywords:
        session.delete(keyword_obj)
    session.commit()

    def generate_search_urls(session):
        base_url = ("https://www.carousell.sg/search/")
        params = {'addRecent': 'false', 'canChangeKeyword': 'false', 'includeSuggestions': 'false', 'sort_by': '3'}

        # Get keywords from DB
        db_keywords = [keyword_obj.keyword_str for keyword_obj in session.query(Keyword).all()]

        print ('--------------------------db_keywords')
        print (db_keywords)
            
        urls = []
        for search in db_keywords:
            query_url = base_url + \
            urllib.parse.quote(search) + "?" + \
            urllib.parse.urlencode(params)
            urls.append(query_url)

        return urls

    def start_requests(self):
        print ('++++++++++++++++++++++++++++++++++++++++++++++++++start_requests')
        # URL = 'https://www.carousell.sg/search/troller?addRecent=false&canChangeKeyword=false&includeSuggestions=false&sort_by=3'
        if (self.start_urls):
            yield scrapy.Request(url=self.start_urls, callback=self.response_parser, headers=self.HEADERS)

    def response_parser(self, response):
        print ('---------1')
        responseExtract = re.search(r'<script type="application/json">.*?</script>', response.text)
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
                    if not 'promoted' in item:
                        is_item_valid = False
                        for search_keyword in self.db_keywords:
                            print ('---------3')
                            search_keyword = search_keyword.lower()
                            title = item['title'].lower()
                            print (title)

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

    start_urls = generate_search_urls(session)

class CarousellSearch():
    def __init__(self, results=30):
        loop_crawl()