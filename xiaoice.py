#!/usr/bin/python
# coding: utf-8

# realXiaoice - xiaoice.py
# 2019/8/11 13:27
#

__author__ = "Benny <benny.think@gmail.com>"

import base64
import logging
import os
import random
import re
import time

import requests

# from config import cookies

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s [%(levelname)s]: %(message)s')
SEND_IMG = 'https://m.weibo.cn/api/chat/upload'
SEND = 'https://m.weibo.cn/api/chat/send'
RECV = 'https://m.weibo.cn/api/chat/list?uid=5175429989&count=10&unfollowing=0'

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


def __send_img(img_path: str) -> str:
    logging.info('Begin to send Image to xiaoIce')
    cur_headers = __read_headers()
    cur_headers.pop('content-type')
    img_name = os.path.basename(img_path)
    # imgType = os.path.splitext(img_path)[1]
    files = {
        'file': (img_name, open(img_path, 'rb'), 'image/jpeg')
    }
    data = {
        'tuid': 5175429989,
        'st': cur_headers['X-XSRF-TOKEN']
    }
    logging.info('Sending Images...')
    r = s.post(SEND_IMG, files=files, params=data, headers=cur_headers).json()
    if r['ok'] != 1:
        logging.warning('Headers are invalid, renewing now...')
        new = __renew_headers()
        new.pop('content-type')
        data = {
            'tuid': 5175429989,
            'st': new['X-XSRF-TOKEN']
        }
        logging.warning('Sending Images...')
        r = s.post(SEND_IMG, files=files, params=data, headers=new).json()
    return r['data']['fids']


def __get_response(send_ts: (int, float), sleep: int) -> str:
    """
        get records based on timestamp.
        check the timestamp in json one by one
        if the timestamp in json is larger than the sendingTimeStamp, collect, otherwise discard
        :param  send_ts: timestamp calculated by system when sending a message
                sleep:the seconds of sleep in main thread. default: chat only with text:1s; chat with image:7s
        :return: response of xiaoIce separated by \n
    """
    # get response
    time.sleep(sleep)
    cur_headers = __read_headers()
    polling_count = 0
    response_messages = []
    response_message = ''
    while 1:
        if polling_count >= 20:
            response_message = ''
            logging.warning('Message fetch failed')
            break
        logging.info('Getting responses by polling...')
        r = s.get(RECV, headers=cur_headers).json()
        messages = r.get('data', {}).get('msgs', {})
        response_messages = []
        for i in range(len(messages)):
            # calculate timestamp
            # Sat May 09 00:14:57 2020 => 1588954497
            recv_ts = time.mktime(time.strptime(messages[i]['created_at'], '%a %b %d %H:%M:%S %z %Y'))
            if messages[i]['sender_id'] == 5175429989 and recv_ts >= send_ts:
                logging.info('Fetch message: {}'.format(messages[i]['text']))
                response_messages.append(messages[i])
        if len(response_messages) != 0:
            break
        polling_count += 1
        time.sleep(random.random() * 2)

    response_messages.reverse()

    for eachMsg in response_messages:
        # if the answer is an image file
        if 'attachment' in eachMsg:
            attachment_uri = eachMsg['attachment']['original_image']['url']
            attachment_ext = eachMsg['attachment']['extension']
            base64_image = base64.b64encode(s.get(attachment_uri, headers=cur_headers).content)
            eachMsg['text'] = 'data:image/' + attachment_ext + ';base64,' + str(base64_image, encoding='utf-8')
        response_message += __remove_bad_html(eachMsg['text']) + '\n'
    return response_message


def chat(msg: str) -> str:
    """
    chat program
    :param msg: message send to xiaoice
    :return: her response
    """
    send_ts = time.time()
    send_msg(msg=msg)
    resp_msg = __get_response(send_ts, 2)
    logging.info('Get Response message: {}'.format(resp_msg))
    return resp_msg


def chat_with_img(img_path: str) -> str:
    """
    chat xiaoice with image
    :param img_path: the path of image
    :return: her response
    """
    send_ts = time.time()
    send_msg(img_path=img_path)

    resp_msg = __get_response(send_ts, 2)
    logging.info('Get Response message: {}'.format(resp_msg))
    return resp_msg


def send_msg(msg=None, img_path=None):
    logging.info('Getting headers from headers.txt')
    cur_headers = __read_headers()
    data = dict(uid=5175429989, st=cur_headers.get('X-XSRF-TOKEN'))

    if img_path is not None:
        data.update(fids=__send_img(img_path))
    else:
        data.update(content=msg)

    logging.info('Sending messages...')
    r = s.post(SEND, headers=cur_headers, data=data).json()
    logging.info('Server response: {}'.format(r))
    if r.get('ok') != 1:
        logging.warning('Headers are invalid, renewing now...')
        new = __renew_headers()
        sub = s.post(SEND, headers=new, data=data).json()
        logging.warning(sub)


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
    # res = chat('好好好我错了')
    res = chat_with_img('assets/stars.jpg')
    print(res)
