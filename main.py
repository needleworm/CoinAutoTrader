"""
Coinone Auto Trading Program
with GUI
Byunghyun Ban
https://github.com/needleworm
"""

import sys
from PyQt5 import uic
from PyQt5 import QtGui
from PyQt5 import QtWidgets as Q
from PyQt5.QtCore import *
import base64
import hashlib
import hmac
import json
import time
import httplib2

ui_class = uic.loadUiType("resources/main.ui")

coin_list = [
    "-",
    "BTC", "ETH", "XRP", "XLM", "EOS", "BCH", "KLAY",
    "LTC", "TRX", "LINK", "DOT", "LUNA", "ADA", "BSV",
    "XTZ", "ATOM", "QTUM", "IOTA", "ETC", "SKLAY", "NEO",
    "AIP", "ASTA", "MCH", "BMP", "FCR", "MNR", "TOROCUS",
    "VIVI", "RUSH", "MSB", "LBXC", "ORC", "NFUP", "TRIX",
    "ISR", "1INCH", "PICA", "HANDY", "BAAS", "ARPA", "DVI",
    "MIR", "LMCH", "KSP", "MOV", "TOM", "AXL", "ZIL", "CBANK",
    "OMG", "MTS", "FLETA", "TEMCO", "ASM", "PIB", "PURE",
    "REN", "DUCATO", "TMTG", "QTBK", "XPN", "GOM2", "TMC",
    "REDI", "SNX", "SXP", "BEL", "QTCON", "EXE", "DRC",
    "STPL", "BORA", "ISDT", "DRM", "AMO", "WIKEN", "HIBS",
    "SUSHI", "HINT", "UOS", "PSC", "ABL", "IBP", "BFC",
    "COMP", "GRT", "BNA", "KRT", "RNX", "PROM", "EGG", "AVAX",
    "AAVE", "DAD", "FTT", "KDAG", "LINA", "TRCL", "DON", "SRM",
    "CRV", "DODO", "BCHA", "KAVA", "ANKR", "KNC", "CAMP", "ZRX",
    "SIX", "KVI", "IOTX", "BTT", "JST", "ALPHA", "BAT", "AOA",
    "SUN", "ONX", "STPT", "IPX", "PCI", "TIP", "INJ", "BASIC",
    "DATA", "BTG", "FET", "CTSI", "VSYS", "MVC", "PXL", "MATIC",
    "HUM", "KAI", "DIA", "ONT", "BAL", "ORBS", "COS", "SOC",
    "KSC", "BOT", "OBSR", "MBL", "DVX", "CBK", "SHOW", "CKB",
    "AXS", "LUA", "BAND", "OGN", "BNT", "BZRX", "CLB", "DMG",
    "FRONT", "GAS", "GET", "HARD", "KSM", "MTA", "NEST", "ONG",
    "STAKE", "TOMOE", "UMA"
]

access_token = "c237f2cd-46f8-4ea5-b0f5-b342381d3a95"
secret_key = "67a6bcf6-4b1d-4f2f-a07c-4e40c01748b3"


def get_encoded_payload(payload):
    payload['nonce'] = int(time.time() * 1000)

    dumped_json = json.dumps(payload)
    encoded_json = base64.b64encode(bytes(dumped_json, 'utf-8'))
    return encoded_json


def get_signature(encoded_payload, secret_key):
    signature = hmac.new(bytes(secret_key, "utf-8"), encoded_payload, hashlib.sha512)
    return signature.hexdigest()


def get_response(action, payload, secret_key):
    url = '{}{}'.format('https://api.coinone.co.kr/', action)

    encoded_payload = get_encoded_payload(payload)

    headers = {
        'Content-type': 'application/json',
        'X-COINONE-PAYLOAD': encoded_payload,
        'X-COINONE-SIGNATURE': get_signature(encoded_payload, secret_key),
    }

    http = httplib2.Http()
    response, content = http.request(url, 'POST', body=encoded_payload, headers=headers)

    return content


def get_balance(coin, access_token, secret_key):
    response = json.loads(get_response('v2/account/balance', {'access_token': access_token}, secret_key))
    coin = float(response[coin]["balance"])
    return coin


def get_coin_price(coinTicker):
    url = "https://api.coinone.co.kr/ticker/?format=json&currency=" + coinTicker
    http = httplib2.Http()
    _, response = http.request(url, "GET")
    response = json.loads(response)
    return float(response["last"])


def buy_coin(access_token, secret_key, price, qty, coin):
    payload = {
        "access_token": access_token,
        "price": str(price),
        "qty": str(qty),
        "currency": coin
    }
    return json.loads(get_response("v2/order/limit_buy", payload, secret_key))


def sell_coin(access_token, secret_key, price, qty, coin):
    payload = {
        "access_token": access_token,
        "price": str(price),
        "qty": str(qty),
        "currency": coin
    }
    return json.loads(get_response("v2/order/limit_sell", payload, secret_key))


