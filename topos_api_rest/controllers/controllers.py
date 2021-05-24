# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta
import logging
import json
from http import cookies
import requests
from odoo import SUPERUSER_ID, _
from odoo.http import Controller, request, Response, route

_logger = logging.getLogger(__name__)
DB_NAME = "topos"


class ToposRestApi(Controller):

    def login(self, auth):
        request.session.authenticate(DB_NAME, auth.get('user'), auth.get(
            'password'))
        return request

    @route('/api/authenticate/', type='json', auth='none', methods=["POST"],
        csrf=False)
    def authenticate(self, **params):
        headers = {'Content-type': 'application/json'}
        auth_url = request.httprequest.url_root + "web/session/authenticate/"
        data = {
            "params": {
                "login": params.get('user', False),
                "password": params.get('password', False),
                "db": DB_NAME,
            }
        }
        res = requests.post(
            auth_url,
            data=json.dumps(data),
            headers=headers,
        )
        result = {}
        response = res.json()
        if response.get('result', False):
            # If authenticate is successful we need to do it with request to get
            # a valid session
            request.session.authenticate(DB_NAME, params.get('user'),
                params.get('password'))
            user = request.env['res.users'].sudo().browse([response.get(
                'result')['uid']])

            # Prepare response info
            result.update({
                'id': response.get('result')['uid'],
                'company_id': response.get('result')['company_id'],
                'partner_id': user.partner_id.id,
                'auth': {
                    "login": params.get('user'),
                    "password": params.get('password'),
                    "session_token": request.session.session_token,
                }
            })
        else:
            result.update({
                'error': {'message': response.get('error')['data']['message']}
            })

        return json.dumps(result)

    @route('/api/balance/', type='json', auth='none', methods=["GET"],
        csrf=False)
    def balance(self, **params):
        request = self.login(params.get('credential'))
        partner = request.env['res.partner'].sudo().search([
            ('id', '=', params.get('partner_id'))])

        return json.dumps({'balance': str(partner.credit_limit)})

    @route('/api/create/order', type='json', auth='none', methods=["POST"],
        csrf=False)
    def create_order(self, **params):
        """
        Check order values and create a new sale order.
        params = {
            'partner_id': partner_id,
            'user_id': user_id,
            'date_order': "",
            'order_line': [
                {
                    'name': "Description",
                    'product_id': product_id,
                    'product_uom_qty': 1,
                    'order_id': order_id,
                    'product_uom': self.product_id.uom_id.id,
                    'price_unit': 150.00,
                    'discount': 0.0,
                },...
            ],
        }
        """
        request = self.login(params.get('auth'))
        if not params.get('create'):
            return json.dumps({'IdResult': ""})

        result = self._create_update_sale_order(request, create=True)

        return json.dumps(result)

    @route('/api/purchase', type='json', auth='none', methods=["POST"],
        csrf=False)
    def purchase(self, **params):
        """
        Check order values and create a new sale order.
        params = {
            'partner_id': partner_id,
            'user_id': user_id,
            'date_order': "",
            'order_line': [
                {
                    'name': "Description",
                    'product_id': product_id,
                    'product_uom_qty': 1,
                    'order_id': order_id,
                    'product_uom': self.product_id.uom_id.id,
                    'price_unit': 150.00,
                    'discount': 0.0,
                },...
            ],
        }
        -----------------------------------------------
        {
            "IdResult": "string",
            "username": "string",
            "password": "string",
            "sku_code": "string",
            "opaccount": "string
            "monto": "float",
        }

        opaccount= numero de celular
        sku_code = codigo de producto
        """
        request = self.login(params.get('auth'))
        result = {}
        data = self._create_update_sale_order(request, params=params)
        if data.get('IdResult'):
            order = request.env['sale.order'].search([('name', '=', data.get(
                'IdResult'))])
            order.with_context(send_email=True).action_confirm()
            order.message_post(
                subject=_("Recarga externa"),
                body=_(
                    "Esta order fue creada para el número: (%s), el total de la "
                    "orden es: %r") % (order.client_order_ref, order.amount_total)
            )
            order._create_invoices()
            invoice = self._post_invoice_and_payment(request, order)
            result.update({
                "DoTResult": {
                    "transaction_id": order.name,
                    "rcode": "0",
                    "rcode_description": "Exito",
                    "opaccount": invoice.ref,
                    "opauthorization": invoice.altan_order,
                }
            })
        return json.dumps(result)

    def _create_update_sale_order(self, request, create=False, params=False):
        """Create a new sales order or update a specific one."""
        result = {}
        company = request.env.user.company_id
        sale_order = request.env['sale.order'].with_context(
            force_company=company.id).with_user(SUPERUSER_ID)
        partner = request.env.user.partner_id
        if create:
            so_data = {
                'partner_id': partner.id,
                'validity_date': datetime.date.today(),
                'date_order': datetime.datetime.now(),
                'company_id': company.id,
            }
            order = sale_order.create([so_data])
            payment_term_xml_id = "account.account_payment_term_immediate"
            order.onchange_partner_id()
            order.write({'payment_term_id': request.env.ref(
                payment_term_xml_id).id})
            result["IdResult"] = order.name
        elif params:
            SaleOrderLineSudo = request.env['sale.order.line'].sudo()
            offer = request.env['product.offer'].sudo().search([
                ('code', '=', params.get('sku_code'))
            ])
            product_id = offer.product_id.product_variant_id
            order = sale_order.search([
                ('name', '=', params.get('IdResult'))])
            order.write({'client_order_ref': params.get('opaccount')})
            if not order:
                result.update({
                    "error_code": "7",
                    "description": "No Existe Transacción Asociada a "
                                   "TRequestID",
                })
            order_line_values = {
                'product_id': product_id.id,
                'product_uom_qty': 1,
                'order_id': order.id,
                'product_uom': product_id.uom_id.id,
                'price_unit': float(params.get('monto')),
                'discount': 0.0,
            }
            order_line = SaleOrderLineSudo.create([order_line_values])
            try:
                order_line._compute_tax_id()
            except ValidationError as e:
                _logger.debug("ValidationError occurs during tax compute. %s" %
                              e)
            result["IdResult"] = order.name
        return result

    def _post_invoice_and_payment(self, request, order):
        # Post the invoice.
        invoices = order.mapped('invoice_ids').filtered(
            lambda inv: inv.state == 'draft')
        invoices.post()
        invoices.msisdn_activate()
        result["altan_order"] = invoices.altan_order_id

        # Create & Post the payment.
        payment_vals = {
            'amount': order.amount_total,
            'payment_type': 'inbound',
            'currency_id': order.currency_id.id,
            'partner_id': order.partner_id.id,
            'partner_type': 'customer',
            'invoice_ids': [(6, 0, invoices.ids)],
            'journal_id': invoices.journal_id.id,
            'company_id': order.company_id.id,
            'payment_method_id': request.env.ref(
                'payment.account_payment_method_electronic_in').id,
            'communication': invoices.name,
        }
        payment = request.env['account.payment'].sudo().create(payment_vals)
        payment.with_context(force_company=order.company_id.id,
            company_id=order.company_id.id).post()

        return invoices
