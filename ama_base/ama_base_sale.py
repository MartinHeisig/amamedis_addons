# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 artmin - IT Dienstleistungen.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from openerp import models, fields, tools, api
from openerp.exceptions import except_orm, Warning
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)


class amamedis_sales_team(models.Model):
    _inherit = 'crm.case.section'
    _description = "Add custom fields for Amamedis sales team."
    
    @api.multi
    @api.depends('image')
    def _get_image(self):
        for record in self:
            record.image_medium = tools.image_resize_image_medium(record.image)

    @api.multi
    def _set_image(self):
        for record in self:
            record.image = tools.image_resize_image_big(record.image_medium)

    from_email = fields.Char('Absenderemail', help='Emailadresse mit der Emails aus dem System versand werden.')
    signature = fields.Html('Signatur', help='Signatur in Emails')
    from_line = fields.Char('Absenderzeile', help='Adresszeile für ausgehende Dokumente')
    footer = fields.Html('Fußzeile', help='Fußzeile für externe Dokumente')
    contact = fields.Html('Ansprechpartner', help='Ansprechpartner welche in ausgehenden Dokumenten angezeigt werden.')
    closing = fields.Char('Briefabschluss')
    image = fields.Binary('Logo', attachment=True)
    image_medium = fields.Binary('Medium-sized image', compute='_get_image', inverse='_set_image', store=True, attachment=True)

    
class amamedis_sale_order(models.Model):
    _inherit = 'sale.order'
    _description = "Add custom fields to sale order."

    delivery_date = fields.Char('Lieferdatum')
    client_order_date = fields.Date('Bestelldatum')
    ref = fields.Char('Kundennummer', related='partner_id.ref')


class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    
    min_quantity = fields.Float('Mindestbestellmenge', related='product_id.min_quantity', readonly=True)
    
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)
        
        warning = {}            
        warning_msgs = res.get('warning') and res['warning'].get('message', '') or ''
        
        if product and flag:
            product_obj = self.pool.get('product.product').browse(cr, uid, product)
            line_min = product_obj.min_quantity or 0
            if qty < line_min:
                warn_msg = _('Bitte eingegebene Menge prüfen, da der aktuelle Wert %s kleiner ist, als die im Produkt hinterlegte Mindestbestellmenge von %s!\n\n' % (qty, line_min))
                warning_msgs += _('Mindestbestellmenge! : ') + warn_msg + '\n\n'
        
        if warning_msgs:
                warning = {
                   'title': _('Configuration Error!'),
                   'message' : warning_msgs
                }
        res.update({'warning': warning})
        
        return res
        
    def product_id_change_with_wh(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False, context=None):
        change_packaging = False
        if product:
            product_obj = self.pool.get('product.product').browse(cr, uid, product)
            if product_obj.packaging_ids:
                if not packaging or packaging != product_obj.packaging_ids[0].id:
                    packaging = product_obj.packaging_ids[0].id
                    change_packaging = True
        res = super(sale_order_line, self).product_id_change_with_wh(cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, warehouse_id=warehouse_id, context=context)
        if change_packaging:
            res['value'].update({'product_packaging': packaging,})
        return res