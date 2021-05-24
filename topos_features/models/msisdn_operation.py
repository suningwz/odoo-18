import json
from . import api as ws

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, Warning, UserError


class MsisdnOperation(models.Model):
    _name = 'msisdn.operation'
    _description = 'MSISDN Net Operations'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name, id desc'

    READONLY_STATES = {
        'draft': [('readonly', False)],
        'confirm': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    name = fields.Char(
        string="Reference",
        readonly=True,
        store=True,
        default='/',
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    sim_card_ids = fields.Many2many(
        comodel_name="stock.production.lot",
        string='SIM CARDS',
        auto_join=True,
        states=READONLY_STATES,
    )
    state = fields.Selection(
        string="State",
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ],
        readonly=True,
        default="draft",
    )
    operation_type = fields.Selection(
        string="Operation type",
        selection=[
            ('msisdn', 'MSISDN'),
            ('portability', 'Portability'),
            ('imei', 'IMEI'),
        ],
        default="msisdn",
        states=READONLY_STATES,
    )
    is_msisdn_operation = fields.Boolean()
    msisdn_operation = fields.Selection(
        string="Operation",
        selection=[
            ('profile', 'Profile'),
            ('resume', 'Resume'),
            ('reactivate', 'Reactivate'),
            ('suspend', 'Suspend'),
            ('barring', 'Barring'),
            ('unbarring', 'Unbarring'),
            ('deactivate', 'Deactivate'),
            ('predeactivate', 'Predeactivate'),
        ],
        default="profile",
        states=READONLY_STATES,
    )
    portability_operation = fields.Selection(
        string="Operation",
        selection=[
            ('portability_import', 'Import'),
            ('portability_reverse_import', 'Reverse Import'),
            ('portability_export', 'Export'),
            ('portability_reverse_export', 'Reverse Export'),
            ('portability_expired_export', 'Expire Export'),
        ],
        default="portability_import",
        states=READONLY_STATES,
    )
    imei_operation = fields.Selection(
        string="IMEI operation",
        selection=[
            ('imei_lock', 'IMEI Lock'),
            ('imei_unlock', 'IMEI Unlock'),
            ('imei_status', 'IMEI Status'),
        ],
        default="imei_status",
        states=READONLY_STATES,
    )
    reason = fields.Selection(
        string="Reason",
        selection=[
            ('0', 'Reanudación normal'),
            ('1', 'Reanudación por notificación de cliente'),
        ],
        states=READONLY_STATES,
    )
    suspend_reason = fields.Selection(
        string="Reason",
        selection=[
            ('0', 'Suspensión normal'),
            ('1', 'Suspensión por notificación de cliente'),
        ],
        states=READONLY_STATES,
    )
    date = fields.Date(
        string='Date',
        readonly=True,
        store=True,
        default=fields.Date.today,
    )
    schedule_date = fields.Date(
        string='Schedule Date',
        required=False,
        default=fields.Date.today,
        states=READONLY_STATES,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Seller',
        required=True,
        default=lambda self: self.env.user,
        states=READONLY_STATES,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.user.company_id,
        states=READONLY_STATES,
    )
    api_executed = fields.Boolean()
    altan_order_id = fields.Char(string="Order ID", readonly=True, store=True, )
    response = fields.Text(string="Response", readonly=True, store=True, )
    network_type = fields.Selection(
        string="Network type",
        selection=[
            ('mobile', 'Mobile'),
            ('fixed', 'Fixed'),
        ],
        default='mobile',
        states=READONLY_STATES,
    )
    msisdn_transitory = fields.Many2one(
        comodel_name='stock.production.lot',
        string='MSISDN Transitory',
        domain="['|', ('company_id', '=', False), "
               "('plan_type', '=', 'sim'), "
               "('company_id', '=', company_id)]",
        states=READONLY_STATES,
    )
    imsi = fields.Char(
        related="msisdn_transitory.imsi_home",
        string="IMSI",
        readonly=True,
        store=True,
    )
    msisdn_ported = fields.Char(string="Last MSISDN", states=READONLY_STATES, )
    operator_id = fields.Many2one(
        comodel_name='mobile.network.operator',
        string='Operator',
        states=READONLY_STATES,
    )
    approved_date = fields.Date(
        string='Approved Date',
        required=False,
        default=fields.Date.today,
        states=READONLY_STATES,
    )
    nip_code = fields.Char(string="NIP", size=4, states=READONLY_STATES, )
    last_data_plan = fields.Char(
        string="Last Data Plan",
        states=READONLY_STATES,
    )
    contact_number = fields.Char(
        string="Contact alternative number",
        states=READONLY_STATES,
    )

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            return {
                'domain': {
                    'sim_card_ids': [
                        ('partner_id', '=', self.partner_id.id),
                        ('company_id', '=', self.env.user.company_id.id),
                    ]
                }
            }

    @api.onchange('operation_type')
    def onchange_operation_type(self):
        if self.operation_type:
            if self.operation_type in ['portability', 'imei']:
                self.msisdn_operation = 'profile'
                self.is_msisdn_operation = False
            else:
                self.is_msisdn_operation = True

    def execute_api_method(self):
        if len(self.sim_card_ids) > 1:
            raise ValidationError("Para esta operación solo puede seleccionar "
                                  "un SIM CARD")

        result = False
        msisdn = self.sim_card_ids.ref
        schedule_date = self.schedule_date.strftime('%Y%m%d')
        resume_reason = int(self.reason)
        suspend_reason = int(self.suspend_reason)

        if self.operation_type == 'msisdn':
            if self.msisdn_operation == 'profile':
                result = self.profile(msisdn)
            elif self.msisdn_operation == 'resume':
                result = self.resume(msisdn, resume_reason, schedule_date)
            elif self.msisdn_operation == 'suspend':
                result = self.suspend(msisdn, suspend_reason, schedule_date)
            elif self.msisdn_operation == 'reactivate':
                result = self.reactivate(msisdn, schedule_date)
            elif self.msisdn_operation == 'deactivate':
                group_name = 'topos_features.telephony_group_manager'
                is_in_group = self.env.user.has_group(group_name)
                if is_in_group:
                    result = self.deactivate(msisdn, schedule_date)
                else:
                    raise ValidationError(
                        "Esta operación solo puede ser ejecutado por un "
                        "Administrador")
            elif self.msisdn_operation == 'predeactivate':
                result = self.predeactivate(msisdn, schedule_date)
            elif self.msisdn_operation == 'barring':
                result = self.barring(msisdn)
            elif self.msisdn_operation == 'unbarring':
                result = self.unbarring(msisdn)
        elif self.operation_type == 'portability':
            # ConfigParameter = self.env['ir.config_parameter'].sudo()
            # rida = ConfigParameter.get_param('abd.rida')
            # rcr = ConfigParameter.get_param('abd.rcr')
            # approved_date = self.approved_date.strftime('%Y%m%d')
            # dida = self.operator_id.dida_code
            # if not self.operator_id.parent_id:
            #     dcr = self.operator_id.dcr_code
            # else:
            #     dcr = self.operator_id.parent_id.dcr_code

            if self.portability_operation == 'portability_import':
                result = self.import_msisdn(self.msisdn_transitory.ref,
                    self.msisdn_ported)
            if self.portability_operation == 'portability_reverse_import':
                result = self.reverse_import(self.msisdn_ported, self.imsi,
                    approved_date, dida, rida, dcr, rcr)
        else:
            pass

        if result:
            self.action_done()

    def profile(self, msisdn):
        response = ws.msisdn_profile(msisdn)
        self.write({
            'response': "<p><code> %s </code></p>" % response,
        })
        return True

    def resume(self, msisdn, reason, schedule_date):
        response = ws.msisdn_resume(msisdn, reason, schedule_date)
        if not response.get('errorCode'):
            self.write({
                'altan_order_id': response.json().get('order')['id'],
                'response': "<p><code> %s </code></p>" % response,
            })
        else:
            raise ValidationError("Error\n\n%s" % response)
        return True

    def suspend(self, msisdn, reason, schedule_date):
        response = ws.msisdn_suspend(msisdn, reason, schedule_date)
        if not response.get('errorCode'):
            self.write({
                'altan_order_id': response.json().get('order')['id'],
                'response': "<p><code> %s </code></p>" % response,
            })
        else:
            raise ValidationError("Error\n\n%s" % response)
        return True

    def reactivate(self, msisdn, schedule_date):
        response = ws.msisdn_reactivate(msisdn, schedule_date)
        if not response.get('errorCode'):
            self.write({
                'altan_order_id': response.get('order')['id'],
                'response': "<p><code> %s </code></p>" % response,
            })
        else:
            raise ValidationError("Error\n\n%s" % response)
        return True

    def deactivate(self, msisdn, schedule_date):
        response = ws.msisdn_deactivate(msisdn, schedule_date)
        if not response.get('errorCode'):
            self.write({
                'altan_order_id': response.get('order')['id'],
                'response': "<p><code> %s </code></p>" % response,
            })
        else:
            raise ValidationError("Error\n\n%s" % response)
        return True

    def predeactivate(self, msisdn, schedule_date):
        response = ws.msisdn_predeactivate(msisdn, schedule_date)
        if not response.get('errorCode'):
            self.write({
                'altan_order_id': response.get('order')['id'],
                'response': "<p><code> %s </code></p>" % response,
            })
        else:
            raise ValidationError("Error\n\n%s" % response)
        return True

    def barring(self, msisdn):
        response = ws.msisdn_barring(msisdn)
        if not response.get('errorCode'):
            self.write({
                'altan_order_id': response.get('order')['id'],
                'response': "<p><code> %s </code></p>" % response,
            })
        else:
            raise ValidationError("Error\n\n%s" % response)
        return True

    def unbarring(self, msisdn):
        response = ws.msisdn_unbarring(msisdn)
        if not response.get('errorCode'):
            self.write({
                'altan_order_id': response.get('order')['id'],
                'response': "<p><code> %s </code></p>" % response,
            })
        else:
            raise ValidationError("Error\n\n%s" % response)
        return True

    def import_msisdn(self, msisdn_transitory, msisdn_ported):
        response = ws.portability_import(msisdn_transitory, msisdn_ported)
        if not response.get('errorCode'):
            self.write({
                # 'altan_order_id': response.get('order')['id'],
                'response': "<p><code> %s </code></p>" % response,
            })
        else:
            raise ValidationError("Error\n\n%s" % response)
        return True

    def reverse_import(self, msisdn_ported, imsi,
            approved_date, dida, rida, dcr, rcr):
        response = ws.portability_import(msisdn_ported, imsi,
            approved_date, dida, rida, dcr, rcr)
        if not response.get('errorCode'):
            self.write({
                # 'altan_order_id': response.get('order')['id'],
                'response': "<p><code> %s </code></p>" % response,
            })
        else:
            raise ValidationError("Error\n\n%s" % response)
        return True

    def check_order_status(self):
        if not self.altan_order_id:
            raise ValidationError("Esta operación no tiene un número de orden.")
        else:
            response = ws.msisdn_order_status(self.altan_order_id)
            msg = """
            <p><b>Estado:</b> %s</p>
            <p><b>Tipo:</b> %s</p>
            """
            message = _(msg % (response.get('status'), response.get('type')))
            return self.message_post(body=message)

    def cancel_order(self):
        if not self.altan_order_id:
            raise ValidationError("Esta operación no tiene un número de orden.")
        else:
            msisdn = self.sim_card_ids.ref
            response = ws.cancel_order(msisdn, self.altan_order_id)
            msg = """
            <p><b>Estado:</b> %s</p>
            <p><b>Tipo:</b> %s</p>
            """
            message = _(msg % (response.get('status'), response.get('type')))
            self.write({'response': "<p><code> %s </code></p>" % response})
            return self.message_post(body=message)

    def button_confirm(self):
        values = {'state': 'confirm'}
        if self.name == '/':
            values['name'] = self.env['ir.sequence'].next_by_code(
                'sim.card.sequence')
        self.write(values)
        # if self.operation_type == 'portability':
        #     self.product_id.write({'nip_code': int(self.nip_code)})

    def button_set_to_draft(self):
        # if self.operation_type == 'portability':
        #     self.product_id.write({'nip_code': 0})
        self.write({'state': 'draft', 'api_executed': False})

    def action_done(self):
        self.write({'state': 'done', 'api_executed': True})

    @api.constrains('nip_code')
    def _check_nip_code_lenght(self):
        if self.operation_type == 'portability' and not self.nip_code.isdigit():
            raise ValidationError(_(
                "NIP Code only accept number (0-9), max 4 digits."))
        return True


class MobileNetworkOperator(models.Model):
    _name = 'mobile.network.operator'
    _description = 'Mobile network operator'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char('Name', required=True, )
    dcr_code = fields.Char('DCR Code', required=True, )
    dida_code = fields.Char('Dida Code', required=True, )
    type = fields.Selection(
        selection=[
            ('mno', 'Mobile Network Operator (MNO)'),
            ('mvno', 'Mobile Virtual Network Operator  (MVNO)'),
        ],
        string='Type',
        required=True,
    )
    parent_id = fields.Many2one(
        comodel_name='mobile.network.operator',
        string="Parent",
        ondelete='cascade',
        domain="['|', ('company_id', '=', False), "
               "('company_id', '=', company_id)]")
    parent_path = fields.Char(index=True)
    children_ids = fields.One2many(
        comodel_name='mobile.network.operator',
        inverse_name='parent_id',
        string="Childrens",
    )
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        store=True,
    )
    child_count = fields.Integer(
        '# MVNOs', compute='_compute_mvno_count',
        help="The number of mvno under this operator",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for operator in self:
            if operator.parent_id:
                operator.complete_name = '%s / %s' % (
                operator.parent_id.complete_name, operator.name)
            else:
                operator.complete_name = operator.name

    def _compute_mvno_count(self):
        for operator in self:
            child_count = self.search_count([
                ('type', '=', 'mvno'),
                ('parent_id', '=', operator.id),
            ])
            operator.child_count = child_count
