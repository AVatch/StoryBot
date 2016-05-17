import scrapy
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors import LinkExtractor
from promptSpider.items import PromptItem

class RedditWPSpider(CrawlSpider):
    name = "redditWP"
    allowed_domains = ["reddit.com"]
    start_urls = [
        "https://www.reddit.com/r/WritingPrompts/"
    ]
    
    rules = [
        # Traverse the in the /r/WritingPrompts subreddit.
        Rule(LinkExtractor(
        	allow=['/r/WritingPrompts/\?count=\d*&after=\w*']),
        	callback='parse_prompt',
        	follow=True),
    ]
    
    
    def parse_prompt(self, response):
        # p > .title > a > text
        # //p[@class="title"]/a/text()
        for item in response.xpath('//p[@class="title"]'):
            prompt = item.xpath('a/text()').extract()[0]
            link = item.xpath('a/@href').extract()[0]
            
            if '[wp]' in prompt.lower():
                # save item
                prompt_item = PromptItem()
                prompt_item['prompt'] = prompt
                prompt_item['link'] = response.urljoin(link)
                yield prompt_item
        