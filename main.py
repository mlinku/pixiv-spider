# -*- coding: utf-8 -*- 
# @Time : 2021/7/16 13:27 
# @Author : mianlyst
# @File : test2.py
'''
大致思路：
-登录
    -使用session进行操作
    -寻找request url 和 form data
    -向request url post form data
-获取排行榜
    -采用抓包的方式获取传送的json值分析取出图片的各种信息
    -对获取的信息进行下载储存
-获取作者作品
    -通过用户id向https://www.pixiv.net/ajax/user/86328/profile/all?lang=zh发送GET请求 这一步需要模拟登录这里输入cookie或者sessoin返回携带
    -利用上个获得的id组成一条新的url发送请求处理获得图片url
    -利用图片url进行下载储存
-获取标签作品
    -对输入的标签进行url编码得到url
    -利用url得到图片信息
    -处理下载储存
'''
import os
import re
from time import sleep
from urllib import parse
import requests
from lxml import etree


class PixivSpider:
    def __init__(self):
        # 用于获取模拟登录的post_key
        self.login_url = 'https://accounts.pixiv.net/login?return_to=https%3A%2F%2Fwww.pixiv.net%2Franking.php%3Fmode%3Dmonthly%26content%3Dillust&lang=zh&source=pc&view_type=page'
        # 用于发送登录请求
        self.request_url = 'https://accounts.pixiv.net/api/login?lang=zh'
        # 用于获取排行榜数据
        self.rank_img_url = 'https://www.pixiv.net/ranking.php?mode={1}{2}{3}&p={0}&format=json'
        # 图片下载referer值的公用前缀
        self.base_url = 'https://www.pixiv.net/artworks/'
        # 用户id搜索的第一个获取图片idurl
        self.id_sech_url = 'https://www.pixiv.net/ajax/user/%d/profile/all?lang=zh'
        self.id_sech_referer = 'https://www.pixiv.net/users/%d'
        # 获取用户图片链接的前缀
        self.id_url_front = 'https://www.pixiv.net/ajax/user/%d/profile/illusts?'
        # 获取用户图片链接的后缀
        self.id_url_beside = '&work_category=illustManga&is_first_page={0}&lang=zh'
        self.id_base_url = 'https://www.pixiv.net/users/%d/artworks'
        self.tag_url_beside = '&order=date_d&mode=all&p=1&s_mode=s_tag_full&type=all&lang=zh'
        self.tag_base_url = 'https://www.pixiv.net/ajax/search/artworks/{0}?word={0}&order=date_d&mode={1}&p=1&s_mode=s_tag_full&type=all&lang=zh'

        self.common_header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

        self.cookie_header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'cookie': "irst_visit_datetime_pc=2022-09-08+22%3A49%3A28; p_ab_id=5; p_ab_id_2=9; p_ab_d_id=361732582; yuid_b=JkZCEGU; __utmz=235335808.1662644970.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); _fbp=fb.1.1662644971312.667664842; PHPSESSID=81243320_sMaZZse2RZMg4H2GW7bXNJtfpWVP0GFS; device_token=174673729283893a44b05ad30e08b3bf; c_type=9; privacy_policy_notification=0; a_type=0; b_type=1; _im_vid=01GCEP61KDRXMB06MJP65GT263; _im_uid.3929=i.siaaAacmQUm8VfV3qLFlKg; login_ever=yes; __utmv=235335808.|2=login%20ever=yes=1^3=plan=normal=1^5=gender=male=1^6=user_id=81243320=1^9=p_ab_id=5=1^10=p_ab_id_2=9=1^11=lang=zh=1; _gid=GA1.2.1286714960.1663858970; __cf_bm=RxuL0tVT0U7HeC66fua8PrmcQdkm2kHi4Bm_ea5MkLY-1663858971-0-Adnm17f8rcHlAFnC6uGOfKTCaLD0rdDZt6bSnE1IxbEV6d+nM6fWQ/IAYbnJZl/x5XDkovQ6uh6cPFH6dY4ExYnjTJID+m1tWfz0JlCMjY/zlK/HkWotjV5Jna3ohtmJV6aKFYugg0aUg2xGmla/Ia4+hzCNLZ5avbIvxTBpZMMPTQKhuk6uHLzzeYbQGNBtXA==; __utma=235335808.1297637551.1662644969.1662644970.1663858975.2; __utmc=235335808; __utmt=1; QSI_S_ZN_5hF4My7Ad6VNNAi=v:0:0; privacy_policy_agreement=5; _ga=GA1.2.1297637551.1662644969; __utmb=235335808.8.10.1663858975; cto_bundle=stf7yl9QVTZDcTNWUFIxNWhDOU5qTnZPTHh0SlpxWHUzZ0FNZ3BwMFlSS3BXSFBNQ0g2aFEyZE5KeThMV25vQUJXd3FpcnNtSkFuRWQlMkJaUG5zUkc4MGo2WElZMlBibVhPNTRzS2NsbnpoaHB1Mmk0VG1RdndEa2NqYXpOamlMTWI4NENSc2JnJTJCWiUyQlBkdDlZMFR3Z3VWQnpoTnclM0QlM0Q; _ga_75BBYNYN9J=GS1.1.1663858974.2.1.1663859152.0.0.0"
        }
        # 模拟登录的data
        self.pixiv_id = ''
        self.password = ''
        self.post_key = []
        self.source = 'pc'
        self.return_to = 'https://www.pixiv.net/'
        self.recaptcha_enterprise_score_token = '03AGdBq27reTb5aiAclEIsFwSYG7O4ipWYLg8B0oRq2ibebDXxzZfqYT_EnRV9jdLJ1VilPZOE30AKEohyBJWBW8SKr9fc4jwpF1zH9mcRXveIP9s6X8UGRn_anM3FjrQuirOq5gzzNQDDmzICMlijlWnYn_q-U_q8Kg-SVSS0ITL8_zdfGvuoM0pTeZYMn51F3-nkcY8GnHzoZNC0PyBqdIVl1pTbzYQ5Cmxu2Bvcd46sW_kLFAg9ChgufxhU-FZ67f2DXepKbVeWqiB-4iOLXLC8P5oTKA7o-tLywpShZIASzx9ynPsV3L-WXfeF5BTJppSrbXKaUqEl92qr-28bBzgGrk9590bdpL8AbduB18EO1RZr3hHSa5xbjqX4di_ilwdKgNrxP63SNur8B8ZDEvB43BeHpCC1pTaC5sbqqUaTex3W3BmGtk1_9a2_Qmg3RIEh5tyaL3_maeeEswboGkaDgvBNUF60wwvdsP_ScoNA6GTy1yqSK7JXI2Jao-FlfVkgnt9R7EyHFi_MySkBIH7LlhVsQPD10ScqHWZIxZ4jHlAqoT5etYt4oLICwcsfvW5pfgPMxWktrZLkoPYxedvmaQbWKQYqOwFDl0wiDsadD3GXYjbzXQfnazplpUz1AzCG4DWeC-3lK-PitbF5nQ9kEO7pKELWlLjk7_ZEHsMvgaR3r0d45ZqCzo1YsqskzGC0t5eA9Npz1aoTBYZFtQdzqzd2V4-soFVg_lcP4xmj_Kzoxj9oukhnNnvaVb1N10UJq5t5dJDKZYkSuTEX_wXOwLbh_g5UxGpM-1qUCFjGd5rx8-TgFJ4_ncFnbL_GJH26gimhBnNMPdY9WpGRvk1qKNHeo6hCgcL3xyftBD-Y-4awPFb54wAIX1Fdidj-n0jOFuf5_cVIBsrNCi95j9SNW-PTfc3sY6qY1GDZttJ1ykymJ2MQ5WNQk-9aLJp1L8Yrhqbz4LepgqXOtix_LO06Kr5mjB7pHQwhXgoePeuVGeEX6aTOCDRKizS2t01EdKS7k277n1PE-ft0jqOBtYR-cnh13vQoumJtaOdG4l1uyKhzXpWiG5ttrkQguXh56RNHwOjqcs6TxyNJzNNmMMYuP1_aOBhML2jGIQ8NnkICQyRxKXkQChHqXRSr4pVNgPrzEBsJ0M5TvCHhyc-4Ot8OfDaVyDRve5amsPCJERvhlxOYMjaMCgCqw9q7Z3MwOiDAGo_HGZU_wlB7nFP837-jg1p8_SdRZqeUoLRAPwgC5T07rctnukmTACo2yqwqeAJxabpJGUcdVrNjVqGKAyxx6zMH4RYRAO8GJSnb-wn624hmD3bALplu2R45yyypgbG5il2FeQUxJFUttt1Ak48tEk-ikVoe7LgP0nTMlY1B9NbuDtJcHXwpxGIweFIigLQKyIN85JXSFrqAZwLEz_io7N5hwglMPFPCgImQ1RtsVyAhV-e9hgsGZdBLjHgoi-PzBoim11BOrgbUxpOo_RptmT6CZaXgIClOvaVdAwdhIKZdg8j45FWWrKS44Y-6WPYYNVuS6p7r2LAbNDbKM_mP1FJEH7jm6R4z4lzfqciwRxlQFhbyt72kLl42jmYicj3_8GQgh7pjXwKH6nWQI2o_nENoAuO8Jb8Z_dT4n1A-kmPoWL1S9A4FPH1UtGxQ6LRtMtJiO2js5Yq7vLGoqNNHiwV4MB90h1LrKaf4WkWOd6ojgx1--58ynGz-QIEHWVClsnpJ21zi2XauVyDVxWyC_phOMnB6tQ'
        self.session = requests.session()  # 用于储存cookie应对无响应
        self.referer = 'https://www.pixiv.net/ranking.php?mode=monthly&content=illust'

    # 登录
    def login(self):
        session = requests.session()
        login_html = self.session.get(url=self.login_url, headers=self.common_header, verify=False)
        sleep(1)
        post_key_tree = etree.HTML(login_html.text)
        self.post_key = re.findall('"pixivAccount.postKey":"(.*?)"', str(post_key_tree.xpath('//input/@value')), re.S)
        data = {
            'password': self.password,
            'pixiv_id': self.pixiv_id,
            'post_key': self.post_key,
            'source': self.source,
            'return_to': self.return_to,
        }
        session.post(url=self.request_url, data=data, headers=self.common_header)
        sleep(1)

    # 获取排行榜信息
    def rank_img(self, mode, content, date):
        print("mode:" + mode + " content:" + content + " date: " + date + "获取ing...")
        for img_pages in range(10):
            data_url = self.rank_img_url.format(img_pages + 1, mode, content, date)
            data = self.session.get(url=data_url, headers=self.common_header, verify=False).json()
            if "error" in data:
                print("错误")
                break
            if not os.path.exists('./pixiv/rank ' + mode + ' ' + content + date):
                os.mkdir('./pixiv/rank ' + mode + ' ' + content + date)
            img_url = re.findall('(https://i.pximg.net/c/.*?jpg)', str(data), re.S)
            re.findall('illust_id\': (.*?),', str(data), re.S)
            img_name = re.findall('title\':.\'(.*?)\'', str(data), re.S)
            sleep(1)
            for i in range(len(img_url)):
                img_url1 = re.sub(r'c/240x480/', "", img_url[i])
                img_url1 = re.sub("\\\/", "/", img_url1)
                img_url1 = re.sub(r'c/250x250_80_a2/', "", img_url1)
                img_url1 = re.sub(r'custom-thumb', "img-original", img_url1)
                img_url1 = re.sub(r'img-master', "img-original", img_url1)
                img_url1 = re.sub(r'_custom1200', "", img_url1)
                img_url1 = re.sub(r'_square1200', "", img_url1)
                img_url1 = re.sub(r'_master1200', "", img_url1)
                img_url1 = re.sub(r'jpg', "png", img_url1)
                # 文件不能含有以下9种字符：? * : " < > \ / |
                sub_patterns = [r'"', r'/', r'\\', '\?', '\*', '\:', '\<', '\>', '\|']
                try:
                    name = str(img_pages * 50 + i + 1) + '.' + re.sub('|'.join(sub_patterns), '', img_name[i])
                    img_data = requests.get(url=img_url1, headers=self.common_header).content
                    if len(img_data) <= 58:
                        img_url1 = re.sub(r'png', "jpg", img_url1)
                        img_path = './pixiv/rank ' + mode + ' ' + content + date + '/' + name + '.jpg'
                        img_data = requests.get(url=img_url1, headers=self.common_header).content
                    else:
                        img_path = './pixiv/rank ' + mode + ' ' + content + date + '/' + name + '.png'
                    self.img_load(img_path=img_path, img_name=name, img_data=img_data, img_url=img_url1)
                except IndexError:
                    pass
            print('第' + str(img_pages + 1) + '页爬取成功啦')

    # 文件储存
    def img_load(self, img_path, img_name, img_data, img_url):
        with open(img_path, 'wb') as fp:
            fp.write(img_data)
        print(img_name, '下载成功')
        sleep(0.5)

    # 通过用户id获取图片
    def id_sech(self, id):
        id_get_url = format(self.id_sech_url % id)
        self.id_url_front = format(self.id_url_front % id)
        self.id_url_beside = self.id_url_beside.format(1)
        id_data = self.session.get(url=id_get_url, headers=self.common_header, verify=False).text
        find_list = ['illusts":{(.*),"manga":', '"manga":{(.*?),"novels":']
        id_list1 = re.findall(find_list[0], id_data)
        if id_list1 == []:
            print("该id不存在作品")
        else:
            print(id_list1)
            id_list2 = re.findall(find_list[1], id_data)
            print(id_list2)
            id_list = re.findall('"(.*?)":null', str(id_list1) + str(id_list2))
            print(id_list)
            print(len(id_list))
            if len(id_list) >= 100:
                num = int(len(id_list) / 100) + 1
                print(num)
                for i in range(num):
                    url_final = ''
                    if i == num - 1:
                        for id1 in id_list[(num - 1) * 100:]:
                            if id1 == id_list[0]:
                                url_final += 'ids%5B%5D=' + id1
                            else:
                                url_final += '&ids%5B%5D=' + id1
                    else:
                        page = i + 1
                        for id1 in id_list[0:page * 100]:
                            if id1 == id_list[0]:
                                url_final += 'ids%5B%5D=' + id1
                            else:
                                url_final += '&ids%5B%5D=' + id1
                    id_url = self.id_url_front + url_final + self.id_url_beside
                    self.id_img_seach(id_url, id, i)
            else:
                for id1 in id_list:
                    if id1 == id_list[0]:
                        url_final += 'ids%5B%5D=' + id1
                    else:
                        url_final += '&ids%5B%5D=' + id1
                id_url = self.id_url_front + url_final + self.id_url_beside
                self.id_img_seach(id_url, id, 0)

    def id_img_seach(self, id_url, id, page_num):
        if not os.path.exists('./pixiv/id ' + str(id) + ' ' + str(page_num)):
            os.mkdir('./pixiv/id ' + str(id) + ' ' + str(page_num))
        sleep(0.2)
        img_url_data = requests.get(url=id_url, headers=self.cookie_header).text

        img_url = re.findall('"url":"(.*?)","description":"",', str(img_url_data))
        for i in range(len(img_url)):
            img_path = './pixiv/id ' + str(id) + ' ' + str(page_num) + '/' + str(i + 1) + '.png'
            if os.path.exists(img_path): continue
            img_url1 = re.sub("\\\/", "/", img_url[i])
            img_url1 = re.sub(r'c/250x250_80_a2/', "", img_url1)
            img_url1 = re.sub(r'custom-thumb', "img-original", img_url1)
            img_url1 = re.sub(r'img-master', "img-original", img_url1)
            img_url1 = re.sub(r'_custom1200', "", img_url1)
            img_url1 = re.sub(r'_square1200', "", img_url1)
            img_url1 = re.sub(r'jpg', "png", img_url1)
            img_data = requests.get(url=img_url1, headers=self.common_header).content
            if len(img_data) <= 58:
                img_url1 = re.sub(r'png', "jpg", img_url1)
                img_path = './pixiv/id ' + str(id) + ' ' + str(page_num) + '/' + str(i + 1) + '.jpg'
                img_data = requests.get(url=img_url1, headers=self.common_header).content
            img_name = i + 1
            self.img_load(img_path, img_name, img_data, img_url1)
            sleep(0.1)

    def tag_seach(self, tag, mode, page_num):
        if not os.path.exists('./pixiv/tag ' + str(tag) + ' ' + str(page_num)):
            os.mkdir('./pixiv/tag ' + str(tag) + ' ' + str(page_num))
        key = parse.quote(tag)
        tag_url = self.tag_base_url.format(key, mode)
        if not os.path.exists('./tag ' + str(tag)):
            os.mkdir('./tag ' + str(tag))
        for j in range(page_num):
            tag_url1 = re.sub('!', str(j + 1), tag_url)
            tag_data = requests.get(url=tag_url1, headers=self.cookie_header).text
            img_url = re.findall('url":"(.*?)","description":""', tag_data, re.S)
            for i in range(len(img_url)):
                img_url1 = re.sub("\\\/", "/", img_url[i])
                img_url1 = re.sub(r'c/250x250_80_a2/', "", img_url1)
                img_url1 = re.sub(r'custom-thumb', "img-original", img_url1)
                img_url1 = re.sub(r'img-master', "img-original", img_url1)
                img_url1 = re.sub(r'_custom1200', "", img_url1)
                img_url1 = re.sub(r'_square1200', "", img_url1)
                img_url1 = re.sub(r'jpg', "png", img_url1)
                img_id = img_url1.split('/')[11].split('_')[0]
                img_data = requests.get(url=img_url1, headers=self.common_header).content
                if len(img_data) <= 58:
                    img_url1 = re.sub(r'png', "jpg", img_url1)
                    img_path = './pixiv/tag ' + str(tag) + ' ' + str(page_num) + '/' + str(
                        i + j * len(img_url) + 1) + '.jpg'
                    img_data = requests.get(url=img_url1, headers=self.common_header).content
                else:
                    img_path = './pixiv/tag ' + str(tag) + ' ' + str(page_num) + '/' + str(
                        i + j * len(img_url) + 1) + '.png'
                img_name = i + j * len(img_url) + 1
                self.img_load(img_path, img_name, img_data, img_url1)
                sleep(1)
            print("第" + str(j + 1) + "页爬取好了，还剩" + str(page_num - j - 1) + "页")
            sleep(1)

    # mode转换
    def mode_traform(self, mode):
        if mode == '日':
            mode = 'daily'
        elif mode == '月':
            mode = 'monthly'
        elif mode == '周':
            mode = 'weekly'
        elif mode == '全年龄':
            mode = 'all'
        elif mode == 'R18':
            mode = 'R18'
        else:
            mode = '0'
        return mode

    # content转换
    def content_traform(self, content):
        if content == '综合':
            content = ''
        elif content == '插画':
            content = '&content=illust'
        elif content == '动图':
            content = '&content=ugoira'
        elif content == '漫画':
            content = '&content=manga'
        else:
            content = '0'
        return content

    # 日期转换
    def date_traform(self, date):
        if len(date) == 8:
            date = '&date=' + date
            return date
        else:
            return ''

    # 主函数
    def run(self):
        if not os.path.exists('./pixiv'):
            os.mkdir('./pixiv')
        select = input("  pixiv图片获取\n请输入选择的模式:\n1、获取作品排行榜\n2、获取作者相关作品\n3、获取标签相关作品\n")
        if select == '1':
            mode = self.mode_traform(input("请输入日、周、月之一进行日期范围选择:"))
            content = self.content_traform(input("请输入综合、插画、动图、漫画之一进行内容范围选择:"))
            date = self.date_traform(input("若需要进行日期选择请输入日期（格式：20210714）:"))
            if ((mode == '0') | (content == '0')):
                print("请正确输入")
            else:
                self.rank_img(mode=mode, content=content, date=date)
                print("获取成功啦")
        elif select == '2':
            userid = int(input("请输入作者id:"))
            self.id_sech(userid)
            print("获取成功啦")
        elif select == '3':
            tag = input("请输入标签tag:")
            mode = self.mode_traform(input("请输入全年龄、R18进行模式选择:"))
            if mode == '0':
                print("请正确输入")
            else:
                try:
                    page_num = int(input("请输入要读取到第几页:"))
                except:
                    print("请输入正确的页数")
                self.tag_seach(tag, mode, page_num)
                print("获取成功啦")


if __name__ == '__main__':
    PixivSpider = PixivSpider()
    PixivSpider.run()
