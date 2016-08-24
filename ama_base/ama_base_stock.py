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


class amamedis_base_stock(models.Model):
    _inherit = 'stock.picking'
    
    @api.multi
    @api.depends('origin')
    def _get_origin(self):
        for record in self:
            so_ids = False
            po_ids = self.env['purchase.order'].search([('name', '=', record.origin)])
            if po_ids and po_ids[0]:
                so_ids = self.env['sale.order'].search([('name', '=', po_ids[0].origin)])
            else:
                so_ids = self.env['sale.order'].search([('name', '=', record.origin)])
            
            if so_ids and so_ids[0]:
                record.orig_order = so_ids[0]
            else:
                record.orig_order = False
    
    orig_order = fields.Many2one('sale.order', string='Originalauftrag', compute='_get_origin', store=True, default=False)
        