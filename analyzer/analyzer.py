import pandas as pd
import numpy as np
import sklearn
import time
import datetime
import os

import timescaledb_model as tsdb

MAXINT = 2147483647
db = tsdb.TimescaleStockMarketModel('bourse', 'ricou', 'db', 'monmdp')        # inside docker
#db = tsdb.TimescaleStockMarketModel('bourse', 'ricou', 'localhost', 'monmdp') # outside docker

def last_to_float(last):
    if isinstance(last, float):
        return last
    return float(last.split('(')[0].replace(' ', ''))

def get_cid(symbol, companies):
    return companies.index[companies['symbol'] == symbol].tolist()[0]

def store_companies(df, name_bourse, old_companiz=pd.DataFrame()):
    if old_companiz.empty:
        companies_data = db.execute(query="SELECT id, name, mid, symbol, symbol_nf, isin, reuters, boursorama, pea, sector FROM companies")
        old_companiz = pd.DataFrame(companies_data, columns=['id', 'name', 'mid', 'symbol', 'symbol_nf', 'isin', 'reuters', 'boursorama', 'pea', 'sector'])
       
    companiz = (
        df
        .drop(columns=['last'])
        .drop(columns=['volume'])
    )
    
    companiz.reset_index(drop=True, inplace=True)
    companiz['id'] = companiz.index
    companiz.set_index('id', inplace=True)
    
    if name_bourse == 'pmapme':
        companiz['mid'] = 0
    else:
        companiz['mid'] = db.execute(query="SELECT id FROM markets WHERE alias = %s", args=(name_bourse,))[0][0]
    companiz['symbol_nf'] = 'idk'
    companiz['isin'] = 'idk'
    companiz['reuters'] = 'idk'
    companiz['boursorama'] = 'idk'
    companiz['pea'] = True
    if name_bourse == 'amsterdam':
        companiz['pea'] = False
    companiz['sector'] = 0
    
    if old_companiz.empty:
        return companiz
    
    filtered_companiz = companiz[~companiz['symbol'].isin(old_companiz['symbol'])]
    old_companiz = pd.concat([old_companiz, filtered_companiz], ignore_index=True)
    
    old_companiz.reset_index(drop=True, inplace=True)
    old_companiz['id'] = old_companiz.index
    old_companiz.set_index('id', inplace=True)
    
    return old_companiz
    

def store_stocks(df, timestamp_value, companies, old_stockz=pd.DataFrame()):
    # Filter rows where 'last' and 'volume' are not zero
    df_filtered = df[(df['last'] != 0) & (df['volume'] != 0)]
    
    # Rename 'last' column to 'value' and drop 'name' column
    stockz = df_filtered.rename(columns={'last': 'value'}).drop(columns=['name'])
    
    # Assign timestamp value to 'date' column
    stockz['date'] = timestamp_value
    
    # Map 'symbol' to 'cid' using companies DataFrame
    stockz['cid'] = stockz['symbol'].map(lambda x: get_cid(x, companies))
    
    # Drop 'symbol' column
    stockz.drop(columns=['symbol'], inplace=True)
    
    # Set 'date' as the index
    stockz.set_index('date', inplace=True)
    
    # Concatenate with old_stockz if it's not empty
    if not old_stockz.empty:
        stockz = pd.concat([old_stockz, stockz])
    
    return stockz
    
def push_companies(companiz):
    db.df_write(companiz, "companies", chunksize=100000, index=True, commit=True, if_exists='replace')
    
def push_stocks(stockz):
    db.df_write(stockz, "stocks", chunksize=100000, index=True, commit=True)
    
def push_daystocks(daystockz):
    db.df_write(daystockz, "daystocks", chunksize=100000, index=True, commit=True)

