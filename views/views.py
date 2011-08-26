from models.ds import Booking, Passenger, Sector, Document
from models.ds import PassengerSectorBooking, LastUse

from google.appengine.ext import db

from datetime import datetime, timedelta
from pytz.gae import pytz
from pytz import timezone

# Constants, private functions
_active_period = timedelta(days=90)
_expiry_period = timedelta(days=365*2)

def _current_date():
  return datetime.now(timezone('Australia/Sydney')).date()

def _use(obj_key):
  key_str = str(obj_key)
  now = _current_date()
  u = LastUse.get_or_insert(key_str, obj=obj_key)
  if now > u.last_use:
    u.last_use = now
    db.put_async(u)

# get functions

# By identifiers
def get_booking_by_id(booking_id):
  b = Booking.get_by_id(booking_id)
  if b:
    _use(b.key())
    return b.to_dict()
  return None

def get_sector_by_id(sector_id):
  s = Sector.get_by_id(sector_id)
  if s:
    return s.to_dict()
  return None

def get_passenger_by_sn(service_no):
  p = Passenger.get_by_key_name(service_no)
  if p:
    return p.to_dict()
  return None

def get_document_by_id(doc_id):
  d = Document.get_by_id(doc_id)
  if d:
    return d.to_dict()

# Searches
def get_bookings(active_only=True):
  res = {}
  now = _current_date()
  for cat in ['UNPAID', 'PAID', 'CREDIT', 'CANCELLED']:
    q = Booking.all()
    q.filter("state = ", cat)
    if active_only:
      q.filter("last_date >= ", now - _active_period)

    res[cat] = [b.to_dict() for b in q]

  return res

def get_bookings_by_booking_ref(booking_ref, company=None, active_only=False):
  q = Booking.all()
  q.filter('booking_ref = ', booking_ref)

  if company:
    q.filter('company = ', company)

  if active_only:
    q.filter("last_date >= ", _current_date() - _active_period)

  return [b.to_dict() for b in q]

def get_passengers_by_name(last_name, init=None):
  q = Passenger.all()
  q.filter('last_name >= ', last_name)
  q.filter('last_name < ', last_name + u'\ufffd')

  if init:
    q.filter('init = ', init)

  q.order('last_name')
  q.order('init')

  return [p.to_dict() for p in q]

def get_sectors_by_passenger_sn(service_no):
  p = db.Key.from_path('Passenger', service_no)
  psb = PassengerSectorBooking.all()
  psb.filter('passenger = ', p)

  return [r.sector.to_dict() for r in psb]

def get_sectors_by_booking_id(booking_id):
  b = db.Key.from_path('Booking', booking_id)
  ss = Sector.all()
  ss.filter('booking = ', b)

  return [s.to_dict() for s in ss]

def get_bookings_by_passenger_sn(service_no, course=None, active_only=False):
  p = db.Key.from_path('Passenger', service_no)
  q = PassengerSectorBooking.all()
  q.filter('passenger = ', p)

  res = {}
  for psb in q:
    res[psb.booking.key().id()] = psb.booking.to_dict()

  return res.values()

def get_passenger_fares_by_sector_id(sector_id):
  s = db.Key.from_path('Sector', sector_id)
  q = PassengerSectorBooking.all()
  q.filter('sector = ', s)
  
  res = []
  for psb in q:
    p = psb.passenger.to_dict()
    p['fare'] = psb.fare_type
    res.append(p)

  return res

def get_documents_by_booking_id(booking_id):
  b = db.Key.from_path('Booking', booking_id)
  dd = Document.all()
  dd.filter('booking = ', b)
  return [d.to_dict() for d in dd]

def get_current_courses():
  now = _current_date()
  q = Booking.all()
  q.filter("last_date >= ", now - _active_period)

  return set([b.course for b in q])


# add functions

def add_booking(company, booking_ref, course, **kwds):
  res = Booking(company=company, booking_ref=booking_ref, course=course)

  if 'fare' in kwds:
    res.fare = kwds['fare']
  if 'paid_by' in kwds:
    res.paid_by = kwds['paid_by']
    if res.last_date < kwds['paid_by']:
      res.last_date = kwds['paid_by']
  if 'state' in kwds:
    res.state = kwds['state']
  if 'amount_in_credit' in kwds:
    res.amount_in_credit = kwds['amount_in_credit']
  if 'credit_expiry' in kwds:
    res.credit_expiry = kwds['credit_expiry']
    if res.last_date < kwds['credit_expiry']:
      res.last_date = kwds['credit_expiry']

  res.put()
  _use(res.key())
  return res.to_dict()

