# -*- coding: utf-8 -*-
import scrapy
import time
import re
from scrapy import cmdline
from scrapy.http import Request
import json
from caixin.items import CaixinItem_artcontent,CaixinItem_page
from scrapy_redis.spiders import RedisSpider
import logging
'''
    将这个爬虫转化成scrapy-redis爬虫之后，有多个点需要去注意：
    1-获取cookie的方式需要改变，因为我启用了续爬功能，但是下一次爬虫会从之前保存的消息队列中获取链接，会导致我在爬虫最新开始的位置
        获取cookie的方法失效，解决办法应该是在下载中间件里面添加获取cookie的方法（我的想法现在有一点问题，会重复获取（不一定
        ，因为传递cookie是必须要进行的步骤，我现在只不过是想将这个传递的步骤放到下载中间件去执行）），这个问题我已经成功的解决
        了，中间件会在每一次要发送链接的时候都调用，因此是不能在中间件里面调用获取cookie的，只能先获取了再拿过来。
    2-过滤的开关和以前还是一样的，在request函数里面添加参数dont_filter来判断是否这个发送的链接需要过滤，但是还是只是根据链接去判断
        那么我在链接里面添加的时间戳就不能存在了，但是我的想法是可以自己定义用来判重的东西，比如我在链接里面只取出一小段，像是文章的id，
        到和后面看一下修改过滤规则的办法再来重新试一下；
    3-关于redis空跑的问题，发生的原因是消息队列里面的消息取完之后，队列中没有链接可取了，但是这种情况也不是说一定是爬虫运行完毕了，
        有可能是短暂性的没有链接被丢进来，但是具体的时间长短还不知道，可以保守一点，时间加长一点。先去看看别人是怎么做的。还有一个点就是
        消息队列空了不代表pipeline是空的，也不代表download是空的阿，不能仅仅只依靠这个去解决。
    4-现在正在尝试使用bloomfilter来去重，去重的方式变化了，之前的方式是首先将链接的处理一下，得到链接指纹，再将链接指纹存入进redis里面
        ，每次获取request之后，将处理链接的指纹与库中的链接指纹做对比，如果存在，就会抛弃这个request，如果不存在，将指纹加入到redis库中，
        修改的思路是这样的，还是采用redis-scrapy的调度器，每次获取到request之后，调用指纹处理，获取链接的指纹，再将指纹处理一下，将指纹映
        射到之前在redis里面申请的一大块储存空间中，如果其中有的映射位为0，说明之前没有映射过这个指纹，返回标记值，接着去请求这个链接，如果
        映射位全部位1，说明之前已经映射过了，也就是这个链接之前是存在的，丢弃这个链接。思路还是比较清楚，我现在的疑问是：
        1.还是不清楚具体的
        从消息队列中获取request，再处理request，再比较指纹，或存在后丢弃，或不存在，改变bloomfilter位值的值，这些具体的过程还是有点不清
        楚；
        2.这个很大的储存块bloomfilter，是怎么在爬虫关闭之后储存到redis里面的，如果我想清空bloomfilter，原理应该是将这么一大块空间
        的位全部变成0，具体的过程怎么实现；
        3.还是之前问题1相关的问题，就是之前会存在的过滤指纹的数据库去哪了，说来说去还是对里面的具体实现过程不清楚；
    5-昨天把具体的过程已经弄的算是比较清楚了，现在厘清一下过程：调度器首先接受request发送过来的信号（所有链接都用信号简称）-->首先判断这个request
        是否开启了去重的开关，如果开启，再将信号传递给去重比较函数-->去重比较函数中首先获取信号的指纹-->将指纹传递给映射函数（也就是bloomfilter）-->
        获取指纹的md5-->再利用散列函数计算其再数据库的位置，再比较这个位置的值是否为1，如果7次散列函数的计算结果和数据库中相对应的位置比较都是1，
        就说明这个值之前映射过，也就是其之前就存在了，信号就不会被存进信号队列中，直接舍弃-->如果其之前并不存在，将信号传递给插入函数-->插入函数会
        再一次调用7个散列函数计算出7个位置，并将其对应位置的数据库中的值变成1，到目前的步骤，数据库中已经存在了这个信号的映射-->再返回到调度器中
        -->调度器将信号push进消息队列；基本上上面就是一个信号从发出到进队列的过程。
    6-我去尝试一下，看看头之类的是什么时候加入到链接中的，是在消息在进入队列之后，再从队列中取出信息，发送信号之前再添加头文件和cookie；
    7-中间还是有一些可以优化的问题，比如之前的散列函数计算基本上就算是重复计算了两次，如果不存在的话，可否把之前的计算结果直接拿的插入函数中
        也许可能是爬虫的主要瓶颈其实是在下载上面，这些点没有这么重要；
'''

