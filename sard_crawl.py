# coding=utf8
'''download cwe

'''
import requests
import time
import zipfile
import os
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import re
import socks
import socket


def downloadc(cweid, path, files):
    '''

    :param cweid:
    :param path:
    :return:
    '''

    url = "https://samate.nist.gov/SARD/view.php?count=100&languages[]=C&typeofartifacts[]=Source+Code&" \
          "flaw=" + cweid + "&status_Candidate=1&status_Accepted=1&action=zip-selected&first=&sort=desc"
    print(url)
    filename = cweid + "-c.zip"
    header = {
        'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36",
        'Referer': "https://samate.nist.gov/SARD/search.php",
        'Cookie': "__utmc=222292762; __utmz=222292762.1555401581.1.1.utmccn=(direct)|utmcsr=(direct)|utmcmd=(none);" \
                  "__utma=222292762.1021045234.1555401581.1555401581.1555420158.2; __utmb=222292762"
    }
    s = requests.session()
    r = get_by_socks5(s, url, header)
    fcontrol = 1
    if (r.text.find('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"') > 0):
        first = 0
        while ((cweid + "-" + str(first) + "-c.zip") in files):
            print("pass", cweid + "-" + str(first) + "-c.zip")
            first += 100

        if first > 0:
            first -= 100

        url = "https://samate.nist.gov/SARD/view.php?count=100&languages[]=C&" \
              "flaw=" + cweid + "&status_Candidate=1&status_Accepted=1&action=zip-page&first=" + str(
            first) + "&sort=desc"
        if fcontrol == 15:
            time.sleep(6)
            fcontrol = 0
        fcontrol += 1
        s.keep_alive = False
        r = get_by_socks5(s, url, header)
        while (r.text.find('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"') <= 0):
            filename = cweid + "-" + str(first) + "-c.zip"

            with open(path + "/" + filename, "wb") as code:
                print('writing')
                code.write(r.content)
            if r.status_code == 200:
                print(filename, ' download sucess!')
            else:
                print(filename, "download fail!")
                print(r.status_code)
                print(filename)

            first += 100

            url = "https://samate.nist.gov/SARD/view.php?count=100&languages[]=C&flaw=" + cweid + \
                  "&status_Candidate=1&status_Accepted=1&action=zip-page&first=" + str(first) + "&sort=desc"
            if fcontrol == 15:
                time.sleep(6)
                fcontrol = 0
            fcontrol += 1
            s.keep_alive = False
            print(url)
            r = get_by_socks5(s, url, header)
    else:
        with open(path + "/" + filename, "wb") as code:
            print('writing')
            code.write(r.content)
        if r.status_code == 200:
            print(filename, 'download sucess!')
        else:
            print(filename, "download fail!")
            print(r.status_code)
            print(filename)



def downloadcpp(cweid, path, files):
    '''

    :param cweid:
    :param path:
    :return:
    '''
    url = "https://samate.nist.gov/SARD/view.php?count=100&languages[]=C%2B%2B&typeofartifacts[]=Source+Code&" \
          "flaw=" + cweid + "&status_Candidate=1&status_Accepted=1&action=zip-selected&first=&sort=desc"
    print(url)
    filename = cweid + "-cpp.zip"
    header = {
        'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36",
        'Referer': "https://samate.nist.gov/SARD/search.php",
        'Cookie': "__utmc=222292762; __utmz=222292762.1555401581.1.1.utmccn=(direct)|utmcsr=(direct)|utmcmd=(none);" \
                  "__utma=222292762.1021045234.1555401581.1555401581.1555420158.2; __utmb=222292762"
    }
    s = requests.session()
    r = get_by_socks5(s, url, header)
    fcontrol = 1
    if (r.text.find('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"') > 0):
        first = 0
        while ((cweid + "-" + str(first) + "-c.zip") in files):
            print("pass", cweid + "-" + str(first) + "-c.zip")
            first += 100
        if first > 0:
            first -= 100
        url = "https://samate.nist.gov/SARD/view.php?count=100&languages[]=C%2B%2B&" \
              "flaw=" + cweid + "&status_Candidate=1&status_Accepted=1&action=zip-page&first=" + str(
            first) + "&sort=desc"
        if fcontrol == 15:
            time.sleep(6)
            fcontrol = 0
        fcontrol += 1
        s.keep_alive = False
        r = get_by_socks5(s, url, header)
        while (r.text.find('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"') <= 0):
            filename = cweid + "-" + str(first) + "-cpp.zip"
            with open(path + "/" + filename, "wb") as code:
                print('writing')
                code.write(r.content)
            if r.status_code == 200:
                print(filename, 'download sucess')
            else:
                print(filename, "download fail!")
                print(r.status_code)
                print(filename)
            first += 100
            url = "https://samate.nist.gov/SARD/view.php?count=100&languages[]=C%2B%2B&flaw=" + cweid + \
                  "&status_Candidate=1&status_Accepted=1&action=zip-page&first=" + str(first) + "&sort=desc"
            if fcontrol == 15:
                time.sleep(6)
                fcontrol = 0
            fcontrol += 1
            s.keep_alive = False
            print(url)
            r = get_by_socks5(s, url, header)
    else:
        with open(path + "/" + filename, "wb") as code:
            print('writing')
            code.write(r.content)
        if r.status_code == 200:
            print(filename, 'download sucess')
        else:
            print(filename, "download fail!")
            print(r.status_code)
            print(filename)


