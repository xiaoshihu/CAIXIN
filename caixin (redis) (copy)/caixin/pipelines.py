# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
# from caixin.items import CaixinItem_artcontent,CaixinItem_page
'''
    管道的作用是将读取到的数据进行永久化存储，当然在储存的时候还可以对数据进行分类，比如我下面的几个管道
    都进行了管道类的父类的判断，我现在的想法是作出三个管道，分别是将数据存进json文件，mongo数据库，和
    mysql数据库。
'''
import json
class JsonPipeline(object):
    def __init__(self):
        print('in pipeline!')
        self.f = open('artcontent.json','w',encoding='utf-8')
        self.f1 = open('artinformation.json', 'w', encoding='utf-8')

    def process_item(self, item, spider):
        if isinstance(item,CaixinItem_artcontent):
            data = json.dumps(dict(item), ensure_ascii=False) + '\n'
            self.f.write(data)
        else:
            data = json.dumps(dict(item), ensure_ascii=False) + '\n'
            self.f1.write(data)
        return item

    def close_spider(self,spider):
        self.f.close()
        self.f1.close()
        print('close pipeline！')

# import caixin.settings
from scrapy.conf import settings
from caixin.items import CaixinItem_artcontent,CaixinItem_page
import pymongo

# MONGO_HOST = "localhost"  # 主机IP
# MONGO_PORT = 27017  # 端口号
# MONGO_DB = "caixindata"  # 库名
# MONGO_COLL1 = "artinformation"  # 储存文章信息的表
# MONGO_COLL2 = "artcontent"  # 储存文章内容的表

class MongoPipeline(object):

    # collection_name = 'scrapy_items'

    def __init__(self):
        self.host = settings['MONGO_HOST']
        self.port = settings['MONGO_PORT']
        self.db = settings['MONGO_DB']
        self.artinf = settings['MONGO_COLL1']
        self.artcon = settings['MONGO_COLL2']
        self.clean = settings['CLEANMOGON']

    # @classmethod
    # def from_crawler(cls, crawler):
    #     return cls(
    #         mongo_uri=crawler.settings.get('MONGO_URI'),
    #         mongo_db=crawler.settings.get('MONGO_DATABASE', 'items')
    #     )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.host,self.port)
        self.db = self.client[self.db]
        # 清除mongon里面的数据
        if self.clean:
            self.db[self.artcon].remove({})
            self.db[self.artinf].remove({})
            print('clean mongo finished!')

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if isinstance(item,CaixinItem_artcontent):
            try:
                self.db[self.artcon].insert_one(dict(item))
            except Exception:
                print('insert data wrong')
        else:
            try:
                self.db[self.artinf].insert_one(dict(item))
            except Exception:
                print('insert data wrong')
        return item

import pymysql

class Mqlpipeline(object):
    def __init__(self):
        self.host = settings['MYSQL_HOST']
        self.user = settings['MYSQL_USER']
        self.port = settings['MYSQL_PORT']
        self.psw = settings['MYSQL_PSW']
        self.dbname = settings['MYSQL_DB']
        self.clean = settings['CLEANMYSQLTABLE']

        pass

    def open_spider(self, spider):
        try:
            self.db = pymysql.connect(host =self.host,user=self.user,password=self.psw,port=int(self.port),db=self.dbname,charset="utf8")
            self.cursor = self.db.cursor()
            if self.clean:
                self.cursor.execute('TRUNCATE TABLE artcontent')
                self.cursor.execute('TRUNCATE TABLE artinformation')
        except  Exception:
            raise scrapy.exceptions.CloseSpider(reason='connent mysql failed!')

    def process_item(self, item, spider):
        if isinstance(item,CaixinItem_artcontent):
            sql = 'INSERT INTO artcontent(id,content)values(%s,%s)'
            # self.cursor.execute(sql, (item['ID'], item['content']))
            # self.db.commit()
            try:
                self.cursor.execute(sql, (item['ID'], item['content']))
                self.db.commit()
            except Exception:
                self.db.rollback()
                print('insert artcontent data wrong!')
        else:
            sql = 'INSERT INTO artinformation(id,title,url,type,time)values(%s,%s,%s,%s,%s)'
            # self.cursor.execute(sql, (item['ID'], item['title'], item['url'], item['type'], item['time']))
            # self.db.commit()
            try:
                self.cursor.execute(sql, (item['ID'], item['title'], item['url'], item['type'], item['time']))
                self.db.commit()
            except Exception:
                self.db.rollback()
                print('insert artinformation data wrong！')

        return item
        # pass

    def close_spider(self, spider):
        self.db.close()



