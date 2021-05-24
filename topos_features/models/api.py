# Author: Yasmany Castillo <yasmany003@gmail.com>
# This file contains all methods needed to interact with ALTAN services.
from datetime import date
import requests
from requests.auth import HTTPBasicAuth

API_URL = "http://10.1.10.7:8080/camel_demo/api/"
GEO_URL = "https://10.1.10.16:7342/turboApi/getCoordinates"
GEO_USER = "odoo_user01"
GEO_PASS = "0D00$$01@2020!"
# --------------------------------------------
#             MSISDN API Methods
# --------------------------------------------


def msisdn_suspend(msisdn, reason, schedule_date):
    """Suspensión de trafico saliente y entrante de UF."""
    endpoint = API_URL + 'subscribers/%s/suspend' % msisdn
    payload = {
        'reason': reason,
        'scheduleDate': schedule_date,
    }
    return requests.post(endpoint, json=payload).json()


def msisdn_profile(msisdn):
    """Consulta de perfil de UF"""
    endpoint = API_URL + 'subscribers/%s/profile' % msisdn
    response = requests.get(endpoint)
    return response.json()


def msisdn_purchase(msisdn, offerings, effective_date=False, expire_date=False,
                    schedule_date=False):
    """Compra de Producto."""
    endpoint = API_URL + 'products/purchase'
    payload = {
        'msisdn': msisdn,
        'offerings': offerings,
        'startEffectiveDate': effective_date or "",
        'expireEffectiveDate': expire_date or "",
        'scheduleDate': schedule_date or "",
    }
    response = requests.post(endpoint, json=payload)
    return response.json()


def msisdn_resume(msisdn, reason, schedule_date=False):
    """Reanudación de trafico saliente y entrante de UF."""
    endpoint = API_URL + 'subscribers/%s/resume' % msisdn
    payload = {
        'reason': reason,
        'schedule_date': schedule_date or "",
    }

    response = requests.post(endpoint, json=payload)
    return response.json()


def msisdn_reactivate(msisdn, schedule_date=False):
    """Reactivación de UF."""
    endpoint = API_URL + 'subscribers/%s/reactivate' % msisdn
    payload = {'schedule_date': schedule_date or ""}
    response = requests.post(endpoint, json=payload)
    return response.json()


def msisdn_activate(msisdn, offerings, effective_date=False, expire_date=False,
                    schedule_date=False):
    """Activación de UF.
    El address solo es requerido para HBB.
    """
    endpoint = API_URL + 'subscribers/%s/activate' % msisdn
    payload = {
        'offeringId': offerings,
        'address': "19.3959336,-99.176576",
        'startEffectiveDate': effective_date or "",
        'expireEffectiveDate': expire_date or "",
        'scheduleDate': schedule_date or "",
    }
    response = requests.post(endpoint, json=payload)
    return response.json()


def msisdn_activate_batch(values):
    """Activación de UF mediante Batch.
    msisdn|offeringId|Coordenadas|scheduleDate
    @:param values: must a tuple list like this:
    [('5586410013', '7800869','',''),...]
    """
    data = ""
    for item in values:
        data += "%s|%s|%s|%s\n" % (item[0], item[1], item[2], item[3])

    file_path = '/tmp/activation_batch_%s.txt' % date.today()
    with open(file_path, 'w', encoding="utf-8", newline='\r\n') as txt:
        txt.write(str(data))

    endpoint = API_URL + 'subscribers/activations'
    response = requests.post(endpoint, files={'file': open(file_path, 'rb')})
    return response.json()


def msisdn_deactivate(msisdn, schedule_date=False):
    """Desactivación de UF."""
    endpoint = API_URL + 'subscribers/%s/deactivate' % msisdn
    payload = {'schedule_date': schedule_date or ""}
    response = requests.post(endpoint, json=payload)
    return response.json()


def msisdn_predeactivate(msisdn, schedule_date=False):
    """Pre-desactivación de UF."""
    endpoint = API_URL + 'subscribers/%s/predeactivate' % msisdn
    payload = {'schedule_date': schedule_date or ""}
    response = requests.post(endpoint, json=payload)
    return response.json()


def msisdn_barring(msisdn):
    """Suspensión de tráfico Saliente de UF."""

    endpoint = API_URL + 'subscribers/%s/barring' % msisdn
    response = requests.post(endpoint)
    return response.json()


def msisdn_unbarring(msisdn):
    """Reanudación de tráfico Saliente de UF."""
    endpoint = API_URL + 'subscribers/%s/unbarring' % msisdn
    response = requests.post(endpoint)
    return response.json()


def msisdn_order_status(order_id):
    """Consulta de Estado de Orden."""
    endpoint = API_URL + 'orders/%s' % order_id
    response = requests.get(endpoint)
    return response.json()


