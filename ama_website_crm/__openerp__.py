# -*- coding: utf-8 -*-
{
    'name': "ama_website_crm",

    'summary': "Adapt module website_crm for Amamedis",

    'description': """
        Adapt module website_crm for Amamedis, adding custom fields in crm.lead to be filled from an inbound phone call and tries to find a partner contact based on the given caller phone number 
    """,

    'author': "Martin Heisig",

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
        'ir.model.access.csv'
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo.xml',
    ],
}