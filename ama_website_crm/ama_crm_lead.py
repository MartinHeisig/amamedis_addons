# -*- coding: utf-8 -*-

from openerp import models, fields, api

class ama_website_crm(models.Model):
    _inherit = ['crm.lead']
    
    CallID = fields.Integer('CallID')
    ACDGroup = fields.Integer('ACDGroup')
    DDI2 = fields.Char('DDI2')
    CLI = fields.Char('CLI (A-Teilnehmer)')
    DestCLI = fields.Char('Zielperson')
    AgentSec = fields.Integer('Sekunden')
    medium_nr = fields.Many2one('ama.acd.ddi', ondelete='set null', string='Kanal Detail')
    

class ama_acd_ddi(models.Model):
    _name = 'ama.acd.ddi'

    ACDGroup = fields.Integer('ACDGroup')
    DDI2 = fields.Char('DDI2')
    medium_nr = fields.Char('Kanal Detail')
    name = fields.Char(compute='_compute_name')
    
    @api.multi
    def _compute_name(self):
        for record in self:
            record.name = record.medium_nr
    