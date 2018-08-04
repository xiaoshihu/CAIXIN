import requests
import time
import scrapy
'''
    获取登陆财新网的cookie
'''
import caixin.settings

import redis

def getcookie():

    login_number = 'jQuery17208055946860981429_1524729037362'
    # 账号
    account = '18571993793'
    # 密码
    password = '5eb5330bee366cf109d4b1652bd2aa28'
    # 获取当前13位的时间戳
    millis = int(round(time.time() * 1000))
    # 登陆的链接
    headers = {'User-Agent': r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36'}
    login_url = 'https://gateway.caixin.com/api/ucenter/user/v1/loginJsonp?callback' \
                '={}&device=CaixinWebsite&account={}&password={}&rand=0.69891700220643' \
                '66&deviceType=5&unit=1&_={}'.format(login_number, account, password, millis)
    session = requests.Session()
    r = session.get(login_url,headers = headers)
    # jsonStr = r.content.decode('gbk')
    if 'SUCCESS' in r.text:
        print('logging success！')
        cookie = r.cookies.get_dict()
        return cookie
    else:
        # 如果登陆失败，直接抛出异常，关闭爬虫
        raise scrapy.exceptions.CloseSpider(reason='logging failed!')
        # return print('logging failure')
    pass

cookie = getcookie()

# 清除redis数据库中保留的过滤信息
if caixin.settings.CLEANREDIS:
    try:
        rconn_filter = redis.Redis(caixin.settings.REDIS_HOST, caixin.settings.REDIS_PORT,
                                   caixin.settings.REDIS_DB)
    except Exception:
        try:
            rconn_filter = redis.Redis(caixin.settings.REDIS_HOST, caixin.settings.REDIS_PORT)
        except Exception:
            rconn_filter = None

    if rconn_filter:
        if 'bloomfilter0' in str(rconn_filter.keys()):
            rconn_filter.delete('bloomfilter0')
        if 'bloomfilter1' in str(rconn_filter.keys()):
            rconn_filter.delete('bloomfilter1')
    print('clean redis Finish!')
