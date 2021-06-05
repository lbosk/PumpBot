from binance.client import Client
from binance.enums import *
from binance.exceptions import *
from binance.websockets import BinanceSocketManager
from twisted.internet import reactor
import sys
import math
import json
import requests
import webbrowser
import time
import urllib
import os
import ssl
from threading import Thread
from pynput.keyboard import Key, Listener

# UTILS
def float_to_string(number, precision=10):
    return '{0:.{prec}f}'.format(
        number, prec=precision,
    ).rstrip('0').rstrip('.') or '0'

def log(information):
    currentTime = time.strftime("%H:%M:%S", time.localtime())
    logfile.writelines(str(currentTime) + " --- " + str(information) + "\n")

def marketSell(amountSell):
    print("Market selling due to error")
    order = client.order_market_sell(
        symbol=tradingPair,
        quantity=amountSell)
    log("Sold at market price.")
    print("Sold at market price")

def topupBNB(min_balance, topup):
    # Top up BNB balance if it drops below minimum specified balance
    bnb_balance = client.get_asset_balance(asset='BNB')
    balance=str(bnb_balance['free'])
    print("You have "+balance+" BNB in your wallet")    
    bnb_balance = float(bnb_balance['free'])
    balancePair = 'BNB' + str(quotedCoin)
    if bnb_balance < min_balance:
        qty = round(topup - bnb_balance, 2)
        print("Topping up BNB wallet with "+str(qty)+" BNB to avoid transaction fees")
        log("Getting "+str(qty)+" more BNB to top-up wallet")
        order = client.order_market_buy(symbol=balancePair, quantity=qty)
        return order
    return False

# set orderCompleted to false
orderCompleted = False

# websocket stuff
def process_message(msg):
    if msg['e'] == 'executionReport':
        if msg['X'] == 'FILLED':
            global orderCompleted
            orderCompleted = True

def quitProgram():
    print("Quitting, this could take a few seconds!")
    log("Quitting program")
    # close log file
    logfile.close()
    # stop socket
    reactor.stop()
    # quit program
    sys.exit()

Panic= False
def on_press(key):
    global Panic
    if key == Key.space:
        Panic=True
        return False
   
# make log file
logfile = open("log.txt", "w+")

# read json file
try:
    f = open('keys.json', )
except FileNotFoundError:
    log("Keys.json not found.")
    print("Error. Keys.json not found. \nRemember to rename your keys.json.example to keys.json.")
    quitProgram()
    
log("Loading API keys.")
data = json.load(f)
apiKey = data['apiKey']
apiSecret = data['apiSecret']
if (apiKey == "") or (apiSecret == ""):
    log("API Keys Missing.")
    print("One or Both of you API Keys are missing.\n"
    "Please open the keys.json to include them.")
    quitProgram()

log("API keys successfully loaded.")
log("Loading config.json settings.")
f = open('config.json', )
data = json.load(f)
# loading config settings
quotedCoin = data['quotedCoin'].upper()
buyLimit = data['buyLimit']
percentOfWallet = float(data['percentOfWallet']) / 100
manualQuoted = float(data['manualQuoted'])
profitMargin = float(data['profitMargin']) / 100
stopLoss = float(data['stopLoss'])
currentVersion = float(data['currentVersion'])
endpoint = data['endpoint']
buyTimeout = data["buyTimeout"]
sellTimeout = data["sellTimeout"]
fiatcurrency = data['fiatcurrency']
log("config.json settings successfully loaded.")

# check we have the latest version
ssl._create_default_https_context = ssl._create_unverified_context
url = 'https://raw.githubusercontent.com/fj317/PumpBot/master/config.json'
urllib.request.urlretrieve(url, 'version.json')
try:
    f = open('version.json', )
except FileNotFoundError:
    log("version.json not found. Quitting program.")
    print("Fatal error checking versions. Please try again\n")
    quitProgram()
data = json.load(f)
f.close()
latestVersion = data['currentVersion']
os.remove("version.json")
if latestVersion > currentVersion:
    log("Current version {}. New version {}".format(currentVersion, latestVersion))
    print("\nNew version of the script found. Please download the new version...\n")
    time.sleep(3)

endpoints = {
    'default': 'https://api.binance.{}/api',
    'api1': 'https://api1.binance.{}/api',
    'api2': 'https://api2.binance.{}/api',
    'api3': 'https://api3.binance.{}/api'
}

try:
    Client.API_URL = endpoints[endpoint]
except Exception as d:
    print("Endpoint error. Using default endpoint instead")
    log("Endpoint error. Using default endpoint instead.")

# create binance Client
client = Client(apiKey, apiSecret)

# do websocket stuff
bm = BinanceSocketManager(client)
bm.start_user_socket(process_message)
bm.start()

# get all symbols with coinPair as quote
tickers = client.get_all_tickers()
symbols = []
for ticker in tickers:
    if quotedCoin in ticker["symbol"]: symbols.append(ticker["symbol"])

