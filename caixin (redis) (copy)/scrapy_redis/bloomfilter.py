# 文件：Bloomfilter.py

# encoding=utf-8

# import redis
# import sys
# print  (sys.path)
import redis
from hashlib import md5

# 根据 开辟内存大小 和 种子，生成不同的hash函数
# 也就是构造上述提到的：Bloom Filter使用k个相互独立的哈希函数，我们记为 **H = { H1( ),  H2( ),  ...,  Hk( ) }**
class SimpleHash(object):
    def __init__(self, bitSize, seed):
        self.bitSize = bitSize
        self.seed = seed

    def hash(self, value):
        ret = 0
        for i in range(len(value)):
            # print(f"value[i] = {value[i]},  ord(value[i]) = {ord(value[i])}")
            ret += self.seed * ret + ord(value[i])
        # 控制hashValue的值在这个内存空间的范围
        hashValue = (self.bitSize - 1) & ret
        # print(f"value = {value}, hashValue = {hashValue}")
        return hashValue

# 在redis中初始化一个大字符串，也可以认为是在redis中开辟了一块内存空间
# 需要指定数据库名， 比如这儿用到的就是db2
# 指定使用数据块个数，也就是开辟几个这样的大字符串。
# 当数据达到非常大时，512M肯定是不够用的，可能每个位都被置为1了，所以需要开辟多个大字符串
# 大字符串名name = (key + int)
class BloomFilter(object):
    def __init__(self, host='localhost', port=6379, db=2, blockNum=1, key='bloomfilter'):
        """
        :param host: the host of Redis
        :param port: the port of Redis
        :param db: witch db in Redis
        :param blockNum: one blockNum for about 90,000,000; if you have more strings for filtering, increase it.
        :param key: the key's name in Redis
        """
        # 开启redis的服务
        self.server = redis.Redis(host=host, port=port, db=db)
        # 2^31 = 256M
        # 这是一个限制值，最大为256M，因为在redis中，字符串值可以进行伸展，伸展时，空白位置以0填充。
        self.bit_size = 1 << 31  # Redis的String类型最大容量为512M，现使用256M
        # seeds 应该就是几个特征值，个数越多，数据就会越准确，而且每一个特征值不一样，生成的hash函数就是不一样的
        self.seeds = [5, 7, 11, 13, 31, 37, 61]
        self.key = key
        self.blockNum = blockNum
        # 我也不知道这个东西具体是什么，但是代表了这7个散列函数
        self.hashfunc = []
        for seed in self.seeds:
            # 根据seed 构造出 k=7 个独立的hash函数
            self.hashfunc.append(SimpleHash(self.bit_size, seed))

    # 判断元素是否在集合中
    def isContains(self, str_input):
        if not str_input:
            return False
        # print('str_input :'+str_input)
        m5 = md5()
        # 将指纹加密
        m5.update(str_input.encode('utf-8'))
        # 先取目标字符串的md5值
        str_input = m5.hexdigest()
        # print('str_input md5 :' + str_input)
        # 再将加密的值取出来,目前还不清楚为什么要这样做，指纹已经是处理过了的
        # 我现在想，为什么不直接去使用指纹呢,我想可能就是因为指纹是40位的，而
        # md5是32位的，又节省了8位
        ret = True

        # print('int(str_input[0:2], 16):'+str(int(str_input[0:2], 16)))
        # print('str_input[0:2]:'+str_input[0:2])
        # str(int(str_input[0:2], 16)将前两位16进制的转变成10进制的
        # key为数据库的名称，
        # str(int(str_input[0:2], 16) % self.blockNum) 为取模运算，意思就是取int(str_input[0:2], 16)
        # 整除self.blockNum之后的余数，因为self.blockNum为1，所以str(int(str_input[0:2], 16) % self.blockNum)
        # 的数值是为0的, name = bloomfilter0 这么做有什么意义？可以跨块来判断了，因为如果这个东西是存在的话，就会引导到相同的
        # 块中的相同的位置，也就会在不同的块中的不同位置去比较，但是有一个问题是，内存会不会爆掉
        # 这个求模真的是写的好，对2求模的话结果只可能是0和1，对其他求模的结果也是这样，相当于随机将这些散列计算结果分散到
        # 好几个大小为256m的空间中，相当于加大了可以接受过滤的信息，这个真的好，写的太好了
        name = self.key + str(int(str_input[0:2], 16) % self.blockNum)
        # print('name:'+name)
        # 用7个散列函数处理挨个处理一遍
        for f in self.hashfunc:
            loc = f.hash(str_input)
            # print('loc:'+str(loc))
            # print('self.server.getbit(name, loc):'+str(self.server.getbit(name, loc)))
            # getbit为获取指定位置的位，name为数据库的名称
            # 如果在数据库中取的值为1的话，ret的值就为1，取的值为0，ret的值就为0，只要其中有一个值为0，ret最后的值都会
            # 为0，也就是说，7次判断中，有一次对不上就是之前不存在的。这个方法还不错
            ret = ret & self.server.getbit(name, loc)
            # print('ret:'+str(ret))
        # 如果ret返回的为0，就代表之前在数据库中不存在这个数值，如果返回为1，就是已经存在了。
        return ret

    # 将str_input映射的结果，写入到大字符串中，也就是置上相关的标志位
    def insert(self, str_input):
        m5 = md5()
        m5.update(str_input.encode('utf-8'))
        str_input = m5.hexdigest()

        name = self.key + str(int(str_input[0:2], 16) % self.blockNum)

        for f in self.hashfunc:
            loc = f.hash(str_input)
            # print(f"name = {name}, loc = {loc}")
            # 将运算得到的位置的值设置为1
            self.server.setbit(name, loc, 1)