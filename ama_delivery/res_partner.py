# -*- coding: utf-8 -*-

from openerp import models, fields, api

import logging

_logger = logging.getLogger(__name__)

class res_partner_dhl_addresses(models.Model):
    _inherit = 'res.partner'
    # _phone_fields = ['dhl_phone', 'phone', 'fax', 'mobile']
    # _phone_fields = super(res_partner_dhl_addresses)._phone_fields.append('dhl_phone')
    
    
    mail_template_stock_picking = fields.Many2one(comodel_name='email.template', domain="[('model', '=', 'stock.picking')]", ondelete='set null', string='Lieferschein')
    del_name1 = fields.Char('Versandname 1', size=30, store=True, help='Name der bei der Lieferung verwendet wird')
    del_name2 = fields.Char('Versandname 2', size=30, store=True, help='Namensergänzung die bei der Lieferung verwendet wird')
    
    @api.model
    def _first_install(self):
        partner_ids = self.env['res.partner'].search([])
        
        partner_ids._get_delivery_names()
        
    @api.multi
    @api.onchange('name','first_name','is_company')
    def _get_delivery_names(self):
        for record in self:
            record.name = record.name and record.name.strip()
            record.first_name = record.first_name and record.first_name.strip()
            
            if record.is_company:
                length = len(record.name)
            
                if length > 30:
                    min_split = min(length - 31, 30)
                    max_split = 30

                    if ' ' in record.name[max(min_split-1,0):max_split] or '-' in record.name[max(min_split-1,0):max_split]:
                        i = max_split - 1

                        while i >= min_split-1:
                            if record.name[i] in [' ','-']:
                                record.del_name1 = record.name[:i+1].strip()
                                record.del_name2 = record.name[i+1:].strip()
                                break
                            i -= 1
                    else:
                        record.del_name1 = record.name[:30].strip()
                        record.del_name2 = record.name[30:].strip()
                    
                    _logger.debug('Firmenname %s wurde aufgeteilt in %s UND %s' % (record.name, record.del_name1, record.del_name2))
 
                else:
                    record.del_name1 = record.name.strip()
                    record.del_name2 = ''
            else:
                if len(' '.join([record.first_name or '', record.name or '']).strip()) > 30:
                    record.del_name1 = record.name[:30].strip()
                    record.del_name2 = ''
                else:
                    record.del_name1 = ' '.join([record.first_name or '', record.name or '']).strip()
                    record.del_name2 = ''