def add_document(booking_id, date, blob_info, desc=None):
  res = None
  b = db.Key.from_path('Booking', booking_id)

  if b:
    res = Document(date=date, blob_key=blob_info.key(), booking=b, desc=desc)
    res.put()
    _use(b.key())

  return res.to_dict()

def add_sector(booking_id, date, from_loc, to_loc, service):
  res = None
  b = Booking.get_by_id(booking_id)

  if b:
    res = Sector(date=date, from_loc=from_loc, to_loc=to_loc, service=service, booking=b)
    res.put()
    
    if date > b.last_date:
      b.last_date = date
      b.put()

    _use(b.key())

  return res.to_dict()

def add_passenger_to_sector(sector_id, service_no, last_name=None, init=None, fare=None):
  s = Sector.get_by_id(sector_id)
  p = Passenger.get_by_key_name(service_no)

  if not p:
    p = Passenger(service_no=service_no, key_name=service_no, last_name=last_name, init=init)
    p.put()

  if s:
    psb = PassengerSectorBooking(passenger=p, sector=s, booking=s.booking, fare_type=fare, key_name=str(p.key())+str(s.key()))
    psb.put()

    _use(s.booking.key())
    _use(p.key())

  return p.to_dict()

# set/update functions
def update_booking(booking_id, **kwds):
  b = Booking.get_by_id(booking_id)

  if b and len(kwds) > 0:
    if 'booking_ref' in kwds:
      b.booking_ref = kwds['booking_ref']

    if 'company' in kwds:
      b.company = kwds['company']

    if 'course' in kwds:
      b.course = kwds['course']

    if 'fare' in kwds:
      b.fare = kwds['fare']

    if 'paid_by' in kwds:
      b.paid_by = kwds['paid_by']
      if b.paid_by > b.last_date:
        b.last_date = b.paid_by

    if 'state' in kwds:
      b.state = kwds['state']

    if 'amound_in_credit' in kwds:
      b.amount_in_credit = kwds['amount_in_credit']

    if 'credit_expiry' in kwds:
      b.credit_expiry = kwds['credit_expiry']
      if b.credit_expiry > b.last_date:
        b.last_date = b.credit_expiry

    b.put()
    _use(b.key())

def update_document(doc_id, **kwds):
  d = Document.get_by_id(doc_id)

  if d and len(kwds) > 0:
    if 'date' in kwds:
      d.date = kwds['date']
    if 'desc' in kwds:
      d.desc = kwds['desc']

    d.put()
    _use(d.booking.key())

def update_passenger(service_no, **kwds):
  p = Passenger.get_by_key_name(service_no)

  if p and len(kwds) > 0:
    if 'last_name' in kwds:
      p.last_name = kwds['last_name']
    if 'init' in kwds:
      p.init = kwds['init']

    p.put()
    _use(p.key())

def update_sector(sector_id, **kwds):
  s = Sector.get_by_id(sector_id)

  if s and len(kwds) > 0:
    if 'date' in kwds:
      s.date = kwds['date']
    if 'from_loc' in kwds:
      s.from_loc = kwds['from_loc']
    if 'to_loc' in kwds:
      s.to_loc = kwds['to_loc']
    if 'service' in kwds:
      s.service = kwds['service']

    s.put()
    _use(s.booking.key())

def update_passenger_fare(service_no, sector_id, fare_type):
  s = db.Key.from_path('Sector', sector_id)
  p = db.Key.from_path('Passenger', service_no)
  psb = PassengerSectorBooking.get_by_key_name(str(p)+str(s))

  if psb:
    psb.fare_type = fare_type
    psb.put()
    _use(psb.booking.key())
    _use(psb.passenger.key())

# delete functions
def delete_booking_by_id(booking_id):
  b = Booking.get_by_id(booking_id)

  if b:
    db.delete(b.documents)
    db.delete(b.sectors)
    db.delete(b.passengers_rel)

  db.delete_async(db.Key.from_path('LastUse', str(b.key())))
  b.delete()

def delete_sector_by_id(sector_id):
  s = Sector.get_by_id(sector_id)
  if s:
    db.delete(s.passengers_rel)

  s.delete()

def remove_pax_from_sector(sector_id, service_no):
  s = db.Key.from_path('Sector', sector_id)
  p = db.Key.from_path('Passenger', service_no)
  db.delete(db.Key.from_path('PassengerSectorBooking', str(p)+str(s)))
  _use(p)

def remove_pax_from_booking(booking_id, service_no):
  b = db.Key.from_path('Booking', booking_id)
  p = db.Key.from_path('Passenger', service_no)
  psb = PassengerSectorBooking.all(keys_only=True)
  psb.filter('booking = ', b)
  psb.filter('passenger = ', p)
  _use(p)
  _use(b)
  db.delete(psb)
