"""
Coinone Auto Trading Program
with GUI
Byunghyun Ban
https://github.com/needleworm
"""

import sys
#from PyQt5 import uic
from PyQt5 import QtGui
from PyQt5 import QtWidgets as Q
from PyQt5.QtCore import *
import base64
import hashlib
import hmac
import json
import time
import requests


doing_job = False

from ui import Ui_Dialog
ui_class = Ui_Dialog


def get_coin_list():
    coin_list = ["-"]

    url = 'https://api.coinone.co.kr/public/v2/markets/krw'

    headers = {
        'Content-type': 'application/json',
    }

    response = json.loads(requests.get(url, headers=headers).text)
    market = response["markets"]
    for el in market:
        coin_list.append(el["target_currency"].lower())

    coin_list.sort()
    return coin_list


def get_coin_price(coinTicker):
    coinTicker = coinTicker.lower()
    url = "https://api.coinone.co.kr/ticker/?format=json&currency=" + coinTicker
    response = requests.get(url).text
    price = json.loads(response)["last"]
    return float(price)


def get_encoded_payload(payload):
    payload['nonce'] = int(time.time() * 1000)

    dumped_json = json.dumps(payload)
    encoded_json = base64.b64encode(bytes(dumped_json, 'utf-8'))
    return encoded_json


def get_signature(encoded_payload, secret_key):
    signature = hmac.new(bytes(secret_key, "utf-8"), encoded_payload, hashlib.sha512)
    return signature.hexdigest()


def get_response(action, payload="", secret_key=""):
    url = 'https://api.coinone.co.kr/' + action

    encoded_payload = get_encoded_payload(payload)

    headers = {
        'Content-type': 'application/json',
        'X-COINONE-PAYLOAD': encoded_payload,
        'X-COINONE-SIGNATURE': get_signature(encoded_payload, secret_key),
    }

    response = requests.post(url, encoded_payload, headers=headers).text

    return json.loads(response)


def get_balance(coin, access_token, secret_key):
    response = get_response('v2/account/balance', {'access_token': access_token}, secret_key)
    coin = float(response[coin]["balance"])
    return coin


def buy_coin(access_token, secret_key, price, qty, coin):
    coin = coin.lower()
    payload = {
        "access_token": access_token,
        "price": str(price),
        "qty": str(qty),
        "currency": coin
    }
    return get_response("v2/order/limit_buy", payload, secret_key)


def sell_coin(access_token, secret_key, price, qty, coin):
    coin = coin.lower()
    payload = {
        "access_token": access_token,
        "price": str(price),
        "qty": str(qty),
        "currency": coin
    }
    return get_response("v2/order/limit_sell", payload, secret_key)


def buy_all(access_token, secret_key, coin, maxPrice):
    coin = coin.lower()
    krw = get_balance("krw", access_token, secret_key) * 0.998
    price = get_coin_price(coin)
    if price > maxPrice:
        return None, None, None
    qty = krw / price
    qty -= qty % 0.0001
    if qty <= 0:
        return None, None, None
    splt = str(qty).split(".")
    qtyStr = splt[0] + "." + splt[-1][:6]

    return "TRY> Coin Limit Buy\t" + str(time.ctime()) + "\nPrice: " + str(price) + "\tQuantity: " + qtyStr + "\n", \
           buy_coin(access_token, secret_key, price, qty, coin), price * qty


def sell_all(access_token, secret_key, coin, minPrice):
    coin = coin.lower()
    qty = get_balance(coin, access_token, secret_key)
    qty -= qty % 0.0001
    price = get_coin_price(coin)
    if price < minPrice:
        return None, None, None
    if qty <= 0:
        return None, None, None
    splt = str(qty).split(".")
    qtyStr = splt[0] + "." + splt[-1][:6]

    return "TRY> Coin Limit Sell\t" + str(time.ctime()) + "\nPrice: " + str(price) + "\tQuantity: " + qtyStr + "\n", \
        sell_coin(access_token, secret_key, price, qty, coin), price * qty


