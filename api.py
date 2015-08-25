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
                    path = l.split('/')[1:-1]
                    self.paths.append(path)
    
    def __iter__(self):
        'Iterate over all paths'
        for path in self.paths:
            yield path
            

# Document tree
class Element(object):
    'Document tree element. Attributes are added dynamically when DocumentTree is initialised'
    def __init__(self, is_root=False, is_leaf=False):
        self._is_root = is_root
        self._is_leaf = is_leaf

class DocumentTree(object):
    '''Available document hirarchy is under attribute `data`. 
    You can use tab to scan through different (sub) categories'''
    __version__ = '0.1'
    
    def __init__(self):
        self.data = Element(True)
        #todo: for testing
        #self.paths = paths
        self.paths = Paths()
        self.paths.load()
        
        for path in self.paths:
            cur_el = self.data
            for label in path:
                label = clean_label(label)
                if not hasattr(cur_el, label):
                    setattr(cur_el, label, Element())
                cur_el = getattr(cur_el, label)
                