class CaixincrawlSpider(RedisSpider):
    # 设置日志的级别，目前还不知道是怎么使用的
    artinformation_count = 0
    article_count = 0
    logging.getLogger('request').setLevel(logging.WARNING)
    login_number = 'jQuery17208055946860981429_1524729037362'
    name = 'caixincrawl'
    allowed_domains = ['caixin.com']
    # start_urls = ['http://caixin.com/']
    headers = {
        'User-Agent': r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36'}

    def start_requests(self):
        url = 'http://international.caixin.com/'

        return [Request(url=url, callback=self.first_parse,dont_filter=True)]
        # return [Request(url=url, callback=self.parse)]
    def parse(self, response):
        print('spider run finished!')
        pass

    def first_parse(self, response):
        # 这些是总的分类，之后还需要进一步去细分
        # 这两个字典是用来存发标题和对应的链接的，用于之后判断是否需要抓取以及怎么抓取
        # type_dict = {}
        # 我也可以用这种方法来获取cookies池，我的这种方法可能更加好一些，因为我支持异步
        # 如果cookie池足够大，我还可以写一个item将获取到的cookie利用管道储存进redis中
        # 这种获取请求头的办法还是不错的
        # print(response.request.headers.getlist('Cookie'))
        # print(response.request.headers)
        header = {
            'Referer': 'http://international.caixin.com/',
            'User-Agent': r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36'}
        # total_dict = {}
        # caixin_map = response.xpath('')

        # 又要重新来取标题和链接了，和首页是一样的规律
        # 欧洲北美
        # 亚太地区
        # 中东北非
        # 新兴市场
        # 中国外交
        world_area = ['欧洲北美', '亚太地区', '中东北非', '新兴市场', '中国外交']
        world = response.xpath('//a[@target="_blank"]/@href').extract()[0:-1]
        type_economy = response.xpath('//div[@id="subnav1"]/a')
        type_finance = response.xpath('//div[@id="subnav2"]/a')
        type_company = response.xpath('//div[@id="subnav3"]/a')
        type_cnbc = response.xpath('//div[@id="subnav12"]/a')
        type_plutonomy = response.xpath('//div[@id="subnav4"]/a')
        type_world = response.xpath('//div[@id="subnav5"]/a')
        type_viewpoint = response.xpath('//div[@id="subnav6"]/a')
        type_culture = response.xpath('//div[@id="subnav7"]/a')
        type_blog = response.xpath('//div[@id="subnav8"]/a')
        type_publication = response.xpath('//div[@id="subnav9"]/a')
        type_picture = response.xpath('//div[@id="subnav10"]/a')
        type_video = response.xpath('//div[@id="subnav11"]/a')
        type_number = response.xpath('//div[@id="subnav15"]/a')

        type_dict = {}

        economy_urllist = type_economy.xpath('./@href').extract()
        economy_titlelist = type_economy.xpath('./text()').extract()

        finance_urllist = type_finance.xpath('./@href').extract()
        finance_titlelist = type_finance.xpath('./text()').extract()

        company_urllist = type_company.xpath('./@href').extract()
        company_titlelist = type_company.xpath('./text()').extract()

        cnbc_urllist = type_cnbc.xpath('./@href').extract()
        cnbc_titlelist = type_cnbc.xpath('./text()').extract()

        plutonomy_urllist = type_plutonomy.xpath('./@href').extract()
        plutonomy_titlelist = type_plutonomy.xpath('./text()').extract()

        world_urllist = type_world.xpath('./@href').extract()
        world_titlelist = type_world.xpath('./text()').extract()

        viewpoint_urllist = type_viewpoint.xpath('./@href').extract()
        viewpoint_titlelist = type_viewpoint.xpath('./text()').extract()

        culture_urllist = type_culture.xpath('./@href').extract()
        culture_titlelist = type_culture.xpath('./text()').extract()

        blog_urllist = type_blog.xpath('./@href').extract()
        blog_titlelist = type_blog.xpath('./text()').extract()

        publication_urllist = type_publication.xpath('./@href').extract()
        publication_titlelist = type_publication.xpath('./text()').extract()

        picture_urllist = type_picture.xpath('./@href').extract()
        picture_titlelist = type_picture.xpath('./text()').extract()

        video_urllist = type_video.xpath('./@href').extract()
        video_titlelist = type_video.xpath('./text()').extract()

        number_urllist = type_number.xpath('./@href').extract()
        number_titlelist = type_number.xpath('./text()').extract()

        urllist_list = [economy_urllist, finance_urllist, company_urllist, cnbc_urllist, plutonomy_urllist,
                        world_urllist, \
                        viewpoint_urllist, culture_urllist, blog_urllist, publication_urllist, picture_urllist,
                        video_urllist, number_urllist, world]
        titlelist_list = [economy_titlelist, finance_titlelist, company_titlelist, cnbc_titlelist, plutonomy_titlelist,
                          world_titlelist, \
                          viewpoint_titlelist, culture_titlelist, blog_titlelist, publication_titlelist,
                          picture_titlelist, video_titlelist, number_titlelist, world_area]
        x = 0
        # 将上面的两个序列中的元素写成一个字典
        while x < len(urllist_list):
            y = 0
            while y < len(urllist_list[x]):
                type_dict[titlelist_list[x][y]] = urllist_list[x][y]
                y += 1
            x += 1
        # print(type_dict)
        # 下面的内容是我不想抓取的，到时候取出key比较一下就可以了
        # 也许我不需要将这些都踢出来，将剩下的分类就可以了
        useless = ['天天预测', '中国聚焦', '全球市场', '全球公司', '科技创业', '人物访谈', '全球直播 ', '视听', '谢平互金九讲', '王烁学习报告', \
                   '明朝历史传奇小说《赤龙》', '短视频', '音频', '财新时间', '一线人物', 'BBC视野', '微纪录', '财新PMI', '互动新闻']
        # 网页类型分类，因为之后调用的数据处理函数是不同的
        # 动态加载的网页的分类
        dynamic = ['欢乐财新闻', 'TMT', '大家谈', '汽车', '无恙', '新科技','财新名家','旁观中国']
        # 翻页类型的网页的分类
        # 我还是直接将比较特殊的分出来
        # pageturn = ['读懂央行','理解万税','','']
        # 周刊类型处理的网页的分类
        publication = ['《中国改革》','《比较》']
        # 全是图片的
        picture = ['滚动新闻','图片故事','专题报道','一周天下','一周人物','奇闻趣事','财新独家']
        # 下面是比较特殊的
        special = ['反腐纪事', '火线评论','经济','人文','生活','科技','最新更新','钩沉','纪念日','民生']
        for title in type_dict:
            # print(title + ':' + type_dict[title])
            if title in useless:
                continue
            elif title in dynamic:
                continue
            elif title in publication:
                continue
            elif title in picture:
                continue
            elif title in special:
                continue
            else:
                yield Request(url=type_dict[title],callback=
                self.turn_page_parse,headers=header,dont_filter=True)
            # 抓取其中的一个链接来看看,dont_filter=True
            # break
                # print('发送的分类的链接：'+type_dict[title])
            # if title in dynamic or title in special:
            #     print(title + ':' + type_dict[title])
            #     continue
            # else:
        pass
                # print(title + ':' + type_dict[title])
            #     # 这里估计还是需要再分类的
            #     url = type_dict[title]
            #     yield Request(url=url,meta={'cookiejar':response.meta['cookiejar']},callback=self.first_parse,headers=header)
            # print(title + ':' + type_dict[title])

    # 迭代发出页面的请求，这里应该作一下区分，分为动态页面以及翻页页面
    # for urllist in urllist_list:
    #     for url in urllist:
    #         yield Request(url=url,meta={'cookiejar':response.meta['cookiejar']},callback=self.first_parse,headers=self.headers,errback=self.errback)
    # 这个函数是专门处理这种翻页的页面的
    # 天下事和思想精选两个分类是需要动态渲染，然后模拟按钮点击之后才能知道总页面的
    # 下面这个函数可以作为有两个作用的函数：1.遍历分类下面的所有页面。2.遍历每个分类页面下面的文章链接；
    def turn_page_parse(self,response):
        # 这里加了一个判断，这个判断是用来遍历页面中的文章的链接的
        # 我的想法改变了，将遍历页面文章的链接全部放到一个函数里面
        # 这样作的好处是程序思路很清晰，但是所有分类的首页面将会重新下载一遍
        # 重新下载就重新下载吧，也没多少个，把这里的去重关掉

        # if 'index' in response.url:
        #     pass
        # 如果index不在链接里面的话，就能说明这个链接是第一发过来
        # else:
        header = {
            'Referer': response.url,
            'User-Agent': r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36'}
        title = response.xpath('//span[@id="pL"]/text()').extract()[0]
        # print(title+':'+response.url)
        # print(response.url)
        page_extract = response.xpath('//a[@class="pageNext"]/@href').extract()[0]
        page_number = re.findall(r'\d+',page_extract)
        if page_number:
            # print(title + ':' + response.url+':'+page_number[0])

            page = 1
            while page <=int(page_number[0]):
                page_url = 'index-{}.html'.format(page)
                url = response.url+page_url
                yield Request(url=url,
                              callback=self.pagetraversal_parse, headers=header,dont_filter=True)
                # print('发送的页面的链接：' + url)
                page+=1
            # pass
        # 天下事和思想精选两个分类是需要动态渲染，然后模拟按钮点击之后才能知道总页面的
        # 是这两个页面的跳转是由js执行的，我能找出是哪一个js执行的吗
        # 没有必要进行动态渲染，可以直接找到其的js文件，这个的就写在html中
        else:
            # print(response.body)
            # print(response.xpath('//head/title/text()'))
            pagedeal = response.xpath('//script[@language="JavaScript"]').extract()[0]
            maxpage = re.findall('(?<=maxPage \= ).+?(?=;)',pagedeal)[0]
            # print(maxpage)
            i = 1
            while i<maxpage:
                url = 'http://opinion.caixin.com/sxjx/index-{}.html'.format(i)
                yield Request(url=url,callback=self.pagetraversal_parse, headers=header,dont_filter=True)
                i+=1
            pass
        # 再一次将首页的链接发送出去，这次的回调函数是页面链接遍历发送函数
        # 我尝试了一个很错误的问题，就是需要调用一个类的时候，
        # instance = CaixincrawlSpider()
        # instance(response)
        # print('重新发送首页的链接')
        # return Request(url=response.url, meta={'cookiejar': response.meta['cookiejar']},
        #                       callback=self.pagetraversal_parse, headers=header,dont_filter=True)
        # 但是不管怎么样，首页的页面是需要处理的，下面就是遍历文章的链接
        # 其实类内函数调用是可以实现的，条件是必须要将类实例化，但是scrapy怎么在做我就不知道了，那就不能用这个方法了
        # self.pagetraversal_parse(response)

        # 我没有重新发送首页链接，而是直接将这页的内容解析了

        item = CaixinItem_page()

        page = 1
        header = {
            'Referer': response.url,
            'User-Agent': r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36'}
        title = response.xpath('//span[@id="pL"]/text()').extract()[0]
        artlist = response.xpath('//div[@class="stitXtuwen_list"]//dd/h4')
        for art in artlist:
            arturl = art.xpath('./a/@href').extract()
            if 'video' in arturl[0]:
                pass
            else:
                arttitle = art.xpath('./a/text()').extract()
                artcharge = art.xpath('./span/@title').extract()
                id = re.findall(r'(?<=\d/)\d+?(?=\.)', arturl[0])[0]

                item['ID'] = id
                item['type'] = title
                item['title'] = arttitle[0]
                item['time'] = re.findall(r'(?<=m/).*?(?=/)', arturl[0])[0]
                item['url'] = arturl[0]
                # 将文章的信息之类的存进管道中
                yield item
                self.artinformation_count+=1
                print('self.artinformation_count:'+str(self.artinformation_count))
                if '免费' in artcharge:
                    print('这里有免费的文章：' + response.url)
                    # pass
                    # url = arturl
                    yield Request(url=arturl[0], callback=self.free_parse,
                                  headers=header)
                else:
                    # id = re.findall(r'(?<=\d/)\d+?(?=\.)', arturl[0])[0]
                    # millis = int(round(time.time() * 1000))
                    header['Referer'] = arturl[0]
                    url = 'http://gateway.caixin.com/api/newauth/checkAuthByIdJsonp?callback={}&type=0&id={}' \
                          '&page={}&rand=0.4677799755726806&source=http%3A%2F%2Fwww.caixin.com%2F&feeCode=null'.format(
                        self.login_number, id, page)
                    yield Request(url=url, callback=self.article_parse,
                                  headers=header)

        pass

    # 首页页面的处理
    # 这里需要修改了，因为我已经发现了另外一个比较方便的方法，就是直接去请求js文件，这样的话就不用渲染页面了，而且之前我还想到了
    # 这个页面到后来会变的无穷大，所以我现在想到的办法应该还是比较好的
    # 这里发送的链接有问题，同一个链接不知道发送了多少次
    # 由于链接带有时间戳的缘故，导致去重失败，不能使用scrapy本身的去重的功能了是时候引进redis数据库了，将文章的链接储存在
    # 这个在内存中的数据库，每次从这个数据库中读取数据来去重。
    def pagetraversal_parse(self, response):
        item = CaixinItem_page()

        page = 1
        header = {
            'Referer': response.url,
            'User-Agent': r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36'}
        title = response.xpath('//span[@id="pL"]/text()').extract()[0]
        # type_art = response.xpath('//span[@id="pL"]/text()').extract()[0]
        # print(title+':'+response.url)
        # artlist = response.xpath('//div[@class="stitXtuwen_list"]//dd/h4')
        # arturl = response.xpath('//div[@class="stitXtuwen_list"]//dd/h4/a/@href').extract()
        # arttitle = response.xpath('//div[@class="stitXtuwen_list"]//dd/h4/a/text()').extract()
        # artcharge = response.xpath('//div[@class="stitXtuwen_list"]//dd/h4/span/@title').extract()
        # item['type'] = title
        artlist = response.xpath('//div[@class="stitXtuwen_list"]//dd/h4')
        for art in artlist:
            arturl = art.xpath('./a/@href').extract()
            if 'video' in arturl:
                pass
            else:
                arttitle = art.xpath('./a/text()').extract()
                artcharge = art.xpath('./span/@title').extract()
                id = re.findall(r'(?<=\d/)\d+?(?=\.)', arturl[0])[0]

                item['ID']=id
                item['type']=title
                item['title']=arttitle[0]
                item['time']=re.findall(r'(?<=m/).*?(?=/)',arturl[0])[0]
                item['url'] = arturl[0]
                # 将文章的信息之类的存进管道中
                yield item
                self.artinformation_count += 1
                print('self.artinformation_count:'+str(self.artinformation_count))
                if '免费' in artcharge:
                    print('这里有免费的文章：'+response.url)
                    # pass
                    # url = arturl
                    yield Request(url=arturl[0], callback=self.free_parse,
                              headers=header)
                else:
                    # id = re.findall(r'(?<=\d/)\d+?(?=\.)', arturl[0])[0]
                    # millis = int(round(time.time() * 1000))
                    # 利用这个头文件的参数去传递我想要传递下去的数据
                    header['Referer'] = arturl[0]
                    url = 'http://gateway.caixin.com/api/newauth/checkAuthByIdJsonp?callback={}&type=0&id={}' \
                                      '&page={}&rand=0.4677799755726806&source=http%3A%2F%2Fwww.caixin.com%2F&feeCode=null&'.format(
                                self.login_number, id, page)
                    yield Request(url=url, callback=self.article_parse,
                                  headers=header)
                # print('发送的文章链接:'+url)
        # if '免费' in artcharge:
        #     pass
        # else:

        # # print(response.body)
        # # content = str(response.body).encode('utf-8')
        # # print(content)
        # # page = 0
        # # 这里之后可能是要修改的，因为后面获取文章的标题和id的方法可能是需要动态加载
        # article_title = response.xpath('//div[@id="listArticle"]//h4/a/text()').extract()
        # article_link = response.xpath('//div[@id="listArticle"]//h4/a/@href').extract()
        #
        # article_charge = response.xpath('//div[@id="listArticle"]//h4/div/@title').extract()
        #
        # page = 1
        #
        # # test_url = 'http://gateway.caixin.com/api/newauth/checkAuthByIdJsonp?callback=jQuery17203978944846086885_1524815028655&type=0&id=101237195&page=0&rand=0.14719535473252687&source=http%3A%2F%2Fsearch.caixin.com%2Fsearch%2Fsearch.jsp&feeCode=null&_=1524815029317'
        #
        # length_article = len(article_title)
        # i = 0
        # # 在这里不应该直接发送跳转到文章的链接，应该取出文章的编号就好了
        # while i < length_article:
        #     # 下面的这三个数据应该是需要保存起来的，文章ID，标题，文章链接，单独作一个数据库
        #     print('articletitle:', article_title[i])
        #     print('articlelink', article_link[i])
        #     # 文章发布时间
        #     art_time = re.findall(r'(?<=m/).*?(?=/)', article_link[i])[0]
        #     id = re.findall(r'(?<=\d/)\d+?(?=\.)', article_link[i])[0]
        #
        #     # 缺一个管道的操作
        #
        #     millis = int(round(time.time() * 1000))
        #     if '收费' in article_charge[i]:
        #         url = 'http://gateway.caixin.com/api/newauth/checkAuthByIdJsonp?callback={}&type=0&id={}' \
        #               '&page={}&rand=0.4677799755726806&source=http%3A%2F%2Fwww.caixin.com%2F&feeCode=null&_={}'.format(
        #             self.login_number, id, page, millis)
        #         i += 1
        #         yield Request(url=url, meta={'cookiejar': response.meta['cookiejar']}, callback=self.article_parse,
        #                       headers=self.headers)
        #     else:
        #         url = article_link[i]
                # yield Request(url=url, meta={'cookiejar': response.meta['cookiejar']}, callback=self.free_parse,
                #               headers=self.headers)
        #         i += 1
        #     # break
        pass


    # 抓取不到，还是需要抓取js文件，我之前就知道了，其实，那个我所看到的页面是js文件生成的，可以做成动态的
    # 财新这么做也只是为了方便让不是会员的人能看着一部分。
    # js页面处理
    def article_parse(self, response):
        # 将文章的内容和id保存起来
        # print(response.url)
        # print(response.body)
        # content = response.xpath('//div[@id="Main_Content_Val"]/p/text()').extract()
        # content = '\n'.join(content).split()
        # print(response.meta)
        # 我要找的东西不在doc里面，而在js里面，但是我之前看到的整个页面的元素其实是
        # id = response.xpath('//ul[@id="showLoginId"]').extract()
        # print(id)
        # 这样能将byte类型的变成str类型的去输出，这里并不是编码的问题，而是我现在读取到的文件就是byte
        # 类型的，我需要将其转化为str类型的,可能之前就是utf-8类型的，这里可以设置，也可以空缺，也就是不改变编码类型
        # print(response.body.decode('utf-8'))
        # print(type(response.body.decode()))
        # 这里经过一系列比较复杂的转化将得到的网页文件变成我想要的字典的格式
        # 也是为了之后比较方便的存储,还有就是网页有多个页面的时候,我需要将里面的
        # totalpage参数拿出来,
        # 正在使用splash了，心中还是有几个问题，首先是财新网自己的问题，一个分类下面所有的页面难道都需要用加载更多文章去加载？
        # 我不知道这个页面最后会是多大，并且，我现在还不了解splash的渲染方式，像这一种之前有的是否还需要去渲染？
        str_respones = response.body.decode('utf-8')
        # 声明一个用来存储信息的对象
        item = CaixinItem_artcontent()
        if 'content' in str_respones:
            # print(str_respones)
            useless = re.findall(r'/\*.*?o\(', str_respones)[0]
            useless2 = re.findall(r'\)\".*?;', str_respones)[0]
            art_dict = str_respones.replace(useless, '').replace(useless2, '').replace('\\', '')
            content = re.findall(r'(?<=t\":\").*?(?=\",\"f)', art_dict)[0]
            content2 = content.replace('\"', '\'')
            # 上面的步骤都是在去除没有用的信息
            art_dict = art_dict.replace(content, content2)
            # 将离散的数据变成字典的格式
            content_dict = json.loads(art_dict)
            # 获取文章的id，到时候和内容存在一起
            id = re.findall(r'(?<=id\=)\d*?(?=&)', response.url)[0]
            # 判断文章否有多页
            # content_dict已经是字典了
            # print(content_dict['totalPage'])
            if content_dict['totalPage'] == 0:
                # print(content_dict['totalPage'])
                # pass
                # print('显示文章的链接：' + response.url)
                # 如果totalPage参数为0，则文章只有一页
                # id = re.findall(r'(?<=id\=)\d*?(?=&)',response.url)[0]
                pure_art = content_dict['content']
                # 从内容中获取到了文章里面的图片链接
                picture_list = re.findall(r'(?<=src\=\").*?jpg', content_dict['content'])
                # 会有许多重复的结果,如果重复去替代很浪费时间,新建一个序列去储存,每一次代替之前看是否在数列中
                useless_art = re.findall(r'<.*?>', pure_art)
                re_use = []
                for useless_art_element in useless_art:
                    if useless_art_element in re_use:
                        continue
                    else:
                        re_use.append(useless_art_element)
                        pure_art = pure_art.replace(useless_art_element, '')
                pure_art = pure_art.strip()
                # print(pure_art)
                # pure_art = content_dict['content']
                item['ID'] = id
                item['content'] = pure_art
                yield item
                self.article_count+=1
                print('self.article_count:'+str(self.article_count))
            else:
                print(content_dict['totalPage'])
                print('有多页的链接：'+response.url)
                # 进入这里的条件首先就是有多页
                if content_dict['page'] == 1:
                    # 这个代表是多页文章的链接第一次过来
                    # 如果页面不止一页,就去抓取第0页
                    print('have another page!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                    # 将链接中的页面改为page=0
                    url = response.url.replace('page=1', 'page=0')
                    # millis = int(round(time.time() * 1000))
                    # url_time = re.findall(r'(?<=\&\_\=)\d+?\b', url)[0]
                    # url = url.replace( url_time,str(millis))
                    # print(url)
                    # 为什么非要用yield来发送链接
                    yield Request(url=url, callback=self.article_parse,
                                   headers=self.headers)
                    print('request again!')
                else:
                    # 在这里就能判断这是文章的链接第二次发过来
                    print('mulpage deal')
                    pure_art = content_dict['content']
                    # 从内容中获取到了文章里面的图片链接
                    picture_list = re.findall(r'(?<=src\=\").*?jpg', content_dict['content'])
                    useless_art = re.findall(r'<.*?>', pure_art)
                    re_use = []
                    for useless_art_element in useless_art:
                        if useless_art_element in re_use:
                            continue
                        else:
                            re_use.append(useless_art_element)
                            pure_art = pure_art.replace(useless_art_element, '')
                    pure_art = pure_art.strip()
                    # print(pure_art)
                    item['ID'] = id
                    item['content'] = pure_art
                    yield item
                    self.article_count += 1
                    print('self.article_count:'+str(self.article_count))
        else:
            print('response.request')
            print(response.request.headers.get('Referer').decode('utf-8'))
            otherurl = response.request.headers.get('Referer').decode('utf-8')
            yield Request(url=otherurl, callback=self.free_parse,
                                   headers=self.headers)
            pass

    # 免费文章处理
    def free_parse(self, response):
        # 最后需要将文章的id和文章的内容保存起来,还有时间
        # 抓取文章的id
        item = CaixinItem_artcontent()
        art_id = re.findall(r'(?<=\d/)\d+?(?=\.)', response.url)[0]
        # id = re.findall(r'(?<=\d/)\d+?(?=\.)', article_link[i])[0]
        paragraph_list = response.xpath('//div[@id="Main_Content_Val"]/p')
        paragraph_content_list = paragraph_list.xpath('string(.)').extract()
        paragraph_content = '\n'.join(paragraph_content_list)
        # print('free art')
        # print(paragraph_content)
        item['ID'] = art_id
        item['content'] = paragraph_content
        yield item

        pass

    # def errback(self):
    #     print('request was wrong!')
    #     pass

if __name__ == '__main__':
    cmdline.execute('scrapy crawl caixincrawl'.split(' '))