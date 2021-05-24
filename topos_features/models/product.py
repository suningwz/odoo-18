from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    plan_type = fields.Selection(
        selection=[
            ('plan', 'Plan'),
            ('recharge', 'Recharge'),
            ('promo', 'PROMO'),
            ('sim', 'SIM CARD'),
            ('number', 'Phone Number'),
            ('equipment', 'Equipment'),
            ('other', 'Other'),
        ],
        string="Plan type",
        required=True,
        tracking=True,
        default='other',
    )
    sim_type = fields.Selection(
        selection=[
            ('mov', 'MOV'),
            ('mifi', 'MIFI'),
            ('hbb', 'HBB'),
            ('all', 'ALL'),
        ],
        string="Sim type",
        required=True,
        tracking=True,
        default='mov',
    )
    mb_data = fields.Integer(string="MB Data", )
    data_rs = fields.Integer(string="RS", )
    voice_minutes = fields.Integer(string="Voice Minutes", )
    sms = fields.Integer(string="SMS", )
    data_plan_duration = fields.Selection(
        selection=[
            ('3', '3 Days'),
            ('7', '7 Days'),
            ('15', '15 Days'),
            ('30', '30 Days'),
        ],
        string="Duration",
        tracking=True,
    )
    speed = fields.Selection(
        selection=[
            ('be', 'BE'),
            ('512_kbps', '512 Kbps'),
            ('1_mbps', '1 Mbps'),
            ('5_mbps', '5 Mbps'),
            ('10_mbps', '10 Mbps'),
            ('20_mbps', '20 Mbps'),
        ],
        string="Speed",
        tracking=True,
    )
    voicemail = fields.Selection(
        selection=[
            ('on_demand', 'On demand'),
            ('yes', 'Yes'),
            ('no', 'No'),
        ],
        string="Voicemail",
        tracking=True,
    )
    voip_app = fields.Selection(
        selection=[
            ('on_demand', 'On demand'),
            ('yes', 'Yes'),
            ('no', 'No'),
        ],
        string="VoIP App",
        tracking=True,
    )
    call_waiting = fields.Boolean(string="Call waiting", )
    call_forwarding = fields.Boolean(string="Call forwarding", )
    offer_ids = fields.One2many(
        comodel_name='product.offer',
        inverse_name='product_id',
        string='Offers',
    )
    nip_code = fields.Integer(
        string="NIP",
        readonly=True,
        store=True,
        default=0,
    )
    operator_id = fields.Many2one(
        comodel_name='mobile.network.operator',
        string='Operator',
        domain="['|', ('company_id', '=', False), "
               "('company_id', '=', company_id)]",
        readonly=True,
        store=True,
    )
    msisdn_ported = fields.Char(
        string="MSISDN ported",
        readonly=True,
        store=True,
    )
    actual_data_plan = fields.Char(string="Last data plan", )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Owner",
        readonly=True,
        store=True,
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    _sql_constraints = [
        ('default_code_uniq', 'unique(default_code)',
            'Internal Reference must be unique across the database!'), ]


class ProductOffer(models.Model):
    _name = 'product.offer'
    _description = 'Product Offer'
    _order = 'name asc'

    line_total = fields.Integer(string="Lines", required=True, default=1, )
    name = fields.Char('Offer name', required=True, )
    code = fields.Char('Offer ID', required=True, )
    code_type = fields.Selection(
        selection=[('activate', 'Activate'), ('purchase', 'Purchase')],
        string='Code type',
        required=True,
        default='activate', )
    product_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        required=True,)
    required_date = fields.Boolean('Dates required?', )

    @api.onchange('name')
    def _onchange_name(self):
        if self.name and self.name.find('FIFF') > 1:
            self.required_date = True
