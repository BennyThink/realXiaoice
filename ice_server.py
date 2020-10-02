#!/usr/bin/python
# coding: utf-8

# realXiaoice - server.py
# 2019/8/11 17:13
#

__author__ = "Benny <benny.think@gmail.com>"

import json
import logging
import os
import traceback
from concurrent.futures import ThreadPoolExecutor
from platform import uname

from tornado import escape
from tornado import web, ioloop, httpserver, gen, options
from tornado.concurrent import run_on_executor

from xiaoice import chat, chat_with_img


def json_encode(value):
    return json.dumps(value, ensure_ascii=False)


ALLOWED_IPS, AUTH = [], False

escape.json_encode = json_encode


class BaseHandler(web.RequestHandler):
    def data_received(self, chunk):
        pass


class IndexHandler(BaseHandler):
    def get(self):
        text = '''
        GET: http://127.0.0.1:6789/chat?text=hello
        POST:http://127.0.0.1:6789/chat, form-urlencoded or json with {"text":"hello"}
        Response: HTTP 200: {"text":"hi there", "debug":""}
                  Other : {"text":"", "debug":"error"}
        '''
        self.write(text)


class ChatHandler(BaseHandler):
    executor = ThreadPoolExecutor(max_workers=20)

    def get_correct_argument(self, name):
        try:
            if self.request.headers.get('Content-Type') == 'application/json' \
                    and self.request.body:
                value = json.loads(self.request.body).get(name)
            else:
                value = self.get_argument(name, "text")
            return value
        except ValueError as e:
            logging.error('Failed to extract arguments {}'.format(e))

    def accessibility(self):
        ip = self.request.headers.get("X-Real-IP", "") or self.request.remote_ip
        auth_code = self.get_correct_argument('auth') or ''

        msg = {}
        correct_auth = [item.replace('\r', '').replace('\n', '')
                        for item in open('key.txt', encoding='u8').readlines()]
        if AUTH and auth_code not in correct_auth:
            msg = {"text": "", "debug": "Bad auth code."}
        elif ALLOWED_IPS and ip not in ALLOWED_IPS:
            msg = {"text": "", "debug": "Your IP is not allowed to access this API."}

        if msg:
            logging.warning('Access denied for {}'.format(ip))
            self.set_status(403)
            return msg

    @run_on_executor
    def run_request(self):
        denied = self.accessibility()
        if denied:
            return denied

        user_input = self.get_correct_argument('text')
        user_input_type = self.get_correct_argument('type')
        response = {}
        if user_input:
            try:
                if user_input_type == 'text':
                    response = {"text": chat(user_input), "debug": ""}
                elif user_input_type == 'img':
                    response = {"text": chat_with_img(user_input), "debug": ""}
            except Exception as e:
                logging.error(traceback.format_exc())
                self.set_status(500)
                response = {"text": "", "debug": str(e)}
        else:
            self.set_status(400)
            response = {"text": "", "debug": "Wrong params."}
        return response

    @gen.coroutine
    def get(self):
        res = yield self.run_request()
        self.write(res)

    @gen.coroutine
    def post(self):
        res = yield self.run_request()
        self.write(res)


class RunServer:
    root_path = os.path.dirname(__file__)
    page_path = os.path.join(root_path, 'pages')

    handlers = [(r'/', IndexHandler),
                (r'/chat', ChatHandler),
                ]
    settings = {
        "cookie_secret": "5Li05DtnQewDZq1mDVB3HAAhFqUu2vD2USnqezkeu+M=",
        "xsrf_cookies": False
    }

    application = web.Application(handlers, **settings)

    @staticmethod
    def run_server(port=9876, host='127.0.0.1', **kwargs):
        tornado_server = httpserver.HTTPServer(RunServer.application, **kwargs, xheaders=True)
        tornado_server.bind(port, host)

        if uname()[0] == 'Windows':
            tornado_server.start()
        else:
            tornado_server.start(1)

        try:
            print('Server is running on http://{host}:{port}'.format(host=host, port=port))
            ioloop.IOLoop.instance().current().start()
        except KeyboardInterrupt:
            ioloop.IOLoop.instance().stop()
            print('"Ctrl+C" received, exiting.\n')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    options.define("p", default=6789, help="running port", type=int)
    options.define("h", default='127.0.0.1', help="listen address", type=str)
    options.define("a", default='', help="Allowed IPs to access this server,split by comma", type=str)
    options.define("auth", default=False, help="Enable auth? default is set to false", type=bool)
    options.parse_command_line()
    p = options.options.p
    h = options.options.h
    allow = options.options.a
    AUTH = options.options.auth
    if allow:
        ALLOWED_IPS = allow.split(',')
    RunServer.run_server(port=p, host=h)
