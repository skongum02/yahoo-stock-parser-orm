# yahoo-stock-parser-orm

An easy to use Yahoo! finance stock parser that gets data from Yahoo! finance and converts it to a python object for easier analysis

There are two main methods.
getHistoricalData and getCurrentData

They both return a dictionary of { tickerSymbol: [PriceInfo] } object

## usage

```Python
from PriceData import *
tickers = ['spy', 'fb']
pd = PriceData()

#Parameters are tickers, periodsBack, periodType, errMsg

prices = pd.getHistoricalData(tickers, 180, PeriodType.Day, "") # Means for these tickes get me back 180 trading days of data
spyPrices = prices['spy']

#Get the latest closing price of SPY
print(spyPrices[0].close)
print(spyPrices[0].date)
```

