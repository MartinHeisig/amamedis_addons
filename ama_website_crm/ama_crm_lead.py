# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning

import openerp.tools.mail as mail

import openerp.addons.crm.crm as crm
import datetime
import logging
import math
import phonenumbers
import pytz
import urllib

_logger = logging.getLogger(__name__)

class ama_website_crm(models.Model):
    _inherit = ['crm.lead']
    _phone_fields = ['phone', 'mobile', 'fax', 'CLI', 'SNR', 'DialoutDest']
    
    # TODO: at this time the partner search is written in three different methods. should all be redirected to the on_change-method of CLI
    
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
            
                # user = self.env['res.users'].browse(uid)
                if self.env.user.company_id.country_id:
                    countrycode = self.env.user.company_id.country_id.code
                elif self.env.user.country_id:
                    countrycode = self.env.user.country_id.code
                else:
                    countrycode = False
                    
                    
                cli = phonenumbers.format_number(phonenumbers.parse(record.CLI, countrycode), phonenumbers.PhoneNumberFormat.E164)
                _logger.debug("initial value: '%s' updated value: '%s'", record.CLI, cli)
                # if 'ums@zentraldata.de' in record.email:
                if 'heisig@amamedis.de' or 'ums@zentraldata.de' in record.email_from:
                    record.name = 'Fax from ' + cli
                    record.description = 'Automatically generated from fax'
                else:
                    record.name = 'Call from ' + cli
                    
                i = 0
                partner_ids = False
                partner = False
                
                while not partner_ids and i<3:
                    partner_ids = self.env['res.partner'].search(['|',('phone', 'like', cli[:len(cli)-i]),'|',('mobile', 'like', cli[:len(cli)-i]),('fax', 'like', cli[:len(cli)-i])])
                    i += 1
                if partner_ids:
                    if len(partner_ids) > 1:
                        # tmp_partner_ids = Set([]) # Achtung: Hier drin sind Partner, nicht deren IDs
                        tmp_partner_ids = set()
                        for tmp_partner_id in partner_ids:
                            # tmp_partner = self.env['res.partner'].browse(tmp_partner_id)
                            if not tmp_partner_id.is_company:
                                if tmp_partner_id.parent_id:
                                    tmp_partner_id = tmp_partner_id.parent_id
                                else:
                                    tmp_partner_ids.add(tmp_partner_id) 
                            if tmp_partner_id.is_company:
                                if tmp_partner_id.parent_id:
                                    tmp_parent = tmp_partner_id.parent_id
                                    if tmp_parent.phone.startswith(cli[:len(cli)-(i-1)]) or tmp_parent.mobile.startswith(cli[:len(cli)-(i-1)]) or tmp_parent.fax.startswith(cli[:len(cli)-(i-1)]):
                                        tmp_partner_ids.add(tmp_parent)
                                    else:
                                        tmp_partner_ids.add(tmp_partner_id)
                                else:
                                    tmp_partner_ids.add(tmp_partner_id)
                        if len(tmp_partner_ids) > 1:
                            # del_partner = Set([])
                            del_partner = set()
                            for partner_a in tmp_partner_ids:
                                partner_search = partner_a
                                while partner_search.parent_id:
                                    partner_search = partner_search.parent_id
                                    if partner_search in tmp_partner_ids:
                                        del_partner.add(partner_a)
                                        break
                            tmp_partner_ids.difference_update(del_partner)
                            # tmp_partner_ids = tmp_partner_ids.difference(del_partner)
                        if len(tmp_partner_ids) > 1:
                            if not record.description:
                                record.description = ''
                            record.description += "\nFehler beim Kontaktsuchen - es gab mehrere Treffer:"
                            for partner in tmp_partner_ids:
                                # partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, id)
                                record.description += "\nID: " + str(partner.id) + " Name: " + partner.name
                            while True:
                                partner = tmp_partner_ids.pop()
                                if partner.is_company:
                                    break
                                if not partner.is_company and len(tmp_partner_ids) == 0:
                                    record.description += "\nFehler beim Kontaktsuchen - alle gefundenen Kontakte sind keinem Unternehmen zugeordnet"
                                    break
                        else:
                            partner = tmp_partner_ids.pop()
                    else:
                        partner = partner_ids[0]
                        if not partner.is_company:
                            if partner.parent_id:
                                partner = partner.parent_id
                            else:
                                record.description += "\nFehler beim Kontaktsuchen - einziger gefundener Kontakt ist keinem Unternehmen zugeordnet"
                
                if partner:
                    partner_name = (partner.parent_id and partner.parent_id.name) or (partner.is_company and partner.name) or False
                    record.partner_id = partner.id
                    record.partner_name = partner_name
                    record.contact_name = (not partner.is_company and partner.name) or False
                    record.title = partner.title and partner.title.id or False
                    record.street = partner.street
                    record.street2 = partner.street2
                    record.city = partner.city
                    record.state_id = partner.state_id and partner.state_id.id or False
                    record.country_id = partner.country_id and partner.country_id.id or False
                    record.email_from = partner.email
                    record.phone = partner.phone
                    record.mobile = partner.mobile
                    record.fax = partner.fax
                    record.zip = partner.zip
                    record.function = partner.function
                    record.name = partner.name
                    record.section_id = partner.section_id
                else:
                    record.phone = cli
    
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
                
    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
            'user_id': False,
        }
        if msg.get('author_id'):
            defaults.update(self.on_change_partner_id(cr, uid, None, msg.get('author_id'), context=context)['value'])
        if msg.get('priority') in dict(crm.AVAILABLE_PRIORITIES):
            defaults['priority'] = msg.get('priority')

        if defaults['name'].startswith('Fax an'):
            defaults['description'] = 'Automatically generated from fax'
            defaults['medium_id'] = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'ama_website_crm.crm_t_m_fax')
            error_description = []
            
            for line in mail.html2plaintext(msg.get('body', '')).split('\n'):
                line = line.strip()
                if line.startswith('CallID:'):
                    try:
                        cid = line.split(':', 1)[1]
                        if cid.isdigit():
                            defaults['CallID'] = cid
                        else:
                            error_description.append(line)
                    except:
                        error_description.append(line)
                if line.startswith('SNR:'):
                    try:
                        defaults['SNR'] = line.split(':', 1)[1]
                    except:
                        error_description.append(line)
                if line.startswith('ACDGroup:'):
                    try:
                        acd = line.split(':', 1)[1]
                        if acd.isdigit():
                            defaults['ACDGroup'] = acd
                        else:
                            error_description.append(line)
                    except:
                        error_description.append(line)
                if line.startswith('DDI2:'):
                    try:
                        tmp = line.split(':', 1)[1]
                        if tmp != '(-1)':
                            defaults['DDI2'] = line.split(':', 1)[1]
                    except:
                        error_description.append(line)
                if line.startswith('CLI:'):
                
                    cli_t = False
                    try:
                        cli_t = line.split(':', 1)[1]
                    except:
                        error_description.append(line)
                    if cli_t:
                        if self.pool.get('res.users').browse(cr, uid, uid).company_id.country_id:
                            countrycode = self.pool.get('res.users').browse(cr, uid, uid).company_id.country_id.code
                        elif self.pool.get('res.users').browse(cr, uid, uid).country_id:
                            countrycode = self.pool.get('res.users').browse(cr, uid, uid).country_id.code
                        else:
                            countrycode = False
                            
                            
                        cli = phonenumbers.format_number(phonenumbers.parse(cli_t, countrycode), phonenumbers.PhoneNumberFormat.E164)
                        _logger.debug("initial value: '%s' updated value: '%s'", cli_t, cli)
                            
                        i = 0
                        partner_ids = False
                        partner = False
                        
                        while not partner_ids and i<3:
                            partner_ids = self.pool.get('res.partner').search(cr, uid, ['|',('phone', 'like', cli[:len(cli)-i]),'|',('mobile', 'like', cli[:len(cli)-i]),('fax', 'like', cli[:len(cli)-i])])
                            i += 1
                        if partner_ids:
                            if len(partner_ids) > 1:
                                tmp_partner_ids = set()
                                for tmp_partner_id in partner_ids:
                                    tmp_partner = self.pool.get('res.partner').browse(cr, uid, tmp_partner_id)
                                    if not tmp_partner.is_company:
                                        if tmp_partner.parent_id:
                                            tmp_partner = tmp_partner.parent_id
                                        else:
                                            tmp_partner_ids.add(tmp_partner) 
                                    if tmp_partner.is_company:
                                        if tmp_partner.parent_id:
                                            tmp_parent = tmp_partner.parent_id
                                            if tmp_parent.phone.startswith(cli[:len(cli)-(i-1)]) or tmp_parent.mobile.startswith(cli[:len(cli)-(i-1)]) or tmp_parent.fax.startswith(cli[:len(cli)-(i-1)]):
                                                tmp_partner_ids.add(tmp_parent)
                                            else:
                                                tmp_partner_ids.add(tmp_partner)
                                        else:
                                            tmp_partner_ids.add(tmp_partner)
                                if len(tmp_partner_ids) > 1:
                                    del_partner = set()
                                    for partner_a in tmp_partner_ids:
                                        partner_search = partner_a
                                        while partner_search.parent_id:
                                            partner_search = partner_search.parent_id
                                            if partner_search in tmp_partner_ids:
                                                del_partner.add(partner_a)
                                                break
                                    tmp_partner_ids.difference_update(del_partner)
                                if len(tmp_partner_ids) > 1:
                                    defaults['description'] += "\nFehler beim Kontaktsuchen - es gab mehrere Treffer:"
                                    for partner in tmp_partner_ids:
                                        defaults['description'] += "\nID: " + str(partner.id) + " Name: " + partner.name
                                    while True:
                                        partner = tmp_partner_ids.pop()
                                        if partner.is_company:
                                            break
                                        if not partner.is_company and len(tmp_partner_ids) == 0:
                                            defaults['description'] += "\nFehler beim Kontaktsuchen - alle gefundenen Kontakte sind keinem Unternehmen zugeordnet"
                                            break
                                else:
                                    partner = tmp_partner_ids.pop()
                            else:
                                partner = self.pool.get('res.partner').browse(cr, uid, partner_ids[0])
                                if not partner.is_company:
                                    if partner.parent_id:
                                        partner = partner.parent_id
                                    else:
                                        defaults['description'] += "\nFehler beim Kontaktsuchen - einziger gefundener Kontakt ist keinem Unternehmen zugeordnet"
                                        
                        defaults['CLI'] = cli
                        defaults['partner_id'] = partner.id
                        defaults.update(self.on_change_partner_id(cr, uid, None, partner.id, context=context)['value'])
                        defaults['section_id'] = partner.section_id.id
                        defaults['name'] = partner.name
                    else:
                        error_description.append(line)
                
                if line.startswith('CallStart:'):
                    try:
                        cs = line.split(':', 1)[1]
                        tz = pytz.timezone(self.pool.get('res.users').browse(cr, uid, uid).partner_id.tz) or pytz.utc
                        defaults['CallStart'] = tz.localize(datetime.datetime.strptime(cs, '%d.%m.%Y %H:%M')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M')
                    except:
                        error_description.append(line)
                if line.startswith('HSekunden:'):
                    try:
                        hsec = line.split(':', 1)[1]
                    except:
                        error_description.append(line)
                    if hsec and hsec.isdigit():
                        defaults['TotalSec'] = int(math.ceil(float(hsec) / 100))
                    else:
                        error_description.append(line)
                if error_description:
                    defaults['description'] += '\nDatatype Mismatch (Parse Fax): '
                    for l in error_description:
                        defaults['description'] += '\n' + l

        defaults.update(custom_values)
        return super(ama_website_crm, self).message_new(cr, uid, msg, custom_values=defaults, context=context)


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
