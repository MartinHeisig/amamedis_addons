# -*- coding: utf-8 -*-
{
    'name': "Amamedis Lieferung",

    'summary': """
        Customized delivery for Amamedis""",

    'description': """
        Extension for Odoo to order shipments with DHL, track them and initiate following steps
    """,

    'author': "Martin Heisig",
    'website': "https://github.com/MartinHeisig/amamedis_addons.git",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Inventory',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'base_phone',
        'delivery',
        'email_template',
        'partner_street_number',
        'purchase_transport_multi_address',
        'quotation_split',
        'sale_stock',
        'stock',
        'stock_dropshipping',
        'dhl_delivery',
        'release_quantity',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'delivery_carrier_view.xml',
        'res_company_view.xml',
        'res_partner_view.xml',
        'stock_dhl_view.xml',
        'stock_dm_view.xml',
        'records_dhl.xml',
        'stock_view.xml',
        'sale_view.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
        # 'demo.xml',
    # ],
}