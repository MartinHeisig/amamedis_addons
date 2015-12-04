# -*- coding: utf-8 -*-

from openerp import models, fields, api

class ama_website_crm(models.Model):
    _inherit = ['crm.lead']
    _phone_fields = ['phone', 'mobile', 'fax', 'CLI', 'SNR', 'DialoutDest']
    
    CallID = fields.Integer('CallID', readonly=True)
    ACDGroup = fields.Integer('ACDGroup', readonly=True)
    DDI2 = fields.Char('DDI2', readonly=True)
    CLI = fields.Char('CLI (A-Teilnehmer)', widget='phone', readonly=True)
    DestCLI = fields.Char('Zielperson', help='Personalnummer des zuletzt verbundenen Agenten oder genutzte Zielnummer einer Überlaufzielliste', readonly=True)
    AgentSec = fields.Integer('Sekunden', help='Sekunden, die der Anrufer mit dem 1. Agent bzw. Überlaufziels verbunden war', readonly=True)
    medium_nr = fields.Many2one('ama.acd.ddi', ondelete='set null', string='Kanal Detail', compute='_search_acd_ddi', store=True)
    SNR = fields.Char('SNR', help='vom Anrufer angerufene Nummer', widget='phone', readonly=True)
    CallStart = fields.Datetime('CallStart', help='Anrufbeginn', readonly=True)
    DialoutStart = fields.Datetime('DialoutStart', help='Anrufbeginn der Verbindung beim Durchstellen durch den Agent', readonly=True)
    DialoutDest = fields.Char('DialoutDest', help='Zielnummer zu der ein Agent den Anrufer vermittelt hat (Durchstellen)', widget='phone', readonly=True)
    DialoutSec = fields.Integer('DialoutSec', help='Verbindungsdauer zum durchgestellten Ziel', readonly=True)
    CallID2 = fields.Integer('CallID2', help='CallID des ersten ausgehenden Calls (zum Agenten)', readonly=True)
    CallID3 = fields.Integer('CallID3', help='CallID des ersten ausgehenden Calls (zum 2. Agenten oder ext. MA)', readonly=True)
    TotalSec = fields.Integer('TotalSec', help='Sekunden, die der Anruf war', readonly=True)
    
    # Onchange Methode neue API
    @api.onchange('CLI')
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
                    record.partner_id = partner_ids[0]
                    # record.on_change_partner_id(partner_ids[0])
    
    # Onchange Methode alte API - benötigt separaten Aufruf im View
    '''
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
    '''
    
    @api.depends('ACDGroup', 'DDI2')
    @api.multi
    def _search_acd_ddi(self):
        for record in self:
            if record.ACDGroup and record.DDI2:
                record.medium_nr = self.env['ama.acd.ddi'].search([('ACDGroup','=',record.ACDGroup),('DDI2','=',record.DDI2)], limit=1)
    
    

class ama_acd_ddi(models.Model):
    _name = 'ama.acd.ddi'

    ACDGroup = fields.Integer('ACDGroup', required=True)
    DDI2 = fields.Char('DDI2', required=True)
    medium_nr = fields.Char('Kanal Detail', required=True)
    type = fields.Selection([
        ('drogge', "Dirk Rogge"),
        ('fax', "Fax"),
        ('inbound', "Inbound"),
    ], required=True)
    medium_nr_info = fields.Char('Kanal Detail Info')
    guide = fields.Text('Guide')
    searchtext = fields.Char('Suchtext')
    name = fields.Char('Name', compute='_compute_name')
    
    @api.multi
    def _compute_name(self):
        for record in self:
            record.name = record.medium_nr
    