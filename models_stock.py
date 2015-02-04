# -*- coding: utf-8 -*-

from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue

from lxml.html import document_fromstring
from lxml import etree

from datetime import date
from dateutil import parser
from dateutil.relativedelta import relativedelta

import csv,StringIO
import logging, httplib, pickle, codecs
from twse_gae.models import TWSEStockModel
from twse_gae.models_otc import OTCStockModel


CONFIG_STOCK_LIST = ['0050','2330','3293','6282']


class StockModel(db.Model):
    STOCK_TYPE_TWSE = 'twse'
    STOCK_TYPE_OTC = 'otc'
    URL_STOCK_INFO = 'http://mops.twse.com.tw/mops/web/ajax_quickpgm?encodeURIComponent=1&firstin=true&step=4&checkbtn=1&queryName=co_id&TYPEK2=&code1=&keyword4='
    URL_CODE_LIST_TWSE = 'http://isin.twse.com.tw/isin/C_public.jsp?strMode=2'
    URL_CODE_LIST_OTC = 'http://isin.twse.com.tw/isin/C_public.jsp?strMode=4'
    
    CSV_COL_ID = 'id'
    CSV_COL_ABBRE_NAME = 'abbre'
    CSV_COL_FULL_NAME = 'full'
    CSV_COL_MARKET = 'market'
    CSV_COL_INDUSTRY = 'industry'
    CSV_COL_MEMO = 'memo'
    
    MARKET_TYPE_TWSE = 'twse'
    MARKET_TYPE_OTC = 'otc'
    MARKET_TYPE_PUBLIC = 'public'
    MARKET_TYPE_EMERGING = 'emerging'
    CONST_MARKET_TYPE = {
                         MARKET_TYPE_TWSE: u'上市',
                         MARKET_TYPE_OTC: u'上櫃',
                         MARKET_TYPE_PUBLIC: u'公開發行',
                         MARKET_TYPE_EMERGING: u'興櫃',
                         
                         }
    

    '''
    csv_dict = {
                'twse': {code:name,...},
                'otc': {code:name,...},
                }
    '''
    
    csv_dict_pickle = db.BlobProperty()
    csv_dict = {}

    @classmethod
    def get_model(cls):
        fname = '{} {}'.format(__name__,'get_model')
        t_model = cls.get_or_insert('stock')
        if not t_model.csv_dict_pickle in [None, '']:
            t_model.csv_dict = pickle.loads(t_model.csv_dict_pickle)
        else:
            t_model.csv_dict = {}
        #logging.debug('{}: {}'.format(fname,str(t_model.csv_dict)))
        return t_model

    
    def get_stock_type(self, p_stk_no):
        fname = '{} {}'.format(__name__,'get_stock_type')
        
        t_type = None
        if p_stk_no in self.csv_dict:
            t_stk_info = self.csv_dict[p_stk_no]
            t_type_text = t_stk_info[StockModel.CSV_COL_MARKET]
            if t_type_text == StockModel.CONST_MARKET_TYPE[StockModel.MARKET_TYPE_TWSE]:
                t_type = StockModel.MARKET_TYPE_TWSE
            elif t_type_text == StockModel.CONST_MARKET_TYPE[StockModel.MARKET_TYPE_OTC]:
                t_type = StockModel.MARKET_TYPE_OTC
            elif t_type_text == StockModel.CONST_MARKET_TYPE[StockModel.MARKET_TYPE_PUBLIC]:
                t_type = StockModel.MARKET_TYPE_PUBLIC
            elif t_type_text == StockModel.CONST_MARKET_TYPE[StockModel.MARKET_TYPE_EMERGING]:
                t_type = StockModel.MARKET_TYPE_EMERGING
                
        logging.debug('{}: stock {} type is {}'.format(fname,p_stk_no,t_type))
        return t_type

    @classmethod
    def get_type_by_stk_no(cls, p_stk_no):
        t_model = cls.get_model()
        return t_model.get_stock_type(p_stk_no)
        
    @classmethod
    def get_stock(cls, p_stk_no):
        fname = '{} {}'.format(__name__,'get_stock')
        logging.debug('{}: with {}'.format(fname,p_stk_no))
        
        t_stk_type = cls.get_type_by_stk_no(p_stk_no)
        if t_stk_type == cls.MARKET_TYPE_TWSE:
            t_stock = TWSEStockModel.get_stock(p_stk_no)
        elif t_stk_type == cls.MARKET_TYPE_OTC:
            t_stock = OTCStockModel.get_stock(p_stk_no)
        else:
            t_stock = None
        logging.info('{}: with {}'.format(fname,t_stock))
        return t_stock
    
    '''
    @classmethod
    def parse_csv_dict(cls, p_type, p_csv_content):
        raise Exception('todo')
        fname = '{} {}'.format(__name__,'update_csv_dict')
        csv_reader = csv.DictReader(StringIO.StringIO(p_csv_content))
        data_dict = {}
        for row in csv_reader:
            t_item = dict(row)
            t_item_id = cls.parse_csv_col_date(t_item[cls.CSV_COL_ID])
            data_dict[str(t_item_id)] = t_item
            
        logging.debug('{}:{}'.format(fname,str(data_dict)))
        return data_dict
    '''
        
    @classmethod     
    def parse_web_content(cls,p_htmltable):
        t_dict_data = {}
        for t_row in p_htmltable[1:]:
            if len(t_row) == 6:
                t_id = t_row[0][0].text
                t_abbr_name = t_row[1][0].text
                t_full_name = t_row[2][0].text
                t_market = t_row[3][0].text
                t_industry = t_row[4][0].text
                t_memo = t_row[5][0].text
                if t_market in [cls.CONST_MARKET_TYPE[cls.MARKET_TYPE_TWSE],cls.CONST_MARKET_TYPE[cls.MARKET_TYPE_OTC]]:
                    t_dict_data[t_id] = {
                                     cls.CSV_COL_ABBRE_NAME: t_abbr_name,
                                     cls.CSV_COL_FULL_NAME: t_full_name,
                                     cls.CSV_COL_MARKET: t_market,
                                     cls.CSV_COL_INDUSTRY: t_industry,
                                     cls.CSV_COL_MEMO: t_memo,
                                     }
        return t_dict_data
                    
    @classmethod
    def update_from_web(cls):
        fname = '{} {}'.format(__name__,'update_from_web')
        logging.info('{}: fetch url:\n{}'.format(fname,cls.URL_STOCK_INFO))
        
        try :
            web_fetch = urlfetch.fetch(cls.URL_STOCK_INFO)
            if web_fetch.status_code == httplib.OK:
                web_content = document_fromstring(codecs.decode(web_fetch.content,'utf-8'))
                #web_content = document_fromstring(web_fetch.content)
                t_tables = web_content.xpath('//*[@id="zoom"]')
                t_dict_data = cls.parse_web_content(t_tables[0])
                t_model = cls.get_model()
                t_model.csv_dict = t_dict_data
                t_model.csv_dict_pickle = pickle.dumps(t_model.csv_dict)
                t_model.put()
                return True
            else:
                logging.warning('{}: urlfetch status code {}'.format(fname,web_fetch.status_code))
                return False
        except urlfetch.DownloadError, e:
            logging.warning('{} : Internet Download Error \n{}'.format(fname, e))
            return False
    
                    
            
            
            
            
            
        