# cache average prices
log("Caching all quoted coin pairs.")
print("Caching all {} pairs average prices...\nThis can take a while. Please, be patient...\n".format(quotedCoin))
tickers = client.get_ticker()
averagePrices = []
for ticker in tickers:
    if quotedCoin in ticker['symbol']:
        averagePrices.append(dict(symbol=ticker['symbol'], wAvgPrice=ticker["weightedAvgPrice"]))

# getting btc conversion
response = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json')
data = response.json()
in_USD = float((data['bpi'][fiatcurrency]['rate_float']))
print("Sucessfully cached " + quotedCoin + " pairs!")
log("Sucessfully cached quoted coin pairs.")

# find amount of bitcoin to use
log("Getting quoted balance amount.")
try:
    QuotedBalance = float(client.get_asset_balance(asset=quotedCoin)['free'])
except Exception as e:
    log("Error with getting balance.")
    log(e)
    print("Error with getting balance.")
    quitProgram()

# decide if use percentage or manual amount
if manualQuoted <= 0:
    AmountToSell = QuotedBalance * percentOfWallet
else:
    AmountToSell = manualQuoted

# ensure wallet has BNB transaction fees
log("Checking BNB balance if topup required.")
print("Checking BNB balance if topup required.")
topupBNB(0.01, 0.02)

# nice user message
print(''' 
 ___                                ___           _   
(  _`\                             (  _`\        ( )_ 
| |_) ) _   _   ___ ___   _ _      | (_) )   _   | ,_)
| ,__/'( ) ( )/' _ ` _ `\( '_`\    |  _ <' /'_`\ | |  
| |    | (_) || ( ) ( ) || (_) )   | (_) )( (_) )| |_ 
(_)    `\___/'(_) (_) (_)| ,__/'   (____/'`\___/'`\__)
                         | |                          
                         (_)                          ''')
# wait until coin input
print("\nInvesting amount for {}: {}".format(quotedCoin, float_to_string(AmountToSell)))
print("Investing amount in "+fiatcurrency+": {}".format(float_to_string((in_USD * AmountToSell), 2)))
log("Waiting for trading pair input.")
tradedCoin = input("\nCoin pair: ").upper()
tradingPair = tradedCoin + quotedCoin

# get price for coin
x=next((ticker for ticker in averagePrices if ticker["symbol"] == tradingPair), {"symbol": "", "wAvgPrice":0})
averagePrice = x["wAvgPrice"]

# if average price fails then get the current price of the trading pair (backup in case average price fails)
if averagePrice == 0:
    try:
        averagePrice = float(client.get_avg_price(symbol=tradingPair)['price'])
    except:
        print("Unable to retrieve the price of pair "+ tradingPair)
        quitProgram()

log("Calculating amount of coin to buy.")
# calculate amount of coin to buy
amountOfCoin = AmountToSell / float(averagePrice)

log("Rounding amount of coin.")
# rounding the coin amount to the specified lot size
info = client.get_symbol_info(tradingPair)
minQty = float(info['filters'][2]['stepSize'])
amountOfCoin = float_to_string(amountOfCoin, int(- math.log10(minQty)))
minPrice = float(info['filters'][0]['tickSize'])


if buyLimit != 1:
    # rounding price to correct dp
    log("Rounding price for coin.")
    averagePrice = float(averagePrice) * buyLimit
    averagePrice = float_to_string(averagePrice, int(- math.log10(minPrice)))

    log("Attempt to create limit buy order.")
    try:
        # buy order
        order = client.order_limit_buy(
            symbol=tradingPair,
            quantity=amountOfCoin,
            price=averagePrice)
    except BinanceAPIException as e:
        print("A BinanceAPI error has occurred. Code = " + str(e.code))
        print(
            e.message + ". Please use https://github.com/binance/binance-spot-api-docs/blob/master/errors.md to find "
                        "greater details on error codes before raising an issue.")
        log("Binance API error has occured on buy order.")
        quitProgram()
    except Exception as d:
        print(d)
        print("An unknown error has occurred.")
        log("Unknown error has occured on buy order.")
        quitProgram()
else:
    log("Attempt to create market buy order")
    # do market order shit here
    try:
        order = client.order_market_buy(
            symbol=tradingPair,
            quantity=amountOfCoin)
    except BinanceAPIException as e:
        print("A BinanceAPI error has occurred. Code = " + str(e.code))
        print(
            e.message + ". Please use https://github.com/binance/binance-spot-api-docs/blob/master/errors.md to find "
                        "greater details on error codes before raising an issue.")
        log("Binance API error has occured on buy order.")
        quitProgram()
    except Exception as d:
        print(d)
        print("An unknown error has occurred.")
        log("Unknown error has occured on buy order.")
        quitProgram()
    
# waits until the buy order has been confirmed
print("Waiting for coin to buy...")
while not(orderCompleted):
    pass
# when order compelted reset to false for next order
orderCompleted = False

message = 'Buy order has been made: bought {} {} at price {} {}!'
message = message.format(coinOrderQty,tradedCoin,coinPriceBought*coinOrderQty,quotedCoin)
print(message)
log(message)

