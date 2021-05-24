from datetime import date
from dateutil.relativedelta import relativedelta
import logging
import json
from . import api as ws
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    offer_effective_date = fields.Date(
        string='Effective Date',
        readonly=True,
        default=fields.Date.context_today,
        states={'draft': [('readonly', False)]},
    )
    offer_expire_date = fields.Date(
        string='Expire Date',
        readonly=True,
        store=True,
        compute="_compute_expire_date",
    )
    offer_schedule_date = fields.Date(
        string='Schedule Date',
        readonly=True,
        default=fields.Date.today,
        states={'draft': [('readonly', False)]},
    )

    @api.depends('order_line.product_id')
    def _compute_expire_date(self):
        for order in self:
            for line in self.order_line:
                product = line.product_id
                if product.plan_type in ['plan', 'recharge', 'equipment']:
                    if product.sim_type in ['mov', 'hbb'] and not \
                            product.data_plan_duration:
                        raise ValidationError(
                            "El producto: %s, no tiene una duración "
                            "definida." % product.name)
                    else:
                        duration = int(product.data_plan_duration)
                        expire_date = date.today() + relativedelta(
                            days=duration)
                        order.offer_expire_date = expire_date
                else:
                    order.offer_expire_date = False

    def action_confirm(self):
        # Check HBB serviceability if product is HBB
        is_hbb = False
        for line in self.order_line:
            product = line.product_id
            if product.plan_type == 'equipment' and product.sim_type == 'hbb':
                is_hbb = True

        if is_hbb:
            address = self.partner_id.street
            if self.partner_id.street2:
                address += " %s" % self.partner_id.street2
            if self.partner_id.colony:
                address += " %s" % self.partner_id.colony
            if self.partner_id.street_number:
                address += " %s" % self.partner_id.street_number
            if self.partner_id.city:
                address += ", %s" % self.partner_id.zip
            if self.partner_id.zip:
                address += ", %s" % self.partner_id.city
            if self.partner_id.state_id:
                address += " %s" % self.partner_id.state_id.name
            if self.partner_id.country_id:
                address += ", %s" % self.partner_id.country_id.name

            get_param = self.env['ir.config_parameter'].sudo().get_param
            geo_url = get_param('coordinates.url')
            geo_user = get_param('geo.user')
            geo_password = get_param('geo.password')

            response = ws.hbb_serviceability(
                geo_url, geo_user, geo_password, address, self.partner_id.zip)

            if response.get('code') == 0:
                raise ValidationError(
                    "Este servicio no cuenta con disponibilidad en la zona de "
                    "residencia del cliente.")
        return super(SaleOrder, self).action_confirm()

    def _prepare_invoice(self):
        self.ensure_one()
        invoice_values = super(SaleOrder, self)._prepare_invoice()
        invoice_values.update({
            'effective_date': self.offer_effective_date,
            'expire_date': self.offer_expire_date,
            'schedule_date': self.offer_schedule_date,
            'required_sims': False,
            'is_hbb': False,
        })

        for line in self.order_line:
            product = line.product_id
            if product.plan_type in ['plan', 'recharge']:
                invoice_values['required_sims'] = True
                pickings = self.picking_ids.filtered(
                    lambda p: p.state == 'done' and
                              p.picking_type_code == 'outgoing')
                for picking in pickings:
                    lot_ids = []
                    for line in picking.move_line_ids:
                        if line.product_id.plan_type == 'sim':
                            lot_ids.append(line.lot_id.ref)

                    if lot_ids:
                        invoice_values['sim_cards'] = ",".join(lot_ids)
            elif product.plan_type == 'equipment' and product.sim_type == 'hbb':
                invoice_values['is_hbb'] = True

        return invoice_values


class Website(models.Model):
    _inherit = 'website'

    def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
        sale_order = super(Website, self).sale_get_order(force_create, code, update_pricelist, force_pricelist)

        if sale_order:
            sale_order.write({'client_order_ref': sale_order.partner_id.phone})

        return sale_order
