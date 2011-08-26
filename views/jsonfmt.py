from datetime import datetime
import simplejson as json

def json_handler(obj):
  if hasattr(obj, 'isoformat'):
    return obj.isoformat()
  if isinstance(obj, set):
    return list(obj)
###  elif isinstance(obj, ...):
###    return ...
  else:
    raise TypeError, 'Object of type %s with value of %s is not JSON serializable' % (type(Obj), repr(Obj))
