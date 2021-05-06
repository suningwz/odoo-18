{
    'name': 'Openpay Payment Acquirer',
    'summary': 'Payment Acquirer: Openpay Implementation',
    'description': """Openpay Payment Acquirer""",
    'author': "MiPrimerErp, S.A. de C.V.",
    'category': 'Ecommerce',
    'version': '1.0.0',
    'depends': [
        'account',
        'payment',
        'website_sale',
    ],
    # always loaded
    'data': [
        'views/assets.xml',
        'views/payment_view.xml',
        'report/transaction_report.xml',
        'report/transaction_report_template.xml',
        'views/payment_openpay_template.xml',
        'views/payment_portal_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    # 'qweb': ['static/src/xml/proccessing_payment.xml'],
    'images': ['static/description/icon.png'],
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
}
