def convert_keys_str2hex(conf):

    if 'filters' in conf:
        # filtersconvierte strings de key hexadecimales
        for flter in conf['filters']:
            if 'key' in flter:
                flter['key'] = int(flter['key'],16)
                # recorro el segundo nivel de filtros
                if type(flter['value']) == list:
                    for flter2 in flter['value']:
                        flter2['key'] = int(flter2['key'],16)
    '''
    if 'destinations' in conf:
        # convierte los keys dentro de los source de destination
        for dest in conf['destinations']:
            if 'source' in dest and 'key' in dest['source']:
                dest['source']['key'] = int(dest['source']['key'],16)
    '''
    return conf

def get_value_from_ds(ds,key):
    try:
        element = ds.data_element(key)
        if element:
            return element.value
    except KeyError:
        return None
    except Exception, e:
        raise e
    return None