def buy_all(access_token, secret_key, coin, maxPrice=None):
    krw = get_balance("krw", access_token, secret_key)
    price = get_coin_price(coin)
    if price > maxPrice:
        return None, None, None
    qty = krw / price
    qty -= qty % 0.0001
    if qty <= 0:
        return None, None, None
    splt = str(qty).split(".")
    qtyStr = splt[0] + "." + splt[-1][:6]

    return "Coin Limit Buy\n" + str(time.ctime()) + "\nPrice: " + str(price) + "\tQuantity: " + qtyStr + "\n" + \
           buy_coin(access_token, secret_key, price, qty, coin), price * qty


def sell_all(access_token, secret_key, coin, minPrice=None):
    qty = get_balance(coin, access_token, secret_key)
    qty -= qty % 0.0001
    price = get_coin_price(coin)
    if price < minPrice:
        return None, None, None
    if qty <= 0:
        return None, None, None
    splt = str(qty).split(".")
    qtyStr = splt[0] + "." + splt[-1][:6]

    return "Coin Limit Sell\n" + str(time.ctime()) + "\nPrice: " + str(price) + "\tQuantity: " + qtyStr + "\n", \
        sell_coin(access_token, secret_key, price, qty, coin), price * qty


def auto_trading(access_token, secret_key, coin, buyAt, sellAt):
    while True:
        lastBuyPrice = buyAt
        coinPrice = get_coin_price(coin)
        if  coinPrice < buyAt:
            message, jsn, lastBuyPrice = buy_all(access_token, secret_key, coin, buyAt)
            if message:
                print(message)

        elif coinPrice > sellAt:
            message, jsn, lastSellPrice = sell_all(access_token, secret_key, coin, sellAt)
            if message:
                print(message)
            if lastSellPrice and lastBuyPrice:
                print("Income : " + str(lastSellPrice - lastBuyPrice) + "￦")
        time.sleep(0.5)


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
        self.text_out.emit("Auto Trading Bot Initiated.")

        self.text_out.emit("Target Coin : " + self.coin.upper())
        while True:
            QtGui.QGuiApplication.processEvents()
            lastBuyPrice = self.buyPrice
            coinPrice = get_coin_price(self.coin)
            if coinPrice < self.buyPrice:
                message, jsn, lastBuyPrice = buy_all(access_token, secret_key, self.coin, self.buyPrice)
                if message:
                    self.text_out.emit(message)

            elif coinPrice > self.sellPrice:
                message, jsn, lastSellPrice = sell_all(access_token, secret_key, self.coin, self.sellPrice)
                if message:
                    self.text_out.emit(message)
                if lastSellPrice and lastBuyPrice:
                    self.text_out.emit("Income : " + str(lastSellPrice - lastBuyPrice) + "￦")
            time.sleep(1)


class setCoin(QThread):
    text_out = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def change(self, price):
        print(price)
        self.text_out.emit(price)

class WindowClass(Q.QMainWindow, ui_class[0]):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.coin = ""
        self.access_token = ""
        self.secret_key = ""
        self.buyPrice = 0
        self.sellPrice = 0

        # 코인명 콤보박스에 업로드
        self.comboBox.addItems(coin_list)

        # 코인명이 바뀔 경우 코인명을 업데이트함
        self.comboBox.currentIndexChanged.connect(self.set_coin)

        # 버튼이 눌릴 경우 작업을 시작합니다.
        self.pushButton.clicked.connect(self.button_pushed)

    def button_pushed(self):
        if self.coin == "-":
            return

        # 정보 불러오기
        self.access_token = self.lineEdit.text()
        self.secret_key = self.lineEdit_2.text()
        self.buyPrice = int(self.lineEdit_3.text())
        self.sellPrice = int(self.lineEdit_4.text())
        self.checked = self.checkBox.isChecked()

        if not (self.access_token and self.secret_key and self.buyPrice and self.sellPrice and self.coin and self.checked):
            return

        # 멀티스레드로 오토트레이딩
        self.Bot = autoTrader(self.access_token, self.secret_key, self.coin, self.buyPrice, self.sellPrice)
        self.Bot.text_out.connect(self.textBrowser.append)
        QtGui.QGuiApplication.processEvents()
        self.Bot.run()

    def set_coin(self):
        self.coin = self.comboBox.currentText()
        if self.coin != "-":
            currentPrice = int(get_coin_price(self.coin))
        else:
            currentPrice = 0

        self.coinsetter1 = setCoin()
        self.coinsetter1.text_out.connect(self.lineEdit_3.setText)
        self.coinsetter1.change(str(int(currentPrice * 0.995)))

        self.coinsetter2 = setCoin()
        self.coinsetter2.text_out.connect(self.lineEdit_4.setText)
        self.coinsetter2.change(str(int(currentPrice * 1.005)))


if __name__ == "__main__":
    app = Q.QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    app.exec_()