class autoTrader(QThread):
    text_out = pyqtSignal(str)

    def __init__(self, access_token, secret_key, coin, buyPrice, sellPrice):
        super().__init__()
        self.access_token = access_token
        self.secret_key = secret_key
        self.coin = coin
        self.buyPrice = buyPrice
        self.sellPrice = sellPrice

    def run(self):
        QtGui.QGuiApplication.processEvents()
        global doing_job
        if doing_job:
            self.text_out.emit("Auto Trading Bot Initiated.")
            # print("Auto Trading Bot Initiated.")

            self.text_out.emit("Target Coin : " + self.coin + "\n")
            # print("Target Coin : " + self.coin + "\n")
            latest_message = ""
            QtGui.QGuiApplication.processEvents()
        else:
            self.text_out.emit("Stop Auto Trading.\n\n")
            # print("Stop Auto Trading.\n\n")
            QtGui.QGuiApplication.processEvents()

        latest_price = 0
        while doing_job:
            time.sleep(0.5)
            QtGui.QGuiApplication.processEvents()
            lastBuyWon = None
            lastSellWon = None

            coinPrice = get_coin_price(self.coin)
            if coinPrice != latest_price:
                self.text_out.emit("Current Price is " + str(coinPrice))
                # print("Current Price is " + str(coinPrice))
                latest_price = coinPrice
            if coinPrice <= self.buyPrice:
                QtGui.QGuiApplication.processEvents()
                message, jsn, lastBuyWon = buy_all(self.access_token, self.secret_key, self.coin, self.buyPrice)
                if not message:
                    continue
                elif message[:20] == latest_message:
                    continue
                elif message:
                    self.text_out.emit(message)
                    # print(message)
                    latest_message = message[:20]
                QtGui.QGuiApplication.processEvents()
            elif coinPrice >= self.sellPrice:
                message, jsn, lastSellWon = sell_all(self.access_token, self.secret_key, self.coin, self.sellPrice)
                if not message:
                    continue
                elif message[:20] == latest_message:
                    continue
                elif message:
                    self.text_out.emit(message)
                    # print(message)
                    QtGui.QGuiApplication.processEvents()
                    latest_message = message[:20]
                    if lastSellWon and lastBuyWon:
                        self.text_out.emit("Income : " + str(lastSellWon - lastBuyWon) + "￦\n\n")
                        # print("Income : " + str(lastSellWon - lastBuyWon) + "￦\n\n")
                QtGui.QGuiApplication.processEvents()

        # print("Trading Stop!")
        QtGui.QGuiApplication.processEvents()


class SetCoin(QThread):
    text_out = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def change(self, price):
        self.text_out.emit(price)
        # print(price)
        QtGui.QGuiApplication.processEvents()


class WindowClass(Q.QMainWindow, ui_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.coin_list = get_coin_list()
        self.doing_job = False

        self.coin = ""
        self.access_token = ""
        self.secret_key = ""
        self.buyPrice = 0
        self.sellPrice = 0

        # 코인명 콤보박스에 업로드
        self.comboBox.addItems(self.coin_list)

        # 코인명이 바뀔 경우 코인명을 업데이트함
        self.comboBox.currentIndexChanged.connect(self.set_coin)

        # 버튼이 눌릴 경우 작업을 시작합니다.
        self.pushButton.clicked.connect(self.button_pushed)
        QtGui.QGuiApplication.processEvents()

    def button_pushed(self):
        if self.coin == "-":
            QtGui.QGuiApplication.processEvents()
            return

        # 정보 불러오기
        self.access_token = self.lineEdit.text().strip()
        self.secret_key = self.lineEdit_2.text().strip()
        self.buyPrice = float(self.lineEdit_3.text())
        self.sellPrice = float(self.lineEdit_4.text())
        self.checked = self.checkBox.isChecked()

        if not (self.access_token and self.secret_key and self.buyPrice and self.sellPrice and self.coin and self.checked):
            QtGui.QGuiApplication.processEvents()
            return

        global doing_job
        doing_job = not doing_job
        if doing_job:
            self.pushButton.setText("Stop Auto Trading")
            QtGui.QGuiApplication.processEvents()
        else:
            self.pushButton.setText("Start Auto Trading")
            QtGui.QGuiApplication.processEvents()
        # 멀티스레드로 오토트레이딩
        self.Bot = autoTrader(self.access_token, self.secret_key, self.coin, self.buyPrice, self.sellPrice)
        self.Bot.text_out.connect(self.textBrowser.append)
        QtGui.QGuiApplication.processEvents()
        self.Bot.run()

    def set_coin(self):
        self.coin = self.comboBox.currentText()
        if self.coin != "-":
            currentPrice = get_coin_price(self.coin)
        else:
            currentPrice = 0
        QtGui.QGuiApplication.processEvents()

        self.coinsetter1 = SetCoin()
        self.coinsetter1.text_out.connect(self.lineEdit_3.setText)
        self.coinsetter1.change(str(int(currentPrice * 0.997 * 1000) / 1000))
        QtGui.QGuiApplication.processEvents()

        self.coinsetter2 = SetCoin()
        self.coinsetter2.text_out.connect(self.lineEdit_4.setText)
        self.coinsetter2.change(str(int(currentPrice * 1.003 * 1000) / 1000))
        QtGui.QGuiApplication.processEvents()


if __name__ == "__main__":
    app = Q.QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    app.exec_()
    sys.exit(app.exec_)
