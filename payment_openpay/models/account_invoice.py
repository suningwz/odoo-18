
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)

#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     effective_date = fields.Date(
#         string='Effective Date',
#         readonly=True,
#         default=fields.Date.today,
#         states={'draft': [('readonly', False)]},
#     )
#     expire_date = fields.Date(
#         string='Expire Date',
#         readonly=False,
#         store=True,
#         compute="_compute_expire_date",
#     )
#     schedule_date = fields.Date(
#         string='Schedule Date',
#         readonly=True,
#         default=fields.Date.today,
#         states={'draft': [('readonly', False)]},
#     )
#     altan_order_id = fields.Char(
#         string="ALTAN Order ID(s)",
#         readonly=True,
#         store=True,
#     )
#     order_status = fields.Selection(
#         string="Order Status",
#         selection=[
#             ('success', 'Successful'),
#             ('fail', 'Failed'),
#             ('cancel', 'Cancelled'),
#         ],
#         readonly=True,
#         store=True,
#     )
#     has_sim_card = fields.Boolean()
#     only_sim_card = fields.Boolean()
#     is_an_activation = fields.Boolean(string="Is an activation?", )
#     sim_card_ids = fields.Many2many(
#         comodel_name="stock.production.lot",
#         string='SIM CARDS',
#     )
#
#     @api.depends('line_ids.price_subtotal', 'line_ids.tax_base_amount',
#         'line_ids.tax_line_id', 'line_ids.product_id')
#     def _compute_expire_date(self):
#         for move in self:
#             expire_date = False
#             if move.is_invoice(include_receipts=True):
#                 for line in move.line_ids:
#                     product = line.product_id
#                     if not product.data_plan_duration and \
#                             product.plan_type in ['plan', 'recharge']:
#                         raise ValidationError("El producto: %s, no tiene una "
#                                               "duración definida." % product.name)
#                     elif product.plan_type in ['plan', 'recharge']:
#                         duration = int(product.data_plan_duration)
#                         expire_date = date.today() + relativedelta(
#                             days=duration)
#                 move.expire_date = expire_date
#
#     def post(self):
#         super(AccountMove, self).post()
#         for move in self:
#             if move.type != 'out_invoice':
#                 continue
#
#             to_write = {}
#             has_sim_card = move.invoice_line_ids.filtered(
#                 lambda l: l.product_id.plan_type == 'sim')
#
#             if len(move.invoice_line_ids) == 1 and has_sim_card:
#                 to_write['only_sim_card'] = True
#             else:
#                 sale_line_ids = move.invoice_line_ids.mapped('sale_line_ids')
#                 sale_id = sale_line_ids.mapped('order_id')
#                 if sale_id:
#                     pickings = sale_id.picking_ids.filtered(
#                         lambda p: p.state == 'done' and
#                                   p.picking_type_code == 'outgoing')
#                     for picking in pickings:
#                         lot_ids = []
#                         for line in picking.move_line_ids:
#                             if line.product_id.plan_type == 'sim':
#                                 lot_ids.append(line.lot_id.id)
#                         move.sim_card_ids = [(6, 0, lot_ids)]
#                         to_write['has_sim_card'] = True
#                 to_write['only_sim_card'] = False
#             move.write(to_write)
#
#     def msisdn_activate(self):
#         start_date = self.effective_date.strftime('%Y%m%d')
#         end_date = self.expire_date.strftime('%Y%m%d')
#         first_time = True if self.is_an_activation else False
#
#         sale_line_ids = self.invoice_line_ids.mapped('sale_line_ids')
#         sale_id = sale_line_ids.mapped('order_id')
#
#         if sale_id and self.has_sim_card:
#             pickings = sale_id.picking_ids.filtered(
#                 lambda p: p.state == 'done' and
#                           p.picking_type_code == 'outgoing')
#             for picking in pickings:
#                 lot_ids = []
#                 for line in picking.move_line_ids:
#                     if line.product_id.plan_type == 'sim':
#                         lot_ids.append(line.lot_id.id)
#                 self.sim_card_ids = [(6, 0, lot_ids)]
#         elif not self.has_sim_card and not self.sim_card_ids:
#             raise ValidationError("Necesita introducir los SIM CARD a los "
#                                   "cuales se aplicara estas ofertas.")
#
#         offer_products = [line.product_id for line in self.invoice_line_ids
#                           if line.product_id.type == 'service']
#         sim_cards = [lot.ref for lot in self.sim_card_ids]
#
#         self.action_assign_offer(sim_cards, offer_products, start_date,
#             end_date, first_time)
#
#     def action_assign_offer(self, sim_cards, offer_products, start_date,
#                                          end_date, first_time):
#         altan_order_list = []
#         response, api_error = False, False
#
#         if len(sim_cards) > 1:
#             batch_values = []
#             # msisdn|offeringId|Coordenadas|scheduleDate
#             for msisdn in sim_cards:
#                 for product in offer_products:
#                     if self.is_an_activation:
#                         offer_line = product.offer_ids.filtered(
#                             lambda po: po.code_type == 'activate')
#                     else:
#                         offer_line = product.offer_ids.filtered(
#                             lambda po: po.code_type == 'purchase')
#                     batch_values.append((msisdn, offer_line.code, "", ""))
#             response = ws.msisdn_activate_batch(batch_values)
#             _logger.info(response)
#             if response.get('transaction'):
#                 altan_order_list.append(response.get('transaction')['id'])
#             else:
#                 api_error = True
#
#         for product in offer_products:
#             msisdn = sim_cards[0]
#             activate_line = product.offer_ids.filtered(
#                 lambda po: po.code_type == 'activate')
#
#             purchase_line = product.offer_ids.filtered(
#                 lambda po: po.code_type == 'purchase')
#
#             if first_time and activate_line:
#                 if not activate_line.required_date:
#                     response = ws.msisdn_activate(msisdn, activate_line.code)
#                 else:
#                     response = ws.msisdn_activate(
#                         msisdn,
#                         activate_line.code,
#                         start_date,
#                         end_date)
#                 _logger.info(response)
#                 if response.get('order'):
#                     altan_order_list.append(response.get('order')['id'])
#                 else:
#                     api_error = True
#             elif purchase_line and not first_time:
#                 if not purchase_line.required_date:
#                     response = ws.msisdn_purchase(msisdn, [purchase_line.code])
#                 else:
#                     response = ws.msisdn_purchase(msisdn, [purchase_line.code],
#                         start_date, end_date)
#                 _logger.info(response)
#                 if response.get('order'):
#                     altan_order_list.append(response.get('order')['id'])
#                 else:
#                     api_error = True
#
#             if api_error:
#                 raise ValidationError(
#                     "Hemos tenido un inconveniente con el servicio.\n\n"
#                     "Error: \n%r." % response)
#
#             order_ids = ",".join(altan_order_list)
#         self.write({
#             'order_status': 'success' if len(altan_order_list) >= 1 else 'fail',
#             'altan_order_id': order_ids if altan_order_list else False,
#         })
