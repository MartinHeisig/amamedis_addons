# -*- coding: utf-8 -*-

from openerp import models, fields, api

class ama_website_crm(models.Model):
    _inherit = ['crm.lead']
    
    CallID = fields.Integer('CallID')
    ACDGroup = fields.Integer('ACDGroup')
    DDI2 = fields.Integer('DDI2')
    CLI = fields.Char('CLI (A-Teilnehmer)')
    DestCLI = fields.Char('DestCLI')
    AgentSec = fields.Char('Sekunden')