from google.appengine.ext import db
from google.appengine.ext import blobstore

from datetime import datetime, timedelta
from pytz.gae import pytz
from pytz import timezone

class Booking(db.Model):
  booking_ref = db.StringProperty(required=True)
  company = db.StringProperty(required=True)
  course = db.StringProperty(required=True)
  fare = db.FloatProperty(indexed=False)
  paid_by = db.DateProperty(default=None)
  state = db.CategoryProperty(default="UNPAID", choices=["UNPAID", "PAID", "CREDIT", "CANCELLED"])
  amount_in_credit = db.FloatProperty(default=None)
  credit_expiry = db.DateProperty(default=None)
  last_date = db.DateProperty(default=datetime.now(timezone('Australia/Sydney')).date())

  def __str__(self):
    return "{'booking_ref':"+str(self.booking_ref)+ \
            ",'company':"+str(self.company)+ \
            ",'course':"+str(self.course)+ \
            ",'fare':"+str(self.fare)+ \
            ",'paid_by':"+str(self.paid_by)+ \
            ",'state':"+str(self.state)+ \
            ",'amount_in_credit':"+str(self.amount_in_credit)+ \
            ",'credit_expiry':"+str(self.credit_expiry)+ \
            ",'last_date':"+str(self.last_date)+ \
            "}"

class Passenger(db.Model):
  service_no = db.StringProperty(default=None)
  last_name = db.StringProperty(required=True)
  init = db.StringProperty(required=True)

  def __str__(self):
    return "{'service_no':"+str(self.service_no)+ \
            ",'last_name':"+str(self.last_name)+ \
            ",'init':"+str(self.init)+ \
            "}"

class Sector(db.Model):
  date = db.DateProperty(required=True)
  from_loc = db.StringProperty(required=True)
  to_loc = db.StringProperty(required=True)
  service = db.StringProperty(required=True)
  booking = db.ReferenceProperty(Booking, required=True, collection_name='sectors')

  def __str__(self):
    return "{'date':"+str(self.date)+ \
            ",'from_loc':"+str(self.from_loc)+ \
            ",'to_loc':"+str(self.to_loc)+ \
            ",'service':"+str(self.service)+ \
            ",'booking':"+str(self.booking)+ \
            "}"

class Document(db.Model):
  date = db.DateProperty(required=True)
  blob_key = blobstore.BlobReferenceProperty(required=True)
  booking = db.ReferenceProperty(Booking, required=True, collection_name='documents')
  desc = db.TextProperty()

  def __str__(self):
    return "{'date':"+str(self.date)+ \
            ",'blob_key':"+str(self.blob_key)+ \
            ",'booking':"+str(self.booking)+ \
            ",'desc':"+str(self.desc)+ \
            "}"

class PassengerSectorBooking(db.Model):
  passenger = db.ReferenceProperty(Passenger, required=True, collection_name='bookings_rel')
  sector = db.ReferenceProperty(Sector, required=True, collection_name='passengers_rel')

  # Derived
  booking = db.ReferenceProperty(Booking, required=True, collection_name='passengers_rel')
  fare_type = db.TextProperty()

class LastUse(db.Model):
  obj = db.ReferenceProperty(db.Model, required=True, collection_name='last_use')
  last_use = db.DateProperty(default=datetime.now(timezone('Australia/Sydney')).date())

# Constants, private functions
_active_period = timedelta(days=90)
_expiry_period = timedelta(days=731)

def _current_date():
  return datetime.now(timezone('Australia/Sydney')).date()

def _use(obj_key):
  key_str = str(obj_key)
  now = _current_date()
  u = LastUse.get_or_insert(key_str, obj=obj_key)
  if now > u.last_use:
    u.last_use = now
    u.put_async()

# get functions
def get_booking_by_id(booking_id):
  b = Booking.get_by_id(booking_id)
  if b:
    _use(b.key())
  return b

def get_sector_by_id(sector_id):
  return Sector.get_by_id(sector_id)

def get_passenger_by_sn(service_no):
  p = Passenger.get_by_key_name(service_no)
  return p

def get_document_by_id(doc_id):
  return Document.get_by_id(doc_id)

def get_bookings(active_only=True):
  res = {}
  now = _current_date()
  for cat in ['UNPAID', 'PAID', 'CREDIT', 'CANCELLED']:
    q = Booking.all()
    q.filter("state = ", cat)
    if active_only:
      q.filter("last_date <= ", now - _active_period)

    q.order('company')
    q.order('booking_ref')
    res[cat] = q

  return res

def get_bookings_by_booking_ref(booking_ref, company=None, active_only=False):
  q = Booking.all()
  q.filter('booking_ref = ', booking_ref)

  if company:
    q.filter('company = ', company)

  if active_only:
    q.filter("last_date <= ", datetime.now(timezone('Australia/Sydney')).date() - _active_period)

  return q

def get_passengers_by_name(last_name, init=None):
  q = Passenger.all()
  q.filter('last_name', last_name)

  if init:
    q.filter('init', init)

  q.order('init')

  return q

def get_sectors_by_passenger_sn(service_no):
  p = Passenger.get_by_key_name(service_no)

  psb = PassengerSectorBooking.all()
  psb.filter('passenger = ', p)

  res = []
  for r in psb:
    res.append(r.sector)

  return res

def get_bookings_by_passenger_sn(service_no, course=None, active_only=False):
  p = Passenger.get_by_key_name(service_no)

  q = PassengerSectorBooking.all()
  q.filter('passenger = ', p)

  seen = []
  res = []
  for r in q:
    b = r.booking
    if (course is None or b.course == course) and (not active_only or b.latest_date < (_current_date() - _active_period)) and str(b.key()) not in seen:
      res.append(b)
      seen.append(str(b.key()))

  return res

# add functions

def add_booking(company, booking_ref, course):
  res = Booking(company=company, booking_ref=booking_ref, course=course)
  res.put()
  _use(res.key())
  return res

def add_document(booking_id, date, blob_info):
  res = None
  b = db.Key.from_path('Booking', booking_id)

  if b:
    res = Document(date=date, blob_key=blob_info.key(), booking=b)
    res.put()
    _use(b.key())

  return res

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

  return res

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

  return p

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
    _use(psb.passenger.pey())

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

def remove_pax_from_booking(booking_id, service_no):
  b = db.Key.from_path('Booking', booking_id)
  p = db.Key.from_path('Passenger', service_no)
  psb = PassengerSectorBooking.all(keys_only=True)
  psb.filter('booking = ', b)
  psb.filter('passenger = ', p)
  db.delete(psb)

## TODO
def delete_stale_records():
  stale = LastUse.all()
  for s in stale:
    db.delete(s.obj)
  db.delete(stale.filter('last_use < ', _current_date() - _expiry_period))
