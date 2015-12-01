# -*- coding: utf-8 -*-
{
    'name': "ama_partner_email_templates",

    'summary': "Adds fields on partner form to choose a special email-template",

    'description': """
        Adds fields on partner form to choose a special email-template
    """,

    'author': "Martin Heisig",
    # 'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','email_template','purchase'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'templates.xml',
        'views/res_partner.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}