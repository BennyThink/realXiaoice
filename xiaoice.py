#!/usr/bin/python
# coding: utf-8

# realXiaoice - xiaoice.py
# 2019/8/11 13:27
#

__author__ = "Benny <benny.think@gmail.com>"

import base64
import logging
import random
import re
import time

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


def __realtime_csrf():
    # get realtime csrf token every 30 min
    logging.info('Get realtime csrf token')
    cookie_line = __read_headers().get('Cookie').split(':')[-1].strip()
    r = s.get(RECV, headers={"Cookie": cookie_line})
    return r.cookies.get('XSRF-TOKEN')


def __renew_headers():
    logging.info('Renewwing headers.txt')
    old_headers = __read_headers()
    old_csrf = old_headers.get('X-XSRF-TOKEN')
    new_csrf = __realtime_csrf()
    old_headers['X-XSRF-TOKEN'] = new_csrf
    old_headers['Cookie'] = old_headers['Cookie'].replace(old_csrf, new_csrf)
    # write files
    with open('headers.txt', 'r')as f:
        text = f.read()
        text = text.replace(old_csrf, new_csrf)
    with open('headers.txt', 'w') as f:
        f.write(text)
    return old_headers


def chat(msg: str) -> str:
    """
    chat program
    :param msg: message send to xiaoice
    :return: her response
    """
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
    polling_count = 0
    last_message = {}
    while 1:
        if polling_count >= 20:
            last_message['text'] = ''
            logging.warning('Last answer message fetch failed')
            break
        logging.info('Getting responses by polling...')
        r = s.get(RECV, headers=cur_headers).json()
        last_message = r.get('data', {}).get('msgs', {})[0]
        if last_message['sender_id'] == 5175429989:
            logging.info('Fetch last message: {}'.format(last_message))
            break
        polling_count += 1
        time.sleep(random.random())

    # if the answer is an image file
    if 'attachment' in last_message:
        attachment_uri = last_message['attachment']['original_image']['url']
        attachment_ext = last_message['attachment']['extension']
        base64_image = base64.b64encode(s.get(attachment_uri, headers=cur_headers).content)
        last_message['text'] = 'data:image/' + attachment_ext + ';base64,' + str(base64_image, encoding='utf-8')

    return __remove_bad_html(last_message['text'])


def __remove_bad_html(msg: str) -> str:
    # remove html code in chat message. If fails, this function will return original chat message.
    logging.info("removing bad urls in chat message")
    non_backslash = msg.replace(r'\/', '/')
    try:
        text_list = re.findall(r'(.*)<a.*', non_backslash)
        text = text_list[0]
        url_list = re.findall(r'(?:(?:https?|ftp)://)+[\w/\-?=%.]+\.[\w/\-?=%.]+', non_backslash)
        url = url_list[0]
        logging.info("All right, you are so 'funny' weibo:-(")
    except IndexError:
        logging.info('It seems like a normal text without any html codes.')
        text = ''
        url = ''
    if url and text:
        return text + url
    else:
        return non_backslash


if __name__ == '__main__':
    res = chat('好好好我错了')
    print(res)
