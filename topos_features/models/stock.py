from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_done(self):
        """Changes picking state to done by processing the Stock Moves of the
        Picking

        Normally that happens when the button "Done" is pressed on a Picking
        view.
        @return: True
        """
        result = super(StockPicking, self).action_done()
        if self.picking_type_code == 'outgoing' and self.group_id.sale_id:
            for line in self.move_line_ids.filtered(
                    lambda x: x.lot_id and x.lot_id.plan_type == 'sim'):
                line.lot_id.write({'partner_id': self.partner_id.id})

        return result


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    plan_type = fields.Selection(
        related="product_id.product_tmpl_id.plan_type",
        readonly=True,
    )
    imsi_home = fields.Char(string="IMSI Home", )
    imsi_roaming_broaker_1 = fields.Char(string="IMSI R. Broaker 1", )
    imsi_roaming_broaker_2 = fields.Char(string="IMSI R. Broaker 2", )
    main_batch = fields.Char(string="Main Batch", )
    batch_a = fields.Char(string="Batch A", )
    batch_b = fields.Char(string="Batch B", )
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner", )

    def name_get(self):
        res = []
        for lot in self:
            res.append((lot.id, '[%s] %s' % (lot.name, lot.ref)))
        return res
