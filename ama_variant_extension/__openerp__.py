# -*- coding: utf-8 -*-
{
    'name': "Amamedis Product Variants Extension",

    'summary': """Amamedis Extensions for Product Variants""",

    'description': """
        Extends the given product.attribute and product.attribute.value system with extensions for the attributes giving a connected model, so the value gives the id inside the model
    """,

    'author': "Martin Heisig",
    'website': "https://github.com/MartinHeisig/amamedis_addons.git",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sales Management',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product'],

    # always loaded
    'data': [
        'ir.model.access.csv',
        'ama_variant_extension_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo.xml',
    ],
}