# -*- coding: utf-8 -*-
{
    'name': "Amamedis Lead Generation",

    'summary': "Adapt crm.lead with special functions for Amamedis for lead generation from phone and fax and message/attachment handling inside the lead",

    'description': """
Amamedis Lead Generation
========================


Changes on Lead-Generation:
---------------------------
    * Adding several fields for phone and fax call data
    * Emails with subject starting with "Fax an" trigger special routine for partner search based on submitted CLI if possible
    * Special routes for incoming phone calls to find partner based on submitted CLI if possible
    * Adding new model for ACDGroup-DDI2 combination automatically selected by transmitted data for phone/fax

    
Further Changes:
----------------
    * Adding attachment list for crm.lead and res.partner
    * Adding field to crm.lead for a suggested name for the attachments based on the incoming lead (via phone, fax, ...)
    * Adding button to crm.lead for renaming the attachments with this name and set the attachment partner to the current selected partner
    * Adding button to crm.lead to move all non-system-notification messages and all attachments to currently selected partner
    * While generating a quotation from a lead for preselected lead-type of fax/phone/mail order all non-system-notification messages and all attachments are moved to the new quotation
    * Further the data from the lead description field generates a new message with its input in the new quotation
    """,

    'author': "Martin Heisig",
    'website': "https://github.com/MartinHeisig/amamedis_addons.git",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Lead Automation',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'website_crm', 'base_phone', 'sale_crm', 'website'],

    # always loaded
    'data': [
        'ama_crm_lead_view.xml',
        'ama_crm_lead_data.xml',
        'ir.model.access.csv'
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo.xml',
    ],
}