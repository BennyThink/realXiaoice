# coding: utf-8
# realXiaoice - keygen.py
# 2019/8/28 20:07

__author__ = "Benny <benny.think@gmail.com>"

import uuid

codes = [item.replace('\r', '').replace('\n', '')
         for item in open('key.txt', encoding='u8').readlines()]
print("Current: ", codes)
f = open('key.txt', 'a', encoding='u8')
f.write('\n' + uuid.uuid4().hex[:5])
f.close()
print("Your new auth code is %s" % hex)
