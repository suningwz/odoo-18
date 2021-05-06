import json
import requests
import logging
from pprint import pprint as pp
from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request
import werkzeug


_logger = logging.getLogger(__name__)


class WebsiteSaleOpenpay(WebsiteSale):

    def checkout_form_validate(self, mode, all_form_values, data):
        error, error_message = super(
            WebsiteSaleOpenpay, self).checkout_form_validate(
            mode, all_form_values, data)
        if 'phone' not in error and all_form_values.get('phone'):
            phone = all_form_values.get('phone')
            if len(phone) < 10:
                error['phone'] = 'error'
                error_message.append('Please enter valid phone number. Length '
                                     'of phone number must be 10 digits')

        return error, error_message

    @http.route(['/shop/payment'], type='http', auth="public", website=True,
        sitemap=False)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        order = request.website.sale_get_order()
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        render_values = self._get_shop_payment_values(order, **post)
        render_values['only_services'] = order and order.only_services or False

        if render_values['errors']:
            render_values.pop('acquirers', '')
            render_values.pop('tokens', '')
        _logger.info("render values: %r" % render_values)
        return request.render("website_sale.payment", render_values)


class PortalConekta(CustomerPortal):

    @http.route(['/print_payment_transaction/<int:transaction_id>'],
        type='http', auth="public", website=True)
    def portal_payment_transaction_detail(self, transaction_id,
                                          report_type=None, download=False,
                                          **kw):
        document = request.env['payment.transaction'].sudo().browse(
            transaction_id)
        document_sudo = document.exists()
        if not document_sudo:
            return request.redirect('/my')
        return self._show_report(
            model=document_sudo,
            report_type=report_type,
            report_ref='payment_openpay.action_report_payment_transaction',
            download=download)


class OpenpayController(http.Controller):
    _accept_url = '/payment/transfer/feedback'

    @http.route([
        '/payment/paynet/feedback'], type='http', auth='none', csrf=False)
    def openpay_form_feedback(self, **post):
        _logger.info('Beginning form_feedback with post data %s', pp(post))
        request.env['payment.transaction'].sudo().form_feedback(post, 'paynet')
        return werkzeug.utils.redirect('/payment/process')

    @http.route(['/payment/openpay/create'], type='json', auth='public')
    def openpay_pay_create_charge(self, **post):
        _logger.info('post : ' + str(post))
        json_data = request.jsonrequest
        _logger.info("json_data :" + str(json_data))
        data = json_data.get('data')
        if json_data and json_data.get('type', '') == 'charge.completed' and \
                data:
            tx_obj = request.env['payment.transaction']
            order_id = data.get('object', {}).get('order_id')
            payment_reference = data.get('object', {}).get(
                'payment_method', {}).get('reference')
            tx = None
            if order_id:
                tx = tx_obj.sudo().search([
                    ('acquirer_reference', '=', order_id)], limit=1)
            if not tx and payment_reference:
                tx = tx_obj.sudo().search([
                    ('openpay_reference', '=', payment_reference)
                ], limit=1)
            if tx:
                if tx.state in ['pending', 'draft']:
                    tx._set_transaction_done()
                try:
                    tx._post_process_after_done()
                except Exception as e:
                    pass

        return "<Response></Response>"

    @http.route([
        '/payment/openpay/s2s/create_json'], type='json', auth='public')
    def openpay_s2s_create_json(self, **kwargs):
        acquirer_id = int(kwargs.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        return acquirer.s2s_process(kwargs).id

    @http.route(['/payment/openpay/s2s/create'], type='http', auth='public')
    def openpay_s2s_create(self, **post):
        acquirer_id = int(post.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        error = None
        try:
            acquirer.s2s_process(post)
        except Exception as e:
            error = e.message

        return_url = post.get('return_url', '/')
        if error:
            separator = '?' if werkzeug.urls.url_parse(
                return_url).query == '' else '&'
            return_url += '{}{}'.format(separator, werkzeug.urls.url_encode({
                'error': error
            }))

        return werkzeug.utils.redirect(return_url)

    @http.route(['/payment/openpay/s2s/create_json_3ds'], type='json',
        auth='public', csrf=False)
    def openpay_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        token = request.env['payment.acquirer'].browse(
            int(kwargs.get('acquirer_id'))).s2s_process(kwargs)

        if not token:
            return {'result': False}
        res = {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
            '3d_secure': False,
            'verified': False,
        }

        if verify_validity != False:
            token.validate()
            res['verified'] = token.verified

        return res

    @http.route('/payment/openpay/3dsecure', type='http', auth="public",
        website=True)
    def openpay_3dsecure(self, id):
        """ Openpay Payment Controller """
        if id:
            return werkzeug.utils.redirect('/payment/process')
        return werkzeug.utils.redirect('/shop/payment/validate')

    @http.route(
        ['/shop/print/paynet'], type='http', auth="public", website=True)
    def print_paynet_receipt(self, **kwargs):
        order_id = request.session.get('sale_last_order_id')
        if order_id:
            order = request.env['sale.order'].sudo().browse(order_id)
            tx = order.transaction_ids.filtered(lambda t: t.state == 'pending')
            if tx:
                merchant_id = tx.acquirer_id.openpay_merchant_id
                base_url = ""
                if tx.acquirer_id.state == 'enabled':
                    base_url = "https://dashboard.openpay.mx/paynet-pdf"
                elif tx.acquirer_id.state == 'test':
                    base_url = "https://sandbox-dashboard.openpay.mx/paynet-pdf"
                pdf_url = "%s/%s/%s" % (base_url, merchant_id,
                                        order.client_order_ref)
                response = requests.get(pdf_url)
                pdfhttpheaders = [('Content-Type', 'application/pdf'),
                                  ('Content-Length', u'%s' % len(
                                      response.content))]
                return request.make_response(
                    response.content, headers=pdfhttpheaders)
        else:
            return request.redirect('/shop')
