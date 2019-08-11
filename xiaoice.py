#!/usr/bin/python
# coding: utf-8

# realXiaoice - xiaoice.py
# 2019/8/11 13:27
#

__author__ = "Benny <benny.think@gmail.com>"

import time
import logging
import random
import requests

# from config import cookies

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')
SEND = 'https://m.weibo.cn/api/chat/send'
RECV = 'https://m.weibo.cn/api/chat/list?uid=5175429989&count=2&unfollowing=0'

s = requests.Session()


def __read_headers():
    logging.info('Reading headers...')
    real = {}
    f = open('headers.txt', encoding='utf-8')

    line = f.readline().strip()
    while line:
        key = line.split(":")[0]
        # firefox里的原始头冒号后面会多出一个空格，需除去
        real[key] = line[len(key) + 1:].strip()
        line = f.readline().strip()
    f.close()
    return real


def realtime_csrf():
    logging.info('Get realtime csrf token')
    cookie_line = __read_headers().get('Cookie').split(':')[-1].strip()
    r = s.get(RECV, headers={"Cookie": cookie_line})
    return r.cookies.get('XSRF-TOKEN')


def __renew_headers():
    logging.info('Renewwing headers.txt')
    old_headers = __read_headers()
    old_csrf = old_headers.get('X-XSRF-TOKEN')
    new_csrf = realtime_csrf()
    old_headers['X-XSRF-TOKEN'] = new_csrf
    old_headers['Cookie'] = old_headers['Cookie'].replace(old_csrf, new_csrf)
    # write files
    with open('headers.txt', 'r')as f:
        text = f.read()
        text = text.replace(old_csrf, new_csrf)
    with open('headers.txt', 'w') as f:
        f.write(text)
    return old_headers


def chat(msg):
    logging.info('Getting headers from headers.txt')
    cur_headers = __read_headers()
    data = dict(uid=5175429989,
                content=msg,
                st=cur_headers.get('X-XSRF-TOKEN'))

    logging.info('Sending messages...')
    r = s.post(SEND, headers=cur_headers, data=data).json()
    logging.info('Server response: {}'.format(r))

    if r.get('ok') != 1:
        logging.warning('Headers are invalid, renewing now...')
        new = __renew_headers()
        data = dict(uid=5175429989,
                    content=msg,
                    st=new.get('X-XSRF-TOKEN'))

        sub = s.post(SEND, headers=new, data=data).json()
        logging.warning(sub)

    # get response
    time.sleep(random.random())
    while 1:
        logging.info('Getting responses by polling...')
        r = s.get(RECV, headers=cur_headers).json()
        logging.info('Raw response from API: {}'.format(r))
        response = r['data']['msgs'][0]['text']
        if response != msg:
            break
        time.sleep(random.random())
    return response


if __name__ == '__main__':
    res = chat('好好好我错了')
    print(res)
