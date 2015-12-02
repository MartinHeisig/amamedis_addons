# -*- coding: utf-8 -*-

from openerp import models, fields, api

class ama_website_crm(models.Model):
    _inherit = ['crm.lead']
    _phone_fields = ['phone', 'mobile', 'fax', 'CLI']
    
    CallID = fields.Integer('CallID', readonly=True)
    ACDGroup = fields.Integer('ACDGroup', readonly=True)
    DDI2 = fields.Char('DDI2', readonly=True)
    CLI = fields.Char('CLI (A-Teilnehmer)', widget='phone')
    DestCLI = fields.Char('Zielperson', readonly=True)
    AgentSec = fields.Integer('Sekunden', readonly=True)
    medium_nr = fields.Many2one('ama.acd.ddi', ondelete='set null', string='Kanal Detail', readonly=True)
    
    '''@api.onchange('CLI')
    @api.multi
    def _search_partner(self):
        for record in self:
            if record.CLI:
                if record.description:
                    record.description += '\nSearched CLI: ' + record.CLI
                else:
                    record.description = 'Searched CLI: ' + record.CLI
                partner_ids = self.env['res.partner'].search([('phone', 'like', record.CLI)])
                for partner in partner_ids:
                    record.description += '\n' + partner.name + ' ' + partner.phone
                if partner_ids:
                    record.partner_id = partner_ids[0]'''
                    # record.on_change_partner_id(partner_ids[0])
                    
    def on_change_cli(self, cr, uid, ids, cli, context=None):
        values = {}
        if cli:
            partner_ids = self.pool.get('res.partner').search(cr, uid, [('phone', 'like', cli)])
            if partner_ids and partner_ids[0]:
                partner = self.pool.get('res.partner').browse(cr, uid, partner_ids[0], context=context)
                values = {
                    'partner_id': partner.id
            }
        return {'value': values}
    

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
    