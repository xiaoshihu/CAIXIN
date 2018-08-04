# -*- coding: utf-8 -*-

# Scrapy settings for caixin project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://doc.scrapy.org/en/latest/topics/settings.html
#     https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://doc.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'caixin'

SPIDER_MODULES = ['caixin.spiders']
NEWSPIDER_MODULE = 'caixin.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'caixin (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://doc.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 0.4
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
COOKIES_ENABLED = True

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See https://doc.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'caixin.middlewares.CaixinSpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
   'caixin.middlewares.CaixinDownloaderMiddleware': 543,
}

# Enable or disable extensions
# See https://doc.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See https://doc.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
   # 'caixin.pipelines.MongoPipeline': 300,
    'caixin.pipelines.JsonPipeline':300
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# 下面的这些是在配置scrapy-redis和redis，以后还是要拓展的

# 使用scrapy-redis的调度器
SCHEDULER = 'scrapy_redis.scheduler.Scheduler'
# 使用bloom fileter的调度器
# SCHEDULER = "scrapy_redis_bloomfilter.scheduler.Scheduler"

# 使用scrapy-redis的去重类
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
# 使用bloom fileter
# DUPEFILTER_CLASS = "scrapy_redis_bloomfilter.dupefilter.RFPDupeFilter"
# 这里是散列函数的个数，越多，数据将会越准确，出错的几率会越小
# BLOOMFILTER_HASH_NUMBER = 6
# 这里是设置用来去重的映射空间大小，为2^n  这里设置就是2^30大概为128M，这个空间越大，也就是去重的总量能更多
# BLOOMFILTER_BIT = 30
# 这里设置了在爬虫启动的时候不清空之前的消息队列，实现了续爬
SCHEDULER_PERSIST = True
# 设置scrapy-redis的调度器消息队列的类型，这里是优先级类型的，默认就是这个
# SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.SpiderSimpleQueue'

# 下面这种配置方式是一个集合，foobared为password，localhost为地址，6379为port
# REDIS_URL = 'redis://:foobared@localhost:6379'


# 配置redis的信息，下面这个代表是本地
REDIS_HOST = 'localhost'
# 配置端口，这个是默认的6379
REDIS_PORT = 6379

REDIS_DB = 2

# $ scrapy crawl fast -s CLOSESPIDER_ITEMCOUNT=10
# $ scrapy crawl fast -s CLOSESPIDER_PAGECOUNT=10
# $ scrapy crawl fast -s CLOSESPIDER_TIMEOUT=10

# CLOSESPIDER_ITEMCOUNT=30

SCHEDULER_FLUSH_ON_START = True

MYEXT_ENABLED=True      # 开启扩展
IDLE_NUMBER=1           # 配置空闲持续时间单位为 360个 ，一个时间单位为5s

# 在 EXTENSIONS 配置，激活扩展
EXTENSIONS= {
            'caixin.close_spider.RedisSpiderSmartIdleClosedExensions': 500,
        }
# 设置是否在程序开始的时候清除数据库
CLEANREDIS = True

MONGO_HOST = "localhost"  # 主机IP
MONGO_PORT = 27017  # 端口号
MONGO_DB = "caixindata"  # 库名
MONGO_COLL1 = "artinformation"  # 储存文章信息的表
MONGO_COLL2 = "artcontent"  # 储存文章内容的表
# MONGO_USER = "zhangsan"
# MONGO_PSW = "123456"

CLEANMOGON = True

MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PSW = '12345'
MYSQL_PORT = '3306'
MYSQL_DB = 'caixin'

CLEANMYSQLTABLE = True