import logging
from odoo import models, fields, api, _


_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def post(self):
        super(AccountPayment, self).post()
        for rec in self:
            if rec.state == 'posted' and rec.payment_transaction_id \
                    and rec.payment_type == 'inbound':
                if rec.payment_transaction_id.invoice_ids:
                    invoice = rec.payment_transaction_id.invoice_ids.filtered(
                        lambda m: m.invoice_payment_state == 'paid')
                    if invoice:
                        sim_plan = ['plan', 'recharge']
                        for line in invoice.line_ids:
                            if line.product_id.plan_type in sim_plan:
                                rec.msisdn_purchase(invoice)
        return True

    def msisdn_purchase(self, invoice_id):
        start_date = invoice_id.effective_date.strftime('%Y%m%d')
        end_date = invoice_id.expire_date.strftime('%Y%m%d')

        first_time = False
        offer_products = [line.product_id for line in
                          invoice_id.invoice_line_ids
                          if line.product_id.type == 'service']
        data = {
            'msisdn': self.partner_id.phone,
            'effective_date': start_date,
            'expire_date': end_date,
            'offer': offer_products,
        }
        _logger.info("Datos a enviar: %r" % data)
        if invoice_id.partner_id.phone:
            sim_card = [self.partner_id.phone]
            invoice_id.action_assign_offer(
                sim_card, offer_products, start_date, end_date, first_time)
        return True
