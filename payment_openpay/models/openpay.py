import logging
import openpay

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)


def create_missing_journal_for_openpay_acquirer(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['payment.acquirer']._create_missing_journal_for_openpay_acquirer()


class AcquirerOpenpay(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('openpay', 'Openpay'),
        ('paynet', 'Paynet'),
    ])
    openpay_merchant_id = fields.Char(
        string='Openpay Account ID',
        groups='base.group_user',
        help='The Merchant ID is used to ensure communications coming from '
             'Openpay are valid and secured.',
    )
    openpay_public_key = fields.Char(
        string='Public Key',
        required_if_provider='openpay',
        groups='base.group_user',
    )
    openpay_private_key = fields.Char(
        string='Private Key',
        required_if_provider='openpay',
        groups='base.group_user',
    )

    @api.model
    def _create_missing_journal_for_openpay_acquirer(self, company=None):
        '''Create the journal for conekta acquirers.
        We want one journal per acquirer. However, we can't create them during the 'create' of the payment.acquirer
        because every acquirers are defined on the 'payment' module but is active only when installing their own module
        (e.g. payment_paypal for Paypal). We can't do that in such modules because we have no guarantee the chart template
        is already installed.
        '''
        # Search for installed acquirers modules.
        # If this method is triggered by a post_init_hook, the module is 'to install'.
        # If the trigger comes from the chart template wizard, the modules are already installed.
        acquirer_names = ['conekta', 'conekta_oxxo']

        # Search for acquirers having no journal
        company = company or self.env.company
        acquirers = self.env['payment.acquirer'].search([
            ('provider', '=', 'openpay'),
            ('journal_id', '=', False),
            ('company_id', '=', company.id)
        ])

        journals = self.env['account.journal']
        for acquirer in acquirers.filtered(
                lambda l: not l.journal_id and l.company_id.chart_template_id):
            acquirer.journal_id = self.env['account.journal'].create(
                acquirer._prepare_account_journal_vals())
            journals += acquirer.journal_id
        return journals

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(AcquirerOpenpay, self)._get_feature_support()
        res['fees'].append('openpay')
        res['tokenize'].append('openpay')
        return res

    @api.model
    def _get_openpay_urls(self, environment):
        """ Openpay URLS """
        if environment == 'prod':
            return {'openpay_url': 'https://api.openpay.mx'}
        else:
            return {'openpay_url': 'https://sandbox-api.openpay.mx'}

    def paynet_get_form_action_url(self):
        return '/payment/paynet/feedback'

    def paynet_form_generate_values(self, tx_values):
        self.ensure_one()
        paynet_tx_values = dict(tx_values)
        paynet_tx_values.update({
            'phone': tx_values.get('partner_phone'),
            'openpay_merchant_id': self.openpay_merchant_id,
            'openpay_public_key': self.openpay_public_key,
            'openpay_private_key': self.openpay_private_key,
        })
        print(" DAta: %r" % paynet_tx_values)
        return paynet_tx_values

    def openpay_form_generate_values(self, values):
        self.ensure_one()
        tx_values = dict(values)
        temp_openpay_tx_values = dict({
            'company': self.company_id.name,
            'item_name': '%s: %s' % (self.company_id.name, values['reference']),
            'item_number': values['reference'],
            'amount': values['amount'],
            'currency_code': values['currency'] and values[
                'currency'].name or '',
            'currency_id': tx_values.get('currency') and tx_values.get(
                'currency').id or '',
            'openpay_merchant_id': self.openpay_merchant_id,
            'openpay_public_key': self.openpay_public_key,
            'openpay_private_key': self.openpay_private_key,
            'address1': values.get('partner_address'),
            'city': values.get('partner_city'),
            'country': values.get('partner_country') and values.get(
                'partner_country').code or '',
            'state': values.get('partner_state') and (values.get(
                'partner_state').code or values.get(
                'partner_state').name) or '',
            'email': values.get('partner_email'),
            'zip_code': values.get('partner_zip'),
            'name': tx_values['partner_name'],
            'phone': tx_values['partner_phone'],
        })
        temp_openpay_tx_values['returndata'] = tx_values.pop('return_url', '')
        tx_values.update(temp_openpay_tx_values)
        _logger.info("Valores formulario: %r" % tx_values)
        print("txt values: \n %s" % tx_values)
        return tx_values

    @api.model
    def openpay_s2s_form_process(self, data):
        print("Info: \n%r\n" % data)
        payment_token = self.env['payment.token'].sudo().create({
            'acquirer_id': int(data['acquirer_id']),
            'partner_id': int(data['partner_id']),
            'openpay_token': data.get('token_id'),
            'openpay_device_session_id': data.get('device_session_id'),
            'acquirer_ref': data.get('token_id'),
            'name': 'XXXXXXXXXXXX%s - %s' % (
            data['cc_number'][-4:], data['holdername']),
        })
        return payment_token

    def openpay_s2s_form_validate(self, data):
        self.ensure_one()
        # mandatory fields
        for field_name in ["cc_number", "holdername", "cc_expiry", "cardCVC"]:
            if not data.get(field_name):
                return False
        return True

    def openpay_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_openpay_urls(environment)['openpay_url']

    @api.model
    def _get_partner(self, id):
        return self.env['res.partner'].browse(id)

    @api.model
    def _get_openpey_keys(self):
        return [
            self.openpay_merchant_id,
            self.openpay_public_key,
            self.openpay_private_key,
        ]