def cancel_order(msisdn, order_id):
    """Cancelación de Orden con fecha efectiva."""
    endpoint = API_URL + 'scheduledOrders/%s/cancel' % order_id
    payload = {'msisdn': MSISDN}
    print(endpoint, payload)
    response = requests.post(endpoint, json=payload)
    return response.json()


# --------------------------------------------
#             Portability API Methods
# --------------------------------------------
def portability_import(msisdn_transitory, msisdn_ported):
    """Reactivación de UF."""
    endpoint = API_URL + 'import'
    payload = {
        'msisdnTransitory': msisdn_transitory,
        'msisdnPorted': msisdn_ported,
        # 'imsi': imsi,
        # 'approvedDateABD': approved_date or "",
        # 'dida': dida,
        # 'rida': rida,
        # 'dcr': dcr,
        # 'rcr': rcr,
        'autoScriptReg': "Y",
    }

    response = requests.post(endpoint, json=payload)
    return response.json()


def portability_reverse_import(msisdn_ported, imsi, approved_date, dida, rida,
                               dcr, rcr):
    """Reactivación de UF."""
    endpoint = API_URL + 'reverseImport'
    payload = {
        'msisdnPorted': msisdn_ported,
        'imsi': imsi,
        'approvedDateABD': approved_date or "",
        'dida': dida,
        'rida': rida,
        'dcr': dcr,
        'rcr': rcr,
    }
    response = requests.post(endpoint, json=payload)
    return response.json()


def portability_export(msisdn_ported, new_iccid, approved_date, dida, rida,
                       dcr, rcr):
    """Activación de UF."""
    endpoint = API_URL + 'export'
    payload = {
        'msisdnPorted': msisdn_ported,
        'newIccid': new_iccid,
        'approvedDateABD': approved_date or "",
        'dida': dida,
        'rida': rida,
        'dcr': dcr,
        'rcr': rcr,
    }
    response = requests.post(endpoint, json=payload)
    return response.json()


def portability_reverse_export(msisdn_ported, new_iccid, approved_date, dida,
                               rida, dcr, rcr):
    """Reactivación de UF."""
    endpoint = API_URL + 'reverseExport'
    payload = {
        'msisdnPorted': msisdn_ported,
        'newIccid': new_iccid,
        'approvedDateABD': approved_date or "",
        'dida': dida,
        'rida': rida,
        'dcr': dcr,
        'rcr': rcr,
    }
    response = requests.post(endpoint, json=payload)
    return response.json()


def portability_expired_export(msisdn_ported):
    """Reactivación de UF."""
    endpoint = API_URL + 'expiredExport'
    payload = {'msisdnPorted': msisdn_ported}
    response = requests.post(endpoint, json=payload)
    return response.json()


# --------------------------------------------
#             IMEI API Methods
# --------------------------------------------

def imei_lock(imei):
    """Bloqueo de IMEI."""
    endpoint = API_URL + '%s/lock' % imei
    response = requests.post(endpoint)
    return response.json()


def imei_unlock(imei):
    """Desbloqueo de IMEI."""
    endpoint = API_URL + '%s/unlock' % imei
    response = requests.post(endpoint)
    return response.json()


def imei_status(imei):
    """Consulta de estado de IMEI."""
    endpoint = API_URL + '%s/status' % imei
    response = requests.post(endpoint)
    return response.json()


# --------------------------------------------
#             HBB API Methods
# --------------------------------------------

def hbb_serviceability(address, zip):
    """Bloqueo de IMEI."""
    header = {'Content-type': 'application/json'}
    geo = requests.get(GEO_URL, auth=HTTPBasicAuth(GEO_USER, GEO_PASS), json={
        "address": address, "zipcode": zip or ""}, headers=header, verify=False)
    geo_result = geo.json()
    print("Direccion: %s" % address)
    print("API Sara: %r" % geo_result)
    if geo_result.get('code') == 1:
        coordinates = "%s,%s" % (geo_result.get('lat'), geo_result.get('lng'))
        endpoint = API_URL + 'network-services/serviceability?address=%s'
        response = requests.get(endpoint % coordinates).json()

        if response.get('result').find('broadband') >= 0:
            response.update({
                'code': geo_result.get('code'),
                'coordinates': coordinates,
            })
            return response
        else:
            response.update({'code': 0})
            return response

    return geo_result


def hbb_activate(msisdn, offerings, address, effective_date=False,
                 expire_date=False, schedule_date=False):
    """Bloqueo de IMEI."""
    endpoint = API_URL + 'subscribers/%s/activate' % msisdn
    payload = {
        'offeringId': offerings,
        'address': address,
        'startEffectiveDate': effective_date or "",
        'expireEffectiveDate': expire_date or "",
        'scheduleDate': schedule_date or "",
    }
    response = requests.post(endpoint, json=payload)
    return response.json()
