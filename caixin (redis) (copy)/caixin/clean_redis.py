# encoding=utf-8
# ------------------------------------------
#   作用：清空Redis数据，重新跑数据时用。
#   日期：2016-12-15
#   作者：九茶<http://blog.csdn.net/bone_ace>
# ------------------------------------------

'''
    这个文件的作用是清空之前的bloomfilter空间，也就是等于删除所有的过滤,其实就是直接将数据库删除了
    我现在想将这个文件作为一个扩展文件并入scrapy框架中，ok就这么做，但是这个程序的执行是在程序完成
    之后，切记，一定是要在程序做完之后。
'''

import caixin.settings

import redis

if __name__ == '__main__':
    # try:
    #     rconn = redis.Redis(caixin.settings.REDIS_HOST, caixin.settings.REDIS_PORT, caixin.settings.REDIS_DB)
    # except Exception:
    #     rconn = redis.Redis(caixin.settings.REDIS_HOST, caixin.settings.REDIS_PORT)

    try:
        rconn_filter = redis.Redis(caixin.settings.REDIS_HOST, caixin.settings.REDIS_PORT, caixin.settings.REDIS_DB)
    except Exception:
        try:
            rconn_filter = redis.Redis(caixin.settings.REDIS_HOST, caixin.settings.REDIS_PORT)
        except Exception:
            rconn_filter = None

    print(rconn_filter.keys())
    # if rconn:
    #     if 'SinaSpider:requests' in rconn.keys():
    #         rconn.delete('SinaSpider:requests')

    if rconn_filter:
        if 'bloomfilter0' in str(rconn_filter.keys()):
            print('found')
            rconn_filter.delete('bloomfilter0')
    #     if 'SinaSpider:dupefilter1' in rconn_filter.keys():
    #         rconn_filter.delete('SinaSpider:dupefilter1')
    print(rconn_filter.keys())
    print('Finish!')