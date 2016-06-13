# -*- coding: utf-8 -*-
{
    'name': "Amamedis Mahnwesen",

    'summary': """
        Customize invoices for Amamedis to support automated dunning""",

    'description': """
        Extension for Odoo which adds dunning-levels for invoices and sends automated emails after several days
    """,

    'author': "Martin Heisig",
    'website': "https://github.com/MartinHeisig/amamedis_addons.git",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Invoicing & Payments',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'account',
        'sale',
        'account_followup',
        'email_template',
    ],

    # always loaded
    'data': [
        'account_view.xml',
        'partner_view.xml',
        'data.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
        # 'demo.xml',
    # ],
}