def store_file(name, website, companiz, stockz, daystockz):
    #if db.is_file_done():#name):
    #    return
    if website.lower() == "boursorama":
        try:
            df = pd.read_pickle("/home/bourse/data/boursorama/" + name)  # is this dir ok for you ?
        except:
            year = name.split()[1].split("-")[0]
            df = pd.read_pickle("/home/bourse/data/boursorama/" + year + "/" + name)
        # to be finished
                
        market = name.split(" ")
        name_bourse = market[0]
        date = market[1] + " " + market[2].split('.')[0]
        timestamp_value = datetime.datetime.strptime(date, '%Y-%m-%d %H_%M_%S')
        day_timestamp_value = datetime.datetime.strptime(date.split(' ')[0], '%Y-%m-%d')
        
        # Prétraitements sur df
        
        df['last'] = df['last'].apply(last_to_float)
        
        # =====================[ MARKET ]=====================
        
        companiz = store_companies(df, name_bourse, companiz)
        
        # =====================[ STOCKS ]=====================
        
        stockz = store_stocks(df, timestamp_value, companiz.copy(), stockz)
        
        # ====================[ DAYSTOCKS ]====================
        
        if daystockz.empty:
            daystockz = (
                stockz
                .rename(columns={'value': 'open'})
            )
            
            daystockz['close'] = daystockz['open']
            daystockz['high'] = daystockz['open']
            daystockz['low'] = daystockz['open']
        else:
            daystockz = daystockz.reset_index().set_index('cid')
            stockz_copy = stockz.copy().reset_index().set_index('cid')
            stockz_copy = stockz_copy[stockz_copy['date'] == timestamp_value]
            daystockz['close'] = stockz_copy['value']
            for idx in daystockz.index:
                if idx in stockz_copy.index:
                    if daystockz.loc[idx, 'high'] < stockz_copy.loc[idx, 'value']:
                        daystockz.loc[idx, 'high'] = stockz_copy.loc[idx, 'value']
                    if daystockz.loc[idx, 'low'] > stockz_copy.loc[idx, 'value']:
                        daystockz.loc[idx, 'low'] = stockz_copy.loc[idx, 'value']
            daystockz['date'] = day_timestamp_value
            daystockz = daystockz.reset_index().set_index('date')

        # ====================[ FILE_DONE ]====================
        
        db.execute(query="INSERT INTO file_done VALUES (%s);", args=(name,), commit=True)
        
        return companiz, stockz, daystockz

def resample_group(df):
        return df.resample('D').agg({
            'value': [('open', 'first'), ('close', 'last'), ('high', 'max'), ('low', 'min')],
            'volume': 'max'
        })

def store_daystocks(stockz):
    daystockz = stockz.groupby('cid').apply(resample_group, include_groups=False).dropna()
    daystockz = daystockz.reset_index()
    daystockz.columns = ['cid', 'date', 'open', 'close', 'high', 'low', 'volume']
    
    daystockz.reset_index(drop=True, inplace=True)
    daystockz.set_index('date', inplace=True)
    return daystockz

def store_day(market, day, website, year, files):
    files_to_store = [file for file in files if file.startswith(market + " " + day)]
    
    companiz = pd.DataFrame()
    stockz = pd.DataFrame()
    daystockz = pd.DataFrame()
    
    for fts in files_to_store:
        companiz, stockz, daystockz = store_file(fts, website, companiz, stockz, daystockz)
    
    #companiz, stockz = store_file(files_to_store[0], website, companiz, stockz)
    
    #daystockz = store_daystocks(stockz)

    push_stocks(stockz)
    push_companies(companiz)
    push_daystocks(daystockz)

def store_year_of_market(market, year, website, files):
    files_to_store = [file for file in files if file.startswith(market)]
    
    days = set()
    for file in files_to_store:
        days.add(file.split(' ')[1])
    
    for day in days:
        if day.startswith('2020-01'):
            store_day(market, day, website, year, files_to_store)

def store_year(year, website, file_done):
    files = os.listdir('/home/bourse/data/boursorama/' + year)
    files = [x for x in files if x not in file_done]
    
    markets = set()
    for file in files:
        markets.add(file.split(' ')[0])
    
    for market in markets:
        store_year_of_market(market, year, website, files)
        
def store_everything(website):
    files = os.listdir('/home/bourse/data/boursorama/')
    file_done = db.execute(query="SELECT * FROM file_done")
    file_dones = [f[0] for f in file_done]
    
    years = set()
    for file in files:
        years.add(file)
    
    #for year in years:
        #store_year(year, website, file_dones)
    store_year('2020', website, file_dones)

if __name__ == '__main__':
    print(__file__)
    store_everything('boursorama')
    #store_year_of_market('amsterdam', '2020', 'boursorama')
    print("Done")