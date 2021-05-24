{
    'name': "Topos: Funcionalidades Extras",
    'summary': """Este módulo agrega nuevos campos en el lote y el producto.""",
    'author': "MiPrimerErp, S.A. de C.V.",
    'category': 'Extra',
    'version': '13.0.0',
    'depends': [
        'product',
        'sale',
        'stock',
        'payment',
        'website_sale',
    ],
    # always loaded
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_config_parameter_data.xml',
        'data/ir_sequence_data.xml',
        'views/msisdn_views.xml',
        'views/product_view.xml',
        'views/res_partner_view.xml',
        'views/stock_lot_view.xml',
        'views/sale_view.xml',
        'views/account_move_view.xml',
        'views/website_sale_template.xml',
    ],
    'pre_init_hook': 'pre_init_product_code',
}
