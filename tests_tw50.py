from django.http import HttpResponse
from twse_gae.models_tw50 import TW50Model


def update_tw50_view(request):
    if (TW50Model.update_from_web()):
        t_model = TW50Model.get_model()
        t_content = ''
        for t_id in t_model.csv_dict:
            t_content += u'{}:{}<br/>\n'.format(t_id,t_model.csv_dict[t_id]['name'])
        return HttpResponse(t_content)
    else:
        return HttpResponse('update_tw50_view fail')
    
    
    
def tw50_list_view(request):
    t_list = TW50Model.get_id_list()
    if len(t_list) == 0:
        TW50Model.update_from_web()
        t_list = TW50Model.get_id_list()
    return HttpResponse(str(t_list))
    
