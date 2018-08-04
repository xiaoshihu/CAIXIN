# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class CaixinItem_artcontent(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    # 用来在管道中区别我是想存进哪一个表
    # 总共有三个表，第一个表中放的是文章id，链接以及标题
    # 第二个表中放的文章的内容和文章的id
    # 评论不要了，很难及时去更新，也没多少内容
    # 还有一个问题就是，怎样将
    # type = scrapy.Field()

    ID = scrapy.Field()
    # title = scrapy.Field()
    # time = scrapy.Field()

    content = scrapy.Field()
    # 评论还是想抓取，肯定又是js文件，不知道url是否有规律可寻找
    # comment = scrapy.Field()
    pass

class CaixinItem_page(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    # 用来在管道中区别我是想存进哪一个表
    # 总共有三个表，第一个表中放的是文章id，链接以及标题
    # 第二个表中放的文章的内容和文章的id
    type = scrapy.Field()
    ID = scrapy.Field()
    title = scrapy.Field()
    time = scrapy.Field()
    url = scrapy.Field()

    pass