# once finished waiting for buy order we can process the sell order
print('Processing sell order.\nIn any moment press SPACEBAR to sell and exit.')
log("Processing sell order.")
Buy_Timeout = False
start_time = time.time()
while not(orderCompleted) and not(Buy_Timeout):
    elapsed_time = time.time() - start_time
    Buy_Timeout = (elapsed_time >= buyTimeout)

# once bought we can get info of order
log("Getting buy order information.")

# fix problem with getting data from binance servers
while True:
    try:
        OrderStatus=order["status"]
        OrderID=order["clientOrderId"]
        if len(order["fills"]): #if I did not buy anything, fills is empty
            coinOrderInfo = order["fills"][0]
            coinPriceBought = float(coinOrderInfo['price'])
            coinOrderQty = float(coinOrderInfo['qty'])
        else:
            coinPriceBought = 0
            coinOrderQty = 0            
        break
    except:
        log("Error getting data from Binance servers, retrying.")

# if I got out by timeout
if Buy_Timeout:
    # cancel the order
    result = client.cancel_order(
        symbol=tradingPair,
        origClientOrderId =OrderID)
    if ORDER_STATUS_NEW in OrderStatus:
        #I did not buy anything, therefore stop here
        print("Did not succeed to buy")
        log("Did not succeed to buy")
        quitProgram()

# when order compelted reset to false for next order
orderCompleted = False

print('Buy order has been made!')
log("Buy order successfully made.")

# once finished waiting for buy order we can process the sell order
print('Processing sell order.')
log("Processing sell order.")

log("Calculate price to sell at and round.")
# find price to sell coins at
priceToSell = coinPriceBought * profitMargin
# rounding sell price to correct dp
roundedPriceToSell = float_to_string(priceToSell, int(- math.log10(minPrice)))

# get stop price
if stopLoss <= 1:
    # place ther trigger at half way between coinPriceBought and stopLimitPrice
    triggerThreshold = (1+stopLoss)/2
else:
    # place ther trigger above coinPriceBought, at half distance (coinPriceBought-stopLimitPrice)
    triggerThreshold = (3*stopLoss-1)/2
stopPrice = float_to_string(triggerThreshold * coinPriceBought, int(- math.log10(minPrice)))
stopLimitPrice = float_to_string(stopLoss * coinPriceBought, int(- math.log10(minPrice)))
log("Attempting to create sell order.")
try:
    # oco order (with stop loss)
    order = client.create_oco_order(
        symbol=tradingPair,
        quantity=coinOrderQty,
        side=SIDE_SELL,
        price=roundedPriceToSell,
        stopPrice=stopPrice,
        stopLimitPrice=stopLimitPrice,
        stopLimitTimeInForce=TIME_IN_FORCE_GTC
    )
except BinanceAPIException as e:
    print("A BinanceAPI error has occurred. Code = " + str(e.code))
    print(
        e.message + " Please use https://github.com/binance/binance-spot-api-docs/blob/master/errors.md to find "
                    "greater details "
                    "on error codes before raising an issue.")
    log(e)
    log("Binance API error has occured on sell order.")
    marketSell(coinOrderQty)
    quitProgram()
except Exception as d:
    print("An unknown error has occurred.")
    log(d)
    log("Unknown error has occured on sell order.")
    marketSell(coinOrderQty)
    quitProgram()

print('Sell order has been made!')
log("Sell order successfully made.")
# open binance page to trading pair
webbrowser.open('https://www.binance.com/en/trade/' + tradingPair)

print("Waiting for sell order to be completed...")
listener = Listener(on_press=on_press)
listener.start()

Sell_Timeout = False
start_time = time.time()
while not(orderCompleted) and not(Sell_Timeout) and not (Panic):
    elapsed_time = time.time() - start_time
    Sell_Timeout = (elapsed_time >= sellTimeout)

# if I got out by timeout
if Sell_Timeout or Panic:
    # cancel the present OCO order
    OrderID=order["orders"][0]["clientOrderId"]
    result = client.cancel_order(
        symbol=tradingPair,
        origClientOrderId=OrderID)
    #place a sell to the market order
    order = client.order_market_sell(
        symbol=tradingPair,
        quantity=coinOrderQty)
    if Sell_Timeout:
        print("Sell order by timeout has been filled!")
        log("Sell order by timeout has been filled.")
    else:
        print("Sell order by user request!")
        log("Sell order by user request.")
        
else:
    print("Limit sell order has been filled!")
    log("Limit sell order has been filled.")
    
coinPriceSold=float(order["cummulativeQuoteQty"])
message = 'Sell order has been completed: sold {} {} at price {} {}!'
message = message.format(coinOrderQty,tradedCoin,coinPriceSold,quotedCoin)
print(message)
log(message)

newQuotedBalance = float(client.get_asset_balance(asset=quotedCoin)['free'])
profit = newQuotedBalance - QuotedBalance
profit=float_to_string(profit, 2+int(- math.log10(minPrice)))

message = 'Profit made: {} {} = {:.2f} {}'
message = message.format(profit,quotedCoin,float(profit)*in_USD,fiatcurrency)
print(message)
log(message)

# wait for Enter to close
input("\nPress Enter to Exit...")

# quit
quitProgram()
