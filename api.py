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
    
    #rootelements = ['Majandus', 'Keskkond', 'Rahvastik', 'Sotsiaalelu']
    rootelements = ['Majandus']
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
    
    def __init__(self, is_root=False, path=False):        
        self._is_root = is_root
        self._path = path
        self._tables = False
       
    @staticmethod
    def _parse_tables_list(r):
        '''parse html page with list of pages in it
        @param r requests `Response` object with function iter_lines()'''    
        items = []
        item = {}
        el_counts = []
        for line in r.iter_lines():
            if 'HREF="../../../../Dialog/varval.asp' in line:        
                if item:
                    item['element_counts'] = el_counts
                    el_counts = []        
                    items.append(item)
                    item = {}

                item['url'] = line.split('HREF="')[1].split('">')[0]
                item['name'] = line.split('">')[1].split('</A>')[0]
            elif item: #we already have 1st line data in item, next ones are element counts:
                if 'Uuendatud' in line:
                    item['updated'] = re.search("\d\d\.\d\d\.\d\d\d\d", line).group(0)
                elif '<I>(' in line and ')</I>' in line:
                    el_counts.append( int( line.split('<I>(')[1].split(')</I>')[0] ) )        
        return items
        
    def get_tables(self):
        'Download list of data tables under this sub category @todo: finish'
        if not self._tables:
            self._tables = LeafElement._parse_tables_list( requests.get( self._url_pattern.format(self._path) ) )
        return self._tables
        
    

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
                
