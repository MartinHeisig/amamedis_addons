# -*- coding: utf-8 -*-
{
    'name': "Amamedis Fix Modul Account Cash Discount 6.1",

    'summary': """
        Fix for Odoo v8""",

    'description': """
        Fix property fields for use in Odoo v8
    """,

    'author': "Martin Heisig",
    'website': "https://github.com/MartinHeisig/amamedis_addons.git",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting & Finance',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'account_cash_discount_61',
        'account_voucher',
    ],

    # always loaded
    'data': [
        
    ],
    # only loaded in demonstration mode
    # 'demo': [
        # 'demo.xml',
    # ],
}