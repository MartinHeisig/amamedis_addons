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


class amamedis_base_account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    mail_text = fields.Text('E-Mail-Text Rechnung', help='Text der zusaetzlich zum standardisierten Text der E-Mail mit der Rechnung hinzugefuegt wird. Position direkt vor der Grussformel.')
    
    @api.model
    def create(self, vals):
 
        #Write your logic here
        if vals.get('origin'):
            so_ids = False
            
            so_ids = self.env['sale.order'].search([('name', '=', vals['origin'])])
            
            if so_ids and so_ids[0]:
                vals['mail_text'] = so_ids[0].mail_text_inv
        
        res = super(amamedis_base_account_invoice, self).create(vals)
 
        #Write your logic here
         
        return res
        
    @api.model
    def _get_first_invoice_fields(self, invoice):
        res = super(amamedis_base_account_invoice, self)._get_first_invoice_fields(invoice)
        res['mail_text'] = invoice.mail_text
        return res