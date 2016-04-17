import glob
import os
import csv
import math
from datetime import date, timedelta, datetime
from shutil import copyfile
import sys

if sys.version_info[0] == 3:
    from html.parser import HTMLParser
else:
    from HTMLParser import HTMLParser

__author__ = 'vskong'


class PeriodType:
    Day,Week,Month = range(3)

class PriceInfo:
    def __init__(self, date, open, high, low, close, vol, prevClose=0):
        self.date = date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = vol
        self.prevClose = prevClose

    def __str__(self):
        return (self.date + " " + str(self.close))

class YahooFinanceParser(HTMLParser):
    startScraping = False
    peek = False
    price = 0
    grabData = False
    openPrice = 0
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "th":
            self.peek = True
        elif self.startScraping:
            self.grabData = True
    def handle_endtag(self, tag):
        if self.grabData:
            self.grabData = False
    def handle_data(self, data):
        if self.grabData:
            self.price = data.lower()
            print(self.price)
            self.grabData = False
            self.startScraping = False
        elif self.peek and data.lower() == "open:":
            self.startScraping = True
            self.peek = False


class PriceData:
  HISTORICAL_PRICE_URL = "http://ichart.yahoo.com/table.csv?s="
  CURRENT_PRICE_URL = "http://finance.yahoo.com/d/quotes.csv?s="
  HTML_SCRAPE_URL = "http://finance.yahoo.com/q?s="

  H_START_DATE_COLUMN=0
  H_OPEN_PRICE_COLUMN=1
  H_HIGH_PRICE_COLUMN=2
  H_LOW_PRICE_COLUMN=3
  H_CLOSE_PRICE_COLUMN=4
  H_VOLUME_COLUMN=5

  LOG_LEVEL = 1
  TRACE = 0
  ERROR = 1
  DEBUG = 2

  currentTime = datetime.now()


  def __init__(self, logLevel=1):
    self.LOG_LEVEL = logLevel
    self.offline = False
    self.python3 = False
    if sys.version_info[0] == 3:
        self.python3 = True

  def getHistoricalData(self, tickers, periodsBack, periodType, errMsg):
    symbols = {}
    if not self.offline:
        numDays = 0
        periodParameter = ""
        if periodsBack <=0:
            print ("Error..periods back is less than or equal to zero " + periodsBack)
        if periodType == PeriodType.Day:
            numDays = timedelta(days= (((periodsBack-1)/5)+1)*7)
            periodParameter = "&g=d"
        elif periodType == PeriodType.Week:
            numDays = timedelta(weeks=periodsBack)
            periodParameter = "&g=w"
        elif periodType == PeriodType.Month:
            numDays = timedelta(months=periodsBack)
            periodParameter = "&g=m"
        toDate = date.today() + timedelta(days=1)
        fromDate = toDate-numDays
        parameterString = ("a=%s&b=%s&c=%s&d=%s&e=%s&f=%s") %(fromDate.month-1,fromDate.day,fromDate.year,toDate.month-1,toDate.day, toDate.year)
        parameterString = parameterString + periodParameter + "&ignore=.csv"

        closeDate = ""
        closeDateMatches = True
        for ticker in tickers:
            closeDateCheck = self.populateHistoricalTickers(symbols, ticker, parameterString)
            if (self.LOG_LEVEL <= PriceData.TRACE):
                print (closeDateCheck)
            if closeDate == "":
               closeDate = closeDateCheck
            elif closeDate != closeDateCheck:
               closeDateMatches = False
               errMsg = "Ticker " + ticker + " has not been updated yet"
               raise Exception(errMsg)
        if (self.LOG_LEVEL <= PriceData.DEBUG):
            print("Close Date is " + closeDate)
    return symbols


  def populateHistoricalTickers(self, symbols,ticker, parameterString ):
        if len(parameterString) > 1:
           url = self.HISTORICAL_PRICE_URL + ticker + "&" + parameterString
           if (self.LOG_LEVEL <= PriceData.DEBUG):
               print(url)
           data = self.getDataFromServer(url)
           data = data.split('\n')
        else:
            data = open('output/input.csv').read()
            if (self.LOG_LEVEL <= PriceData.TRACE):
                print (data)
            data = data.split('\n')
        priceData = []
        closeDate = ""
        for line in data[1:]:
            line = line.split(',')
            if len(line) > 1:
                priceInfo = PriceInfo(line[self.H_START_DATE_COLUMN].strip("\""),
                                      float(line[self.H_OPEN_PRICE_COLUMN].strip("\"")),
                                      float(line[self.H_HIGH_PRICE_COLUMN].strip("\"")),
                                      float(line[self.H_LOW_PRICE_COLUMN].strip("\"")),
                                      float(line[self.H_CLOSE_PRICE_COLUMN].strip("\"")),
                                      int(line[self.H_VOLUME_COLUMN].strip("\"")),
                                      )
                priceData.append(priceInfo)
                if closeDate == "":
                   closeDate = line[0]
        if (self.LOG_LEVEL <= PriceData.DEBUG):
          debugData = []
          for p in priceData:
            debugData.append(str(p))
          print (",".join(debugData))
        symbols[ticker] = priceData
        return closeDate

  def getCurrentData(self, tickers, numChunks=30, openPrice=False):
    counter = 0
    symbols = {}

    numTickers = len(tickers)
    remainder = numTickers%numChunks
    self.populateTickers(symbols, tickers[counter:remainder], openPrice)

    counter = remainder
    while counter < numTickers:
        self.populateTickers(symbols, tickers[counter:(counter + numChunks)])
        counter += numChunks
    missingSymbols = list(set(tickers) - set(symbols.keys()))
    print ("Missing symbols: {0}".format(missingSymbols))
    for i in missingSymbols:
        symbols[i] = str(self.scrapeData(i)) + "," + self.currentTime.strftime('%m/%d/%Y')
    return symbols

  def getCurrentStockInfo(self, tickers, numChunks=30):
    counter = 0
    symbols = {}

    numTickers = len(tickers)
    remainder = numTickers%numChunks
    self.populateStockInfo(symbols, tickers[counter:remainder])

    counter = remainder
    while counter < numTickers:
        self.populateStockInfo(symbols, tickers[counter:(counter + numChunks)])
        counter += numChunks
    missingSymbols = list(set(tickers) - set(symbols.keys()))
    print ("Missing symbols: {0}".format(missingSymbols))
    for i in missingSymbols:
        symbols[i] = str(self.scrapeData(i)) + "," + self.currentTime.strftime('%m/%d/%Y')
    return symbols

  def getOpenPrice(self, tickers, numChunks=30):
      return self.getCurrentData(tickers, numChunks, True)

  def getDataFromServer(self, url):
    if not self.python3:
        import urllib2
        data = urllib2.urlopen(url).read().decode('utf-8-sig')
    else:
        import urllib.request
        data = urllib.request.urlopen(url).read().decode('utf-8-sig')
    return data

  def scrapeData(self,symbol):
      td = YahooFinanceParser()
      stockURL = self.HTML_SCRAPE_URL + symbol
      if (self.LOG_LEVEL <= self.DEBUG):
          print (stockURL)
      td.feed(self.getDataFromServer(stockURL))
      print ("CurrentPrice: {0} OpenPrice: {1}".format(td.price, td.openPrice))
      try:
          currPrice = str(td.price)
          currPrice = float(currPrice.translate(None, ','))
      except ValueError:
          print ("ValueError {0}".format(td.price))
          currPrice = 0
      return currPrice



  def populateTickers(self, symbols,tickers, openPrice=False):
        if not self.offline:
            symbolString =""
            parameters = "&f=l1|d1|o0"
            for key in tickers:
                symbolString+= (key + "+")
            symbolString = symbolString[:len(symbolString)-1]
            url = self.CURRENT_PRICE_URL + symbolString + parameters
            if (self.LOG_LEVEL <= self.TRACE):
                print (url)
            data = self.getDataFromServer(url)
            print ("Data")
            if (self.LOG_LEVEL <= self.TRACE):
                print (data)
            data = data.split(os.linesep)
        else:
            data = open('output/input.csv').read()
            if (self.LOG_LEVEL <= self.TRACE):
                print (data)
            data = data.split('\n')
        priceData = []
        tickerCounter = 0
        for line in data:
            line = line.split(',')
            if (self.LOG_LEVEL <= self.DEBUG):
                print(line)
            if len(line) > 1:
                if openPrice:
                    currPrice = line[4]
                else:
                    currPrice = line[0]
                if (self.LOG_LEVEL <= self.DEBUG):
                    print(currPrice)
                if currPrice == 'N/A' or float(currPrice) == 0:
                    if (self.LOG_LEVEL <= self.DEBUG):
                        print ("Need to scrape data")
                    currPrice = str(self.scrapeData(tickers[tickerCounter]))
                    line[2] = self.currentTime.strftime('%m/%d/%Y');
                priceData.append(currPrice)
                priceData.append(line[2].strip("\""))
                if self.LOG_LEVEL <= self.TRACE:
                    print(priceData)
                symbols[line[1].strip("\"").lower()] = ",".join(priceData)
            tickerCounter+=1
            priceData = []

  def populateStockInfo(self, symbols,tickers):
        if not self.offline:
            symbolString =""
            parameters = "&f=l1d1ohgvps"
            for key in tickers:
                symbolString+= (key + "+")
            symbolString = symbolString[:len(symbolString)-1]
            url = self.CURRENT_PRICE_URL + symbolString + parameters
            if (self.LOG_LEVEL <= self.TRACE):
                print (url)
            data = self.getDataFromServer(url)
            if (self.LOG_LEVEL <= self.TRACE):
                print ("Data")
                print (data)
            data = data.split(os.linesep)
        else:
            data = open('output/input.csv').read()
            if (self.LOG_LEVEL <= self.TRACE):
                print (data)
            data = data.split('\n')
        tickerCounter = 0
        for line in data:
            line = line.split(',')
            if (self.LOG_LEVEL <= self.DEBUG):
                print(line)
            if len(line) > 1:
                si = PriceInfo(line[1], float(line[2]), float(line[3]), float(line[4]), float(line[0]), int(line[5]), float(line[6]))
                if self.LOG_LEVEL <= self.TRACE:
                    print(si)
                symbols[line[7].strip("\"").lower()] = si
            tickerCounter+=1
