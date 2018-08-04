# import json
#
#
# information = open('artinformation.json', 'r', encoding='utf-8')
# art = open('artcontent.json','r',encoding='utf-8')
# art_idlist = []
# for i in art:
#     f= json.loads(i)
#     art_idlist.append(f['ID'])
#     # print(f)
#     # print(type(f))
# # print(list)
# # art_idlist = []
# # atr_urllist = []
# # art_titlelist = []
# for per in information:
#     y = json.loads(per)
#     # print(y)
#     # art_idlist.append(f['ID'])
#     if y['ID'] in art_idlist:
#         pass
#     else:
#         print(y)
# information.close()
# art.close()