def downLoadMain(cweid, path):
    '''

    :param cweid:
    :param path:
    :return:
    '''
    requests.adapters.DEFAULT_RETRIES = 5  # ??????????????????
    # print('example: \nplease input cweid: 562\nplease input storage path: "D:\PycharmProjects\SARD\CWE562"\n')
    # cweid = input("please input cweid: ")
    # path = input('please input storage path: ')

    isExists = os.path.exists(path)
    if not isExists:
        os.makedirs(path)
    # if isExists:
    #     print("id has downloaded!")
    #     return
    files = set(os.listdir(path))
    if "manifest.xml" in files:
        print("done id !return")
        return

    cweid = str(cweid)
    print('begin to download c ')
    downloadc(cweid, path, files)
    print('begin to download cpp ')
    downloadcpp(cweid, path, files)
    # ?????????
    print('begin to unzip')
    filelist = os.listdir(path)
    for file in filelist:
        with zipfile.ZipFile(path + '/' + file) as zf:
            zf.extractall(path + '/' + file[:-4])
        os.remove(path + '/' + file)
    # ??????manifest.xml
    print('begin to merge xml')
    root = ET.Element('container')  # ????????????
    root.text = "\n\t"
    dirlist = os.listdir(path)
    for dir in dirlist:
        # print(dir)
        flist = os.listdir(path + "/" + dir + "/")
        # print(flist)
        p = None
        for findxml in flist:
            if findxml[-3:] == 'xml':
                p = path + "/" + dir + "/" + findxml
                break
        if (p == None):
            print("no xml found in {}!".format(str(flist)))
            return
        # print(p)
        t = ET.parse(p)
        r = t.getroot()
        for tc in r:
            allfile = tc.findall("file")
            # print(allfile)
            for f in allfile:
                f.attrib["path"] = dir + "/testcases/" + f.attrib["path"]
            root.append(tc)
    tree = ET.ElementTree(root)  # ????????????
    tree.write(path + '/manifest.xml', encoding='utf-8', xml_declaration=True)


def main(cwe_id):
    # cweid = "693"
    # path = "./dataset/svf-related/CWE{}/source-code".format(args['cwe_id'])
    path = "/home/niexu/dataset/CWES/CWE{}/source-code".format(cwe_id)
    if not os.path.exists(path):
        os.makedirs(path)
    downLoadMain(cwe_id, path)


def get_top25_cweid():
    url = 'https://cwe.mitre.org/data/definitions/1350.html'
    header = {
        'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36",
        'Referer': "https://samate.nist.gov/SARD/search.php",
        'Cookie': "__utmc=222292762; __utmz=222292762.1555401581.1.1.utmccn=(direct)|utmcsr=(direct)|utmcmd=(none);" \
                  "__utma=222292762.1021045234.1555401581.1555401581.1555420158.2; __utmb=222292762"
    }
    s = requests.session()
    r = get_by_socks5(s, url, header)

    bs = BeautifulSoup(r.text, 'html.parser')
    group = bs.select('.group')
    cwe_list = []
    for g in group:
        cwe = {}
        cwe_name = g.select('a')[0].text
        cwe_id = g.select('.cweid')[0].text
        cwe_id = re.findall('[0-9]+', cwe_id)[0]
        cwe['cwe_name'] = cwe_name
        cwe['cwe_id'] = cwe_id
        cwe_list.append(cwe)
    return cwe_list

def get_by_socks5(s,url, header):
    socks.set_default_proxy(socks.SOCKS5, '192.168.1.24', 1090)
    socket.socket = socks.socksocket

    r = s.get(url, headers=header)
    return r

if __name__ == '__main__':
    # args = {
    #     'cweid': '693'
    # }
    # main(args)
    socks.set_default_proxy(socks.SOCKS5, '192.168.1.24', 1090)
    socket.socket = socks.socksocket

    cwe_list = ['254', '399']
    while True:
        try:
            for cwe in cwe_list:
                print(cwe)
                main(cwe)
        except Exception as e:
            with open('./log.txt','a+') as f:
                f.write(str(e) + '\n'+time.strftime("%d/%m/%Y") + time.strftime("%H:%M:%S"))
                f.close()
        time.sleep(60)