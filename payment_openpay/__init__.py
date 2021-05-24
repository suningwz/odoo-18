from . import models
from . import controllers
from odoo.addons.payment.models.payment_acquirer import create_missing_journal_for_acquirers
from odoo.addons.payment import reset_payment_provider
# from odoo.addons.payment_openpay.models.payment_acquirer import create_missing_journal_for_openpay_acquirer


def uninstall_hook(cr, registry):
    reset_payment_provider(cr, registry, 'openpay')
