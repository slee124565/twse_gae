from django.http import HttpResponse
from twse_gae.models_stock import StockModel
import codecs

def test_stock_update_from_web(request):
    if (StockModel.update_from_web()):
        t_model = StockModel.get_model()
        t_content = ''
        for t_id in t_model.csv_dict:
            t_content += u'{}:{},{}<br/>\n'.format(t_id,t_model.csv_dict[t_id][StockModel.CSV_COL_ABBRE_NAME],t_model.csv_dict[t_id][StockModel.CSV_COL_MARKET])
        return HttpResponse(t_content)
    else:
        return HttpResponse('test_stock_update_from_web fail')


def test_get_type_by_stk_no(request,p_stk_no):
    return HttpResponse(p_stk_no + ': ' + StockModel.get_type_by_stk_no(p_stk_no))


def test_check_db_exist(request, p_stk_no):
    return HttpResponse(p_stk_no + ': ' + str(StockModel.check_db_exist(p_stk_no)))
