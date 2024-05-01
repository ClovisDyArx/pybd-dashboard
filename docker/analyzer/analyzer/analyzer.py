import pandas as pd
import numpy as np
import sklearn
import time
import datetime

import timescaledb_model as tsdb

MAXINT = 2147483647
db = tsdb.TimescaleStockMarketModel('bourse', 'ricou', 'db', 'monmdp')        # inside docker
#db = tsdb.TimescaleStockMarketModel('bourse', 'ricou', 'localhost', 'monmdp') # outside docker

def last_to_float(last):
    return float(last.split('(c)')[0].replace(' ', ''))

def get_cid(symbol):
    return db.execute(query="SELECT id FROM companies WHERE symbol = %s", args=(symbol,))[0][0]

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
    
    return old_companiz
    

def store_stocks(df, timestamp_value, old_stockz):
    stockz = (
        df
        .loc[(df['last'] != 0) & (df['volume'] != 0)]
        .rename(columns={'last': 'value'})
        .drop(columns=['name'])
    )

    stockz.reset_index(drop=True, inplace=True)
        
    stockz['date'] = timestamp_value
    stockz['cid'] = 0
    stockz['cid'] = stockz['symbol'].apply(get_cid)
    stockz.drop(columns=['symbol'], inplace = True)
        
    stockz.set_index('date', inplace=True)
    
    return stockz
    
def push_companies(companiz):
    db.df_write(companiz, "companies", chunksize=100000, index=True, commit=True)
    
def push_stocks(stockz):
    db.df_write(stockz, "stocks", chunksize=100000, index=True, commit=True)

def store_file(name, website):
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
        
        def tempfunc(tp):
            return tp.split('N')[0]
        
        # =====================[ MARKET ]=====================
        
        #dfshit = df.copy()
        #dfshit['symbol'] = dfshit['symbol'].apply(tempfunc)
        companiz = store_companies(df, name_bourse)
        #companiz = store_companies(dfshit, name_bourse, companiz)
        
        print(companiz)
        push_companies(companiz)
        
        # =====================[ STOCKS ]=====================
        
        stockz = store_stocks(df, timestamp_value)
        #print(stockz)
        push_stocks(stockz)
                
        # ====================[ DAYSTOCKS ]====================
        
        # ====================[ FILE_DONE ]====================
        
        db.execute(query="INSERT INTO file_done VALUES (%s);", args=(name,), commit=True)

if __name__ == '__main__':
    print(__file__)
    store_file("amsterdam 2020-01-01 13_12_01.528372.bz2", "boursorama")
    #store_file("compA 2020-01-01 09:02:02.532411", "boursorama")
    print("Done")
