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


class TW50Model(db.Model):
    URL_TEMPLATE = 'http://www.twse.com.tw/ch/trading/indices/twco/tai50i.php'

    csv_dict_pickle = db.BlobProperty()
    csv_dict = {}

    @classmethod
    def get_model(cls):
        fname = '{} {}'.format(__name__,'get_model')
        t_model = cls.get_or_insert('tw50')
        if not t_model.csv_dict_pickle in [None, '']:
            t_model.csv_dict = pickle.loads(t_model.csv_dict_pickle)
        else:
            t_model.csv_dict = {}
        #logging.debug('{}: {}'.format(fname,str(t_model.csv_dict)))
        return t_model

    @classmethod     
    def parse_web_content(cls,p_htmltable):
        t_dict_data = {}
        
        t_tr_count = 0
        for t_row in p_htmltable:
            if t_row.tag == 'tr' and len(t_row) == 6:
                if t_tr_count > 2:
                    t_name = t_row[1].text
                    #t_name = codecs.decode(t_name,'big5')
                    t_dict_data[t_row[0].text] = {
                                                  'name': t_name,
                                                  'A': t_row[2].text,
                                                  'B': t_row[3].text,
                                                  'C': t_row[4].text,
                                                  'D': t_row[5].text,
                                                  }
                t_tr_count += 1
        
        return t_dict_data
                    
    @classmethod
    def update_from_web(cls):
        fname = '{} {}'.format(__name__,'update_from_web')
        logging.info('{}: fetch url:\n{}'.format(fname,cls.URL_TEMPLATE))
        
        try :
            web_fetch = urlfetch.fetch(cls.URL_TEMPLATE)
            if web_fetch.status_code == httplib.OK:
                #web_content = document_fromstring(codecs.decode(web_fetch.content,'utf-8'))
                web_content = document_fromstring(web_fetch.content)
                t_tables = web_content.xpath('//*[@id="contentblock"]/td/table[3]/tr/td/span/div[3]/table')
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

    @classmethod
    def get_id_list(cls):
        t_model = cls.get_model()
        t_list = t_model.csv_dict.keys()
        t_list.sort(key=lambda x:x[0])
        return t_list