# -*- coding: utf-8 -*-
{
    'name': "ama_website_crm",

    'summary': "Adapt module website_crm for Amamedis",

    'description': """
        Adapt module website_crm for Amamedis, add custom fields in crm.lead and adapts the lead-creation from contact form 
    """,

    'author': "Martin Heisig",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Lead Automation',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'website_crm', 'base_phone'],

    # always loaded
    'data': [
        'ama_crm_lead_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo.xml',
    ],
}