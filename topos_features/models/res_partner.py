from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    street_number = fields.Char(string='Número', )
    colony = fields.Char(string='Colonia', )
    street_ref = fields.Char(string='Referencia', )
    sim_card_ids = fields.One2many(
        comodel_name="stock.production.lot",
        inverse_name="partner_id",
        string='SIM CARDS',
        auto_join=True,
    )
