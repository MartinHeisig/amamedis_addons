# -*- coding: utf-8 -*-
{
    'name': "Amamedis Delivery Note as Email",

    'summary': "Add button(s) to stock.picking form to send delivery note as email",

    'description': """
        Adds the functionality to send delivery note as email to warehouse or supplier.
        
        Adds email-template field to partner-contact to set a induvidual email-template for each supplier
        else a given default template is used
    """,

    'author': "Martin Heisig",
    'website': "https://github.com/MartinHeisig/amamedis_addons.git",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Inventory',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'email_template', 'stock', 'stock_dropshipping'],

    # always loaded
    'data': [
        'ama_email_stock_picking_view.xml',
        'ama_email_stock_picking_data.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo.xml',
    ],
}