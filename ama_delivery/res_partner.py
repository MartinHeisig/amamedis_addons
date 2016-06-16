# -*- coding: utf-8 -*-

from openerp import models, fields, api

import logging

_logger = logging.getLogger(__name__)

class res_partner_dhl_addresses(models.Model):
    _inherit = 'res.partner'
    _phone_fields = ['dhl_phone', 'phone', 'fax', 'mobile']
    # _phone_fields = super(res_partner_dhl_addresses)._phone_fields.append('dhl_phone')
    
    @api.model
    def _first_install(self):
        partner = self.env['res.partner']
        _logger.info('Hier bin ich')
        _logger.info(str(partner))
        partner._validate_street()
    
    @api.multi
    @api.onchange('name','first_name','is_company','parent_id')
    def _validate_name(self):
        for record in self:
            # _logger.info(record.name)
            if record.is_company:
                if record.name:
                    record.dhl_name1 = record.name.strip()[0:30]
                if record.first_name:
                    record.dhl_name2 = record.first_name.strip()[0:30]
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
                
    @api.multi
    @api.onchange('street_name')
    def _validate_street(self):
        for record in self:
            _logger.info(record.street_name)
            if record.street_name:
                record.dhl_streetName = record.street_name.strip()[0:30]
                
                
    @api.multi
    @api.onchange('street_number')
    def _validate_number(self):
        for record in self:
            _logger.info(record.street_number)
            if record.street_number:
                record.dhl_streetNumber = record.street_number.strip()[0:7]
                
                
    @api.multi
    @api.onchange('zip')
    def _validate_zip(self):
        for record in self:
            _logger.info(record.zip)
            if record.zip:
                record.dhl_zip = record.zip.strip()[0:5]
                
    '''@api.multi
    def _validate_zip(self, tmp_zip):
        for record in self:
            _logger.info(tmp_zip)
            if tmp_zip:
                record.dhl_zip = tmp_zip.strip()[0:5]'''
                
                
    @api.multi
    @api.onchange('city')
    def _validate_city(self):
        for record in self:
            _logger.info(record.city)
            if record.city:
                record.dhl_city = record.city.strip()[0:50]
                
                
    @api.multi
    @api.onchange('phone')
    def _validate_phone(self):
        for record in self:
            _logger.info(record.phone)
            if record.phone:
                record.dhl_phone = record.phone.strip()[0:20]
                
    @api.multi
    @api.onchange('email')
    def _validate_email(self):
        for record in self:
            _logger.info(record.email)
            if record.email:
                record.dhl_email = record.email.strip()[0:30]
                
    
    #dhl formated address
    dhl_name1 = fields.Char('Name1', size=30, store=True)
    dhl_name2 = fields.Char('Name2', size=30, store=True)
    dhl_streetName = fields.Char('streetName', size=30, store=True)
    dhl_streetNumber = fields.Char('streetNumber', size=7, store=True)
    dhl_zip = fields.Char('zip', size=5, store=True)
    dhl_city = fields.Char('city', size=50, store=True)
    dhl_phone = fields.Char('phone', size=20, store=True)
    dhl_email = fields.Char('email', size=30, store=True)