# coding=utf-8

import hashlib
import time
import requests
import base64
import hmac
from enum import Enum


class API_TYPE(Enum):
    ORDER = 1
    USER = 2
    QUOTE = 3


class Client(object):

    API_URL = 'https://api.sfex.net'
    API_ORDER = 'order'
    API_USER = 'balance'
    API_QUOTE = 'https://q.sfex.net/v1'

    def __init__(self, api_key, api_secret, requests_params=None):
        """SFEX API Client constructor

        :param api_key: Api Key
        :type api_key: str.
        :param api_secret: Api Secret
        :type api_secret: str.
        :param requests_params: optional - Dictionary of requests params to use for sfex
        :type requests_params: dict.

        """
        self.API_KEY = api_key
        self.API_SECRET = api_secret
        self._session = self._init_session()
        self._requests_params = requests_params

    def _init_session(self):

        session = requests.session()
        session.headers.update({'Accept': 'application/json',
                                'Content-Type': 'application/x-www-form-urlencoded'})
        return session

    def _create_api_uri(self, path, api_type):
        if api_type == API_TYPE.ORDER:
            return "{}/{}/{}".format(self.API_URL, self.API_ORDER, path)
        elif api_type == API_TYPE.USER:
            return "{}/{}/{}".format(self.API_URL, self.API_USER, path)
        elif api_type == API_TYPE.QUOTE:
            return "{}/{}".format(self.API_QUOTE, path)

    def _generate_signature(self, data):
        ordered_data = self._order_params(data)
        query_string = '&'.join(["{}={}".format(d[0], d[1]) for d in ordered_data])
        return base64.b64encode(hmac.new(key=self.API_SECRET.encode("utf-8"),
                                         msg=query_string.encode("utf-8"), digestmod=hashlib.sha256).digest())

    def _order_params(self, data):
        """Convert params to list with signature as last element

        :param data:
        :return:

        """
        params = []
        for key, value in data.items():
            params.append((key, value))
        return params

    def _request(self, method, path, type, signed, **kwargs):

        uri = self._create_api_uri(path, type)

        # set default requests timeout
        kwargs['timeout'] = 10

        # add our global requests params
        if self._requests_params:
            kwargs.update(self._requests_params)

        data = kwargs.get('data', None)
        if data and isinstance(data, dict):
            kwargs['data'] = data
        else:
            kwargs['data'] = {}

        params = kwargs.get('params', None)
        if params and isinstance(params, dict):
            kwargs['params'] = params
        else:
            kwargs['params'] = {}

        # add fixed request params
        kwargs['headers'] = {}
        kwargs['headers']['version'] = '2.4'
        if signed:
            # generate signature
            kwargs['data']['nonce'] = int(round(time.time()))
            kwargs['headers']['key'] = self.API_KEY
            kwargs['headers']['sign'] = self._generate_signature(kwargs['data'])
        response = getattr(self._session, method)(uri, **kwargs)
        return self._handle_response(response)

    def _handle_response(self, response):
        """Internal helper for handling API responses from the Binance server.
        Raises the appropriate exceptions when necessary; otherwise, returns the
        response.
        """
        if not str(response.status_code).startswith('2'):
            return
        try:
            res = response.json()
            return res
        except ValueError:
            return

    def _get(self, path, type=API_TYPE.ORDER, signed=False, **kwargs):
        return self._request('get', path, type, signed, **kwargs)

    def _post(self, path, type=API_TYPE.ORDER, signed=False, **kwargs):
        return self._request('post', path, type, signed, **kwargs)

    def _put(self, path, type=API_TYPE.ORDER, signed=False, **kwargs):
        return self._request('put', path, type, signed, **kwargs)

    def _delete(self, path, type=API_TYPE.ORDER, signed=False, **kwargs):
        return self._request('delete', path, type, signed, **kwargs)

    def _create_order(self, symbol, side, price, amount):
        params = {
            'symbol': symbol,
            'side': side,
            'type': 1,
            'price': price,
            'amount': amount
        }
        return self._post('create', signed=True, data=params)

    # 获取ticker
    def get_ticker(self, symbol):
        params = {
        }
        path = 'ticker/%s' % symbol
        return self._get(path, type=API_TYPE.QUOTE, data=params)

    # 获取深度行情
    def get_depth(self, symbol):
        params = {
            'offset': 10,
            'accuracy': 5,
            'size': 5
        }
        path = 'orderbook/%s' % symbol
        return self._get(path, type=API_TYPE.QUOTE, data=params)

    # 获取用户资产
    def get_user_balance(self):
        params = {}
        return self._post('list', type=API_TYPE.USER, data=params, signed=True)

    # 买单
    def create_buy_order(self, symbol, price, amount):
        return self._create_order(symbol, 1, price, amount)

    # 卖单
    def create_sell_order(self, symbol, price, amount):
        return self._create_order(symbol, 2, price, amount)

    # 获取批量订单
    def get_history_orders(self, page, size):
        '''
        :param page:
        :param size:
        :return:
        '''
        params = {
            'page': page,
            'size': size
        }
        return self._post('history', signed=True, data=params)

    # 撤销订单
    def cancel_order(self, symbol, order_id):
        params = {
            'symbol': symbol,
            'order_id': order_id
        }
        return self._post('remove', signed=True, data=params)

    # 获取挂单信息
    def get_open_orders(self, symbol, page, size):
        '''

        :param symbol:
        :param page:
        :param size:
        :return:
        '''
        params = {
            'symbol': symbol,
            'page': page,
            'size': size
        }
        return self._post('active', signed=True, data=params)
