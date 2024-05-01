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
    cid = companies.index[companies['symbol'] == symbol].tolist()[0]
    return cid

def store_companies(df, name_bourse, old_companiz=pd.DataFrame()):
    companiz = (
        df
        .drop(columns=['last'])
        .drop(columns=['volume'])
    )
    
    companiz.reset_index(drop=True, inplace=True)
    companiz['id'] = companiz.index
    companiz.set_index('id', inplace=True)

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
    stockz = (
        df
        .loc[(df['last'] != 0) & (df['volume'] != 0)]
        .rename(columns={'last': 'value'})
        .drop(columns=['name'])
    )

    stockz.reset_index(drop=True, inplace=True)
        
    stockz['date'] = timestamp_value
    stockz['cid'] = 0
    stockz['cid'] = stockz['symbol'].apply(lambda x: get_cid(x, companies))
    stockz.drop(columns=['symbol'], inplace = True)
        
    stockz.set_index('date', inplace=True)
    
    if old_stockz.empty:
        return stockz
    
    old_stockz = pd.concat([old_stockz, stockz])
    
    return old_stockz
    
def push_companies(companiz):
    db.df_write(companiz, "companies", chunksize=100000, index=True, commit=True)
    
def push_stocks(stockz):
    db.df_write(stockz, "stocks", chunksize=100000, index=True, commit=True)
    
def push_daystocks(daystockz):
    db.df_write(daystockz, "daystocks", chunksize=100000, index=True, commit=True)

def store_file(name, website, companiz, stockz):
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
        
        # Prétraitements sur df
        
        df['last'] = df['last'].apply(last_to_float)
        
        # =====================[ MARKET ]=====================
        
        #dfshit = df.copy()
        #dfshit['symbol'] = dfshit['symbol'].apply(tempfunc)
        companiz = store_companies(df, name_bourse, companiz)
        #companiz = store_companies(dfshit, name_bourse, companiz)
        
        #print(companiz)
        #push_companies(companiz)
        
        # =====================[ STOCKS ]=====================
        
        stockz = store_stocks(df, timestamp_value, companiz.copy(), stockz)
        #print(stockz)
        #push_stocks(stockz)
        
        # ====================[ FILE_DONE ]====================
        
        #db.execute(query="INSERT INTO file_done VALUES (%s);", args=(name,), commit=True)
        
        return companiz, stockz

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

def store_day(market, day, website):
    files = os.listdir('/home/bourse/data/boursorama/2020')
    files_to_store = [file for file in files if file.startswith(market + " " + day)]
    
    companiz = pd.DataFrame()
    stockz = pd.DataFrame()
    
    for fts in files_to_store:
        companiz, stockz = store_file(fts, website, companiz, stockz)
    
    #companiz, stockz = store_file(files_to_store[0], website, companiz, stockz)
    
    daystockz = store_daystocks(stockz)

    push_stocks(stockz)
    push_companies(companiz)
    push_daystocks(daystockz)

if __name__ == '__main__':
    print(__file__)
    store_day('amsterdam', '2020-08-05', 'boursorama')
    #store_file("amsterdam 2020-01-01 13_12_01.528372.bz2", "boursorama")
    #store_file("compA 2020-01-01 09:02:02.532411", "boursorama")
    print("Done")