class TransactionOpenpay(models.Model):
    _inherit = 'payment.transaction'

    openpay_reference = fields.Char("Openpay Payment Reference")
    openpay_txn_id = fields.Char('Transaction ID')
    openpay_txcurrency = fields.Char('Transaction Currency')
    openpay_payment_method = fields.Selection(
        selection=[
            ('store', 'Store'),
            ('card', 'Credit/Debit Card'),
        ],
        string="Payment method",
    )

    def get_transaction_report_url(self, suffix=None, report_type=None,
                                   download=None, query_string=None,
                                   anchor=None):
        """
            Get a portal url for this model, including access_token.
            The associated route must handle the flags for them to have any effect.
            - suffix: string to append to the url, before the query string
            - report_type: report_type query string, often one of: html, pdf, text
            - download: set the download query string to true
            - query_string: additional query string
            - anchor: string to append after the anchor #
        """
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        if base_url[-1] != '/':
            base_url += '/'

        url = base_url + 'print_payment_transaction/' + str(
            self.id) + '%s?%s%s%s%s' % (
                  suffix if suffix else '',
                  '&report_type=%s' % report_type if report_type else '',
                  '&download=true' if download else '',
                  query_string if query_string else '',
                  '#%s' % anchor if anchor else ''
              )
        return url

    def _get_report_base_filename(self):
        self.ensure_one()
        return self.reference

    @api.model
    def _paynet_form_get_tx_from_data(self, data):
        reference, amount, currency_name = data.get('reference'), data.get(
            'amount'), data.get('currency_name')
        tx = self.search([('reference', '=', reference)])

        if not tx or len(tx) > 1:
            error_msg = _('received data for reference %s') % (
                pprint.pformat(reference))
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return tx

    def _paynet_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        if float_compare(float(data.get('amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' %
                                       self.amount))
        if data.get('currency') != self.currency_id.name or data.get(
                'currency') not in ['MXN', 'USD']:
            invalid_parameters.append(('currency', data.get('currency'),
                                       self.currency_id.name))
        if 'phone' in data and len(data['phone']) < 10:
            invalid_parameters.append(('phone', data.get('phone'),
                                       self.partner_id.phone))
        return invalid_parameters

    def _paynet_form_validate(self, data):
        result = self._create_openpay_charge(
            acquirer_ref=self.payment_token_id.acquirer_ref,
            email=self.partner_email)
        return self._openpay_s2s_validate_tree(result)

    def _create_openpay_charge(self, acquirer_ref=None, token_id=None,
                                       email=None):
        partner = self.partner_id
        charge = False

        if not hasattr(self, 'sale_order_ids') and not hasattr(
                self, 'invoice_ids'):
            raise Warning("Can't create payment without Sale Order or Invoice.")
        if hasattr(self, 'sale_order_ids') and not self.sale_order_ids and \
                hasattr(self, 'invoice_ids') and not self.invoice_ids:
            raise Warning("Can't create payment without Sale Order or Invoice.")

        if not partner and self.sale_order_ids:
            partner = self.sale_order_ids[0].partner_id
        if not partner and self.invoice_ids:
            partner = self.invoice_ids[0].partner_id

        merchant_id = self.acquirer_id.openpay_merchant_id
        reference = self.reference
        payment_token = self.payment_token_id

        openpay.api_key = self.acquirer_id.openpay_private_key
        openpay.verify_ssl_certs = False
        openpay.merchant_id = merchant_id
        openpay.production = False
        if self.acquirer_id.state == 'enabled':
            openpay.production = True

        customer = {
            "name": partner.name,
            "last_name": "",
            "email": partner.email,
            "phone_number": partner.phone or partner.mobile,
        }
        try:
            if self.acquirer_id.provider == 'openpay':
                # Create the card
                token = payment_token.openpay_token
                device_session_id = payment_token.openpay_device_session_id

                charge = openpay.Charge.create_as_merchant(
                    source_id=token,
                    method="card",
                    amount=self.amount,
                    currency=self.currency_id.name,
                    description=self.reference,
                    device_session_id=device_session_id,
                    customer=customer,
                )

            if self.acquirer_id.provider == 'paynet':
                charge = openpay.Charge.create_as_merchant(
                    customer=customer,
                    method="store",
                    amount=self.amount,
                    description=reference,
                )
        except Exception as e:
            msg = "La transacción no pudo ser completada, por favor contacte " \
                  "a su banco"
            _logger.info(e.json_body.get('error_code'))
            self._set_transaction_error(msg)
            return False

        return charge

    def openpay_s2s_do_transaction(self, **kwargs):
        self.ensure_one()
        result = self._create_openpay_charge(
            acquirer_ref=self.payment_token_id.acquirer_ref,
            email=self.partner_email)
        return self._openpay_s2s_validate_tree(result)

    def _openpay_s2s_validate_tree(self, tree):
        self.ensure_one()
        if self.state not in ("draft", "pending"):
            _logger.info('Openpay: trying to validate an already validated tx '
                         '(ref %s)', self.reference)
            return True

        if type(tree) == dict and tree.get('error'):
            self._set_transaction_error(msg=tree.get('error'))
            return False
        print("Tree: %r" % tree)
        provider = self.acquirer_id.provider
        status = tree.get('status')
        payment_tokens = self.mapped('payment_token_id')
        if payment_tokens:
            payment_tokens.sudo().write({'active': False, })

        if provider == 'openpay' and status == 'completed':
            self.write({
                'date': fields.datetime.now(),
                'acquirer_reference': tree.id,
            })
            self._set_transaction_done()
            self.execute_callback()
            if self.payment_token_id:
                self.payment_token_id.verified = True
            return True
        elif provider == 'openpay' and status in ['charge_pending',
                                                  'in_progress']:
            self.write({
                'acquirer_reference': tree.id,
                'openpay_reference': tree.id,
            })
            self._set_transaction_pending()
            self.execute_callback()
            if self.payment_token_id:
                self.payment_token_id.verified = True
            return True
        elif provider == 'paynet' and status == 'in_progress':
            self.write({
                'acquirer_reference': tree.id,
                'openpay_reference': tree.payment_method.reference,
            })
            self._set_transaction_pending()
            self.execute_callback()
            return True
        else:
            self.sudo().write({
                'state_message': 'error',
                'acquirer_reference': tree.id,
                'date': fields.datetime.now(),
            })
            self._set_transaction_cancel()
            return False

    @api.model
    def _openpay_form_get_tx_from_data(self, data):
        _logger.info("******************** form data=%r", data)
        reference = data.get('reference')
        amount = data.get('amount')
        currency_name = data.get('currency_name')
        currency = data.get('currency')
        acquirer_reference = data.get('acquirer_reference')

        if not reference or not amount or not currency or not acquirer_reference:
            error_msg = 'Openpay: received data with missing reference (%s) ' \
                        'or acquirer_reference (%s) or Amount (%s)' % (
                reference, acquirer_reference, amount)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        tx = self.env['payment.transaction'].search([
            ('reference', '=', reference)])

        if not tx or len(tx) > 1:
            error_msg = 'Openpay: received data for reference %s' % (reference)
            if not tx:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return tx

    def _openpay_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        reference = data['metadata']['reference']
        if reference != self.reference:
            invalid_parameters.append(('Reference', reference, self.reference))
        return invalid_parameters

    def _openpay_form_validate(self, data):
        return self._openpay_s2s_validate_tree(data)

    def openpay_card_error(self, error_code):
        msg = "La transacción no pudo ser completada, por favor contacte a " \
              "su banco"
        message = {
            '3001': "La tarjeta fue rechazada.",
            '3002': "La tarjeta ha expirado.",
            '3003': "La tarjeta no tiene fondos suficientes.",
            '3004': msg,
            '3005': msg,
        }
        return message[str(error_code)]


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    openpay_token = fields.Char('Openpay token', help='Token from Openpay')
    openpay_device_session_id = fields.Char('Openpay Device Session ID', )


class Website(models.Model):
    _inherit = 'website'

    @api.model
    def get_openpay_payment_acquirere_id(self):
        acquirer_id = self.env['ir.model.data'].sudo().get_object_reference(
            'payment_openpay', 'payment_acquirer_openpay')[1]
        return acquirer_id if acquirer_id else 0


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def message_post_with_template(self, template_id, email_layout_xmlid=None,
                                   auto_commit=False, **kwargs):
        """ Helper method to send a mail with a template
            :param template_id : the id of the template to render to create the body of the message
            :param **kwargs : parameter to create a mail.compose.message woaerd (which inherit from mail.message)
        """
        # Get composition mode, or force it according to the number of record in self
        if not kwargs.get('composition_mode'):
            kwargs['composition_mode'] = 'comment' if len(
                self.ids) == 1 else 'mass_mail'
        if not kwargs.get('message_type'):
            kwargs['message_type'] = 'notification'
        res_id = kwargs.get('res_id', self.ids and self.ids[0] or 0)
        res_ids = kwargs.get('res_id') and [kwargs['res_id']] or self.ids

        # Create the composer
        composer = self.env['mail.compose.message'].with_context(
            active_id=res_id,
            active_ids=res_ids,
            active_model=kwargs.get('model', self._name),
            default_composition_mode=kwargs['composition_mode'],
            default_model=kwargs.get('model', self._name),
            default_res_id=res_id,
            default_template_id=template_id,
            custom_layout=email_layout_xmlid,
        ).create(kwargs)
        # Simulate the onchange (like trigger in form the view) only
        # when having a template in single-email mode
        if template_id:
            update_values = composer.onchange_template_id(template_id,
                kwargs['composition_mode'], self._name, res_id)['value']
            if self._name == 'sale.order':
                attachment = self.env['ir.attachment'].search([
                    ('res_id', '=', self.id),
                ])
                update_values['attachment_ids'] = [(6, 0, attachment.ids)]
            composer.write(update_values)
        return composer.send_mail(auto_commit=auto_commit)
