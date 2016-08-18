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
                
    
    '''@api.model
    def _first_install(self):
        partner_ids = self.env['res.partner'].search([('is_company','=',True)])
        
        partner_ids._validate_name()
        partner_ids._validate_street()
        partner_ids._validate_number()
        partner_ids._validate_zip()
        partner_ids._validate_city()
        #partner_ids._validate_phone()
        #partner_ids._validate_email()
        
        partner_ids = self.env['res.partner'].search([('is_company','=',False),('parent_id','!=',False)])
        
        partner_ids._validate_name()
        partner_ids._validate_street()
        partner_ids._validate_number()
        partner_ids._validate_zip()
        partner_ids._validate_city()
        #partner_ids._validate_phone()
        #partner_ids._validate_email()
    
    @api.multi
    @api.onchange('name','first_name','is_company','parent_id')
    def _validate_name(self):
        for record in self:
            # _logger.info(record.name)
            if record.is_company:
                if record.name:
                    if len(record.name.strip()) > 30:
                        #if name enthält leerzeichen
                        _logger.debug("ID %s: Firmenname %s wird zu %s" % (str(record.id),record.name,record.dhl_name1))
                    else:
                        record.dhl_name1 = record.name.strip()[0:30]
                if record.first_name:
                    record.dhl_name2 = record.first_name.strip()[0:30]
                    if len(record.first_name.strip()) > 30:
                        _logger.debug("ID %s: Firmenvorname %s wird zu %s" % (str(record.id),record.first_name,record.dhl_name2))
            else:
                if record.parent_id.dhl_name1:
                    record.dhl_name1 = record.parent_id.dhl_name1.strip()
                elif record.parent_id.name:
                    record.dhl_name1 = record.parent_id.name.strip()[0:30]
                if record.name or record.first_name:
                    if len(' '.join([record.first_name or '', record.name or '']).strip()) <= 30:
                        record.dhl_name2 = ' '.join([record.first_name or '', record.name or '']).strip()
                    else:
                        record.dhl_name2 = record.name.strip()[0:30]
                        if len(record.name.strip()) > 30:
                            _logger.debug("ID %s: Nachname %s wird zu %s" % (str(record.id),record.name,record.dhl_name2))
                
    @api.multi
    @api.onchange('street_name')
    def _validate_street(self):
        for record in self:
            # _logger.info(record.street_name)
            if record.street_name:
                record.dhl_streetName = record.street_name.strip()[0:30]
                if len(record.street_name.strip()) > 30:
                    _logger.debug("ID %s: Strasse %s wird zu %s" % (str(record.id),record.street_name,record.dhl_streetName))
                
                
    @api.multi
    @api.onchange('street_number')
    def _validate_number(self):
        for record in self:
            # _logger.info(record.street_number)
            if record.street_number:
                record.dhl_streetNumber = record.street_number.strip()[0:7]
                if len(record.street_number.strip()) > 7:
                    _logger.debug("ID %s: HNR %s wird zu %s" % (str(record.id),record.street_number,record.dhl_streetNumber))
                
                
    @api.multi
    @api.onchange('zip')
    def _validate_zip(self):
        for record in self:
            # _logger.info(record.zip)
            if record.zip:
                record.dhl_zip = record.zip.strip()[0:5]
                if len(record.zip.strip()) > 5:
                    _logger.debug("ID %s: PLZ %s wird zu %s" % (str(record.id),record.zip,record.dhl_zip))
                
                
    @api.multi
    @api.onchange('city')
    def _validate_city(self):
        for record in self:
            # _logger.info(record.city)
            if record.city:
                record.dhl_city = record.city.strip()[0:50]
                if len(record.city.strip()) > 50:
                    _logger.debug("ID %s: Stadt %s wird zu %s" % (str(record.id),record.city,record.dhl_city))
                
                
    @api.multi
    @api.onchange('phone')
    def _validate_phone(self):
        for record in self:
            # _logger.info(record.phone)
            if record.phone:
                record.dhl_phone = record.phone.strip()[0:20]
                if len(record.phone.strip()) > 20:
                    _logger.debug("ID %s: Telefon %s wird zu %s" % (str(record.id),record.phone,record.dhl_phone))
                
    @api.multi
    @api.onchange('email')
    def _validate_email(self):
        for record in self:
            # _logger.info(record.email)
            if record.email:
                record.dhl_email = record.email.strip()[0:30]
                if len(record.email.strip()) > 30:
                    _logger.debug("ID %s: Mail %s wird zu %s" % (str(record.id),record.email,record.dhl_email))
                
    
    #dhl formated address
    dhl_name1 = fields.Char('Name1', size=30, store=True)
    dhl_name2 = fields.Char('Name2', size=30, store=True)
    dhl_streetName = fields.Char('streetName', size=30, store=True)
    dhl_streetNumber = fields.Char('streetNumber', size=7, store=True)
    dhl_zip = fields.Char('zip', size=5, store=True)
    dhl_city = fields.Char('city', size=50, store=True)
    dhl_phone = fields.Char('phone', size=20, store=True)
    dhl_email = fields.Char('email', size=30, store=True)'''