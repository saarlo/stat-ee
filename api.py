import requests
import urllib
import re

'''
api interface for pub.stat.ee database
Usage:
    ```
    tree = DocumentTree()
    tables = tree.data.Majandus.Ehitus.Ehitus_ja_kasutusload.list_data()
    print [table['name'] for table in tables]
    r = tree.data.Majandus.Ehitus.Ehitus_ja_kasutusload.get_data(tables[1])
    r.status_code
    print len(r.text)
    ```
'''

# Utils
def is_numeric(value):
    try:
        int(value)
        return True
    except ValueError as e:
        return False
    
def clean_label(label):
    label = label.replace('-', '')
    if is_numeric(label[:2]):
        return label[2:]
    else:
        return label
    
class Paths(object):
    'Utility class - Manage paths to available data tables in pub.stat.ee'
    
    rootelements = ['Majandus', 'Keskkond', 'Rahvastik', 'Sotsiaalelu']
    #rootelements = ['Majandus'] # for testing only activate one category
    url_pattern = 'http://pub.stat.ee/px-web.2001/Database/{}/databasetreeNodes.js'
    
    def __init__(self):
        self.paths = []
    
    def load(self):
        'Load paths from pub.stat.ee. This can take up to a minute.'
        for el in Paths.rootelements:
            r = requests.get(Paths.url_pattern.format(el))        
            for l in r.iter_lines():
                if l[:7] == 'insDoc(':
                    path = l[:-3].split('/')[1:]
                    self.paths.append(path)
    
    def __iter__(self):
        'Iterate over all paths'
        for path in self.paths:
            yield path
            

# Document tree
class Element(object):
    'Document tree element. Attributes are added dynamically when DocumentTree is initialised'
    def __init__(self, is_root=False):
        self._is_root = is_root

class LeafElement(Element):
    'Document tree element special case - leaf node'
    
    _url_pattern = 'http://pub.stat.ee/px-web.2001/Database/{}'
    _data_url = 'http://pub.stat.ee/px-web.2001/Dialog/Saveshow.asp'
    
    def __init__(self, is_root=False, path=False):        
        self._is_root = is_root
        self._path = path
        self._datasets = False
        
    def list_data(self):
        'Download list of data tables under this sub category @todo: finish'
        if not self._datasets:
            self._datasets = LeafElement._parse_data_list( requests.get( self._url_pattern.format(self._path) ) )
        return self._datasets
    
    def get_data(self, dataset):        
        '''
        @param (dict) table item, one element returned by list_data
        @return (Respnse) requests.Response object. has function `iterate_lines` and params `status_code`, `text`
        '''
        return requests.post(self._data_url, data=LeafElement._parse_params(dataset), headers=headers)
       
    @staticmethod
    def _parse_data_list(r):
        '''parse html page that holds list of available datasets in sub-category
        @param (Response) r: requests.Response object with function iter_lines()'''    
        items = []
        item = {}
        el_counts = []
        var_names = []
        for line in r.iter_lines():
            if 'HREF="../../../../Dialog/varval.asp' in line:        
                if item:
                    item['var_counts'], item['vars'] = el_counts, var_names                         
                    items.append(item)
                    item, el_counts, var_names = {}, [], [] #reset aux vars

                item['url'] = line.split('HREF="')[1].split('">')[0]
                item['name'] = line.split('lang=2">')[1].split('</A>')[0]
            elif item: #we already have 1st line data in item, next ones are element counts:
                if 'Uuendatud' in line:
                    item['updated'] = re.search("\d\d\.\d\d\.\d\d\d\d", line).group(0)
                elif '<LI><B>' in line and ':</B>' in line:
                    var_names.append( line.split('<LI><B>')[1].split(':</B>')[0] )
                elif '<I>(' in line and ')</I>' in line:
                    el_counts.append( int( line.split('<I>(')[1].split(')</I>')[0] ) )        
        if item:
            # last item
            items.append(item)
        return items
    
        
    @staticmethod
    def _parse_params(item):
        '''
        Generate POST parameters for data request
        @param (dict) item 
        @return (list) list of (name, value) pairs - http POST parameters for data request
        '''
        params = []
        table_id = item['name'].split(':')[0]
        params.append( ('matrix', table_id ) )
        params.append( ('infofile', table_id[:2] + '_' + table_id[2:] + '.htm' ) )
        params.append( ('root', item['url'].split('path=')[1].split('&')[0]) )
        params.append( ('ti', item['url'].split('ti=')[1].split('&')[0]) )
        params.append( ('classdir', item['url'].split('path=')[1].split('&')[0]) )
        params.append( ('noofvar', len(item['var_counts'])) )
        params.append( ('elim', 'NNNN') )
        params.append( ('numberstub', 2) )
        params.append( ('lang', 2) )
        params.append( ('varparm', item['url'].split('?')[1]) )
        params.append( ('sel', 'J\xe4tka') )    
        params.append( ('pxkonv', 'prnmsc') ) # table format csv without titles

        for i, val in enumerate( item['var_counts'] ):
            params.append( ('Valdavarden' + str(i+1), val ) )
            for j in range(val):
                params.append( ('values' + str(i+1), j+1 ) )
        for i, val in enumerate( item['vars'] ):
            params.append( ('var' + str(i+1), val) )
            params.append( ('context' + str(i+1), '') )


        # hardcoded and copied from request params, probably has to generalise to fit all datasets
        params += [('classdir2', ''), ('description', ''), ('descriptiondefault', '0'), ('hasAggregno', '0'), 
            ('headceller', '1'), ('mainlang', ''), ('mapname', ''), ('multilang', ''),
            ('stubceller', '4'), ('timevalvar', 'Aasta')]

        return params
        
    

class DocumentTree(object):
    '''Available document hirarchy is under attribute `data`. 
    You can use tab to scan through different (sub) categories'''
    __version__ = '0.1'
    
    def __init__(self):
        self.data = Element(True)
        #todo: for testing
        #self._paths = paths
        self._paths = Paths()
        self._paths.load()
        self._build_tree()
        
    def _build_tree(self):         
        for path in self._paths:
            for path in self._paths:
                cur_el = self.data
                # not including last path element in loop, as it is filename (.asp)
                for i, label in enumerate(path[:-1]):
                    label = clean_label(label)
                    if i == len(path) -2: # Leaf element (last of labels)
                        setattr(cur_el, label, LeafElement(path='/'.join(path)))                        
                    elif not hasattr(cur_el, label):
                        setattr(cur_el, label, Element())
                    cur_el = getattr(cur_el, label)
                
