# -*- coding: utf-8 -*-

from openerp import models, fields, tools, api
from openerp.exceptions import except_orm, Warning

import openerp.addons.decimal_precision as dp


class ama_product(models.Model):
    _inherit = 'product.template'
    _description = "Add custom fields on product.template for Amamedis."

    description_orderslip = fields.Text('Beschreibung für Bestellscheine',translate=True, help="A description of the Product for the order slip")
    
    '''_columns = {
        
        # 'list_price': fields.related('product_variant_ids', 'list_price', type='float', string='Sale Price'),
        # 'standard_price': fields.related('product_variant_ids', 'standard_price', type='float', string='Cost Price'),
        # 'description_orderslip': fields.related('product_variant_ids', 'description_orderslip', type='text', string='Order slip description'),
        'description_orderslip': fields.text('Order slip description',translate=True,
            help="A description of the Product for the order slip"),
    }'''
    
class ama_product_product(models.Model):
    _inherit = 'product.product'
    _description = "Add custom fields on product.product for Amamedis."
    
    description_orderslip = fields.Text('Beschreibung für Bestellscheine', translate=True, help="A description of the Product for the order slip")
    min_quantity = fields.Float('Mindestbestellmenge', size=64, default=0)
    
    '''_columns = {
        # 'list_price': fields.float('Sale Price',
        #                            digits_compute=dp.get_precision('Sale Price'),
        #                            help="Base price for computing the customer price. "
        #                            "Sometimes called the catalog price."),
        # 'standard_price': fields.float('Cost Price', required=True,
        #                                digits_compute=dp.get_precision('Purchase Price'),
        #                                help="Product's cost for accounting stock valuation. "
        #                                "It is the base price for the supplier price."),
        'description_orderslip': fields.text('Order slip description',translate=True,
            help="A description of the Product for the order slip"),
    }
    
    
        
    _defaults = {
        # 'description_orderslip': name,
        # 'description_orderslip': lambda self,cr,uid, context: self.pool.get('product.template').browse(cr, uid, id, context).description_orderslip
        # 'description_orderslip': super(ama_product).id,
        # 'description_orderslip': "bubu",
    }'''