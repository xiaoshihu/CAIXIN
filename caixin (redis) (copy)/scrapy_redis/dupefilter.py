import logging
import time

from scrapy.dupefilters import BaseDupeFilter
from scrapy.utils.request import request_fingerprint

from . import defaults
from .connection import get_redis_from_settings
import re

isUseBloomfilter = False
try:
    from .bloomfilter  import BloomFilter
except Exception as e:
    print(f"there is no BloomFilter, used the default redis set to dupefilter.")
else:
    isUseBloomfilter = True

logger = logging.getLogger(__name__)


# TODO: Rename class to RedisDupeFilter.
# 将scrapy里面的过滤类重新写了
class RFPDupeFilter(BaseDupeFilter):
    """Redis-based request duplicates filter.

    This class can also be used with default Scrapy's scheduler.

    """

    logger = logger

    def __init__(self, server, key, debug=False):
        """Initialize the duplicates filter.

        Parameters
        ----------
        server : redis.StrictRedis
            The redis server instance.
        key : str
            Redis key Where to store fingerprints.
        debug : bool, optional
            Whether to log filtered requests.

        """
        self.server = server
        self.key = key
        self.debug = debug
        self.logdupes = True
        self.count = 0

        if isUseBloomfilter == True:
            # 实例化一个BloomFilter对象
            self.bf = BloomFilter()

    @classmethod
    def from_settings(cls, settings):
        """Returns an instance from given settings.

        This uses by default the key ``dupefilter:<timestamp>``. When using the
        ``scrapy_redis.scheduler.Scheduler`` class, this method is not used as
        it needs to pass the spider name in the key.

        Parameters
        ----------
        settings : scrapy.settings.Settings

        Returns
        -------
        RFPDupeFilter
            A RFPDupeFilter instance.


        """
        server = get_redis_from_settings(settings)
        # XXX: This creates one-time key. needed to support to use this
        # class as standalone dupefilter with scrapy's default scheduler
        # if scrapy passes spider on open() method this wouldn't be needed
        # TODO: Use SCRAPY_JOB env as default and fallback to timestamp.
        key = defaults.DUPEFILTER_KEY % {'timestamp': int(time.time())}
        debug = settings.getbool('DUPEFILTER_DEBUG')
        return cls(server, key=key, debug=debug)

    @classmethod
    def from_crawler(cls, crawler):
        """Returns instance from crawler.

        Parameters
        ----------
        crawler : scrapy.crawler.Crawler

        Returns
        -------
        RFPDupeFilter
            Instance of RFPDupeFilter.

        """
        return cls.from_settings(crawler.settings)

    def request_seen(self, request):
        """Returns True if request was already seen.

        Parameters
        ----------
        request : scrapy.http.Request

        Returns
        -------
        bool

        """
        # # 获取到了利用request_fingerprint算法得到的链接相应的映射
        # fp = self.request_fingerprint(request)
        # # This returns the number of values added, zero if already exists.
        # # 将获取到的链接的映射写入到redis数据库里面
        #就是因为下面这个语句，才会在redis里面存在有过滤的数据
        # added = self.server.sadd(self.key, fp)
        # # 可以直接返回一个判断条件？也就是如果true，那就是已经存在了

        if isUseBloomfilter == True:
            # 使用 Bloomfilter 来对url去重
            # 使用request_fingerprint来获取链接的指纹，
            fp = self.request_fingerprint(request)
            if self.bf.isContains(fp):  # 如果已经存在
                return True
            else:
                # 不存在就插入到redis里面
                self.bf.insert(fp)
                return False
        else:
            # 使用redis默认的set进行去重
            fp = self.request_fingerprint(request)
            # This returns the number of values added, zero if already exists.
            added = self.server.sadd(self.key, fp)
        return added == 0

    def request_fingerprint(self, request):
        # 我应该可以在这里面做文章，将链接处理一下，得到自己想要的东西
        """Returns a fingerprint for a given request.

        Parameters
        ----------
        request : scrapy.http.Request

        Returns
        -------
        str

        """
        # self.count +=1
        # id = re.findall(r'(?<=id\=)\d+?(?=&)', request.url)[0]
        # print('in dupefilter'+'*'*20)
        # print(request.url)
        # print('artid:'+id)
        # print('time in dupefilter:{}'.format(self.count))

        return request_fingerprint(request)

    @classmethod
    def from_spider(cls, spider):
        settings = spider.settings
        server = get_redis_from_settings(settings)
        dupefilter_key = settings.get("SCHEDULER_DUPEFILTER_KEY", defaults.SCHEDULER_DUPEFILTER_KEY)
        key = dupefilter_key % {'spider': spider.name}
        debug = settings.getbool('DUPEFILTER_DEBUG')
        return cls(server, key=key, debug=debug)

    def close(self, reason=''):
        """Delete data on close. Called by Scrapy's scheduler.

        Parameters
        ----------
        reason : str, optional

        """
        self.clear()

    def clear(self):
        """Clears fingerprints data."""
        self.server.delete(self.key)

    def log(self, request, spider):
        """Logs given request.

        Parameters
        ----------
        request : scrapy.http.Request
        spider : scrapy.spiders.Spider

        """
        if self.debug:
            msg = "Filtered duplicate request: %(request)s"
            self.logger.debug(msg, {'request': request}, extra={'spider': spider})
        elif self.logdupes:
            msg = ("Filtered duplicate request %(request)s"
                   " - no more duplicates will be shown"
                   " (see DUPEFILTER_DEBUG to show all duplicates)")
            self.logger.debug(msg, {'request': request}, extra={'spider': spider})
            self.logdupes = False
