# -*- coding: utf-8 -*-

from openerp import models, fields, api, tools
from openerp.exceptions import except_orm, Warning

import openerp.tools.mail as mail
from email.message import Message
from openerp.addons.mail.mail_message import decode
from openerp.tools.translate import _

import openerp.addons.crm.crm as crm
import datetime
import dateutil
import logging
import math
import phonenumbers
import pytz
import re
import urllib

_logger = logging.getLogger(__name__)

mail_header_msgid_re = re.compile('<[^<>]+>')

class ama_website_crm(models.Model):
    _inherit = ['crm.lead']
    _phone_fields = ['phone', 'mobile', 'fax', 'CLI', 'SNR', 'DialoutDest']
    
    # TODO: at this time the partner search is written in three different methods. should all be redirected to the on_change-method of CLI
    
    CallID = fields.Integer('CallID', readonly=True)
    ACDGroup = fields.Integer('ACDGroup', readonly=True)
    DDI2 = fields.Char('DDI2', readonly=True)
    CLI = fields.Char('CLI (A-Teilnehmer)', widget='phone', readonly=True)
    DestCLI = fields.Char('Zielperson ID', help='Personalnummer des zuletzt verbundenen Agenten oder genutzte Zielnummer einer Überlaufzielliste', readonly=True)
    DestCLIName = fields.Many2one('ama.cli', ondelete='set null', string='Zielperson', compute='_search_cli_name', help='Name der Zielperson')
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
    attachments = fields.One2many('ir.attachment', 'res_id', domain=[('res_model','=','crm.lead')])
    attachmentType = fields.Selection([
        ('order_fax', "Bestellung Fax"),
        ('order', "Bestellung Mail/Telefon"),
        ('sepa_fax', "SEPA Fax"),
        ('info_chance', "Info Chance"),
        ('info_order', "Info Auftrag"),
        ('info_company', "Info Firma"),
    ], required=True, string='Nachricht-/Ereignisart', default='info_chance')
    attachmentName = fields.Char('Name Anhang')
    
    '''@api.onchange('partner_id')
    @api.multi
    def _change_attachment_partner(self):
        for record in self:
            record.description += '\n' + record.partner_id.name
            for attachment in record.attachments:
                record.description += '\n' + record.partner_id.name + ' --> ' + attachment.name
                values = {'partner_id': record.partner_id[0]}
                attachment.write(values)'''
    
    @api.onchange('attachmentType')
    @api.multi
    def _compute_filename(self):
        for record in self:
            if record.attachmentType in {'order_fax','order'}:
                record.attachmentName = 'Bestellung'
                if record.CallStart:
                    record.attachmentName +=  '_%s' % datetime.datetime.strftime(datetime.datetime.strptime(record.CallStart, '%Y-%m-%d %H:%M:%S'), '%Y%m%d')
                else:
                    record.attachmentName +=  '_%s' % datetime.datetime.today().strftime('%Y%m%d')
                if record.DDI2:
                    record.attachmentName +=  '_%s' % record.DDI2
                if record.CLI:
                    if record.CLI.startswith('+'):
                        record.attachmentName += '_%s' % record.CLI.replace('+', '00', 1)
                    else:
                        record.attachmentName += '_%s' % record.CLI
                if record.CallID:
                    record.attachmentName +=  '_%s' % record.CallID
            if record.attachmentType == 'sepa_fax':
                record.attachmentName = 'SEPA'
                if record.CallStart:
                    record.attachmentName +=  '_%s' % datetime.datetime.strftime(datetime.datetime.strptime(record.CallStart, '%Y-%m-%d %H:%M:%S'), '%Y%m%d')
                else:
                    record.attachmentName +=  '_%s' % datetime.datetime.today().strftime('%Y%m%d')
                if record.DDI2:
                    record.attachmentName +=  '_%s' % record.DDI2
                if record.CLI:
                    if record.CLI.startswith('+'):
                        record.attachmentName += '_%s' % record.CLI.replace('+', '00', 1)
                    else:
                        record.attachmentName += '_%s' % record.CLI
                if record.CallID:
                    record.attachmentName +=  '_%s' % record.CallID
                
    
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
                if defaults['name'].startswith('Fax an'):
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
                                    if tmp_parent.phone and tmp_parent.phone.startswith(cli[:len(cli)-(i-1)]) or tmp_parent.mobile and tmp_parent.mobile.startswith(cli[:len(cli)-(i-1)]) or tmp_parent.fax and tmp_parent.fax.startswith(cli[:len(cli)-(i-1)]):
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
    
    @api.multi
    def rename_attachments(self):
        for record in self:
            counter = 0
            for attachment in record.attachments:
                extension = attachment.mimetype.rsplit('/',1)
                if extension[1]:
                    ext = extension[1]
                if record.attachmentName:
                    new_name = record.attachmentName
                    if counter > 0:
                        new_name += ' (%s)' % counter
                    if ext:
                        new_name += '.%s' % ext
                    attachment.name = new_name
                    attachment.datas_fname = new_name
                    counter += 1
                attachment.partner_id = record.partner_id
                    
    @api.multi
    def move_to_partner(self):
        message = self.env['mail.message']
        for record in self:
            for history in record.message_ids:
                if history.type != 'notification':
                    if history.attachment_ids:
                        for attachment in history.attachment_ids:
                            values = {'res_id': record.partner_id.id, 'res_model': 'res.partner', 'partner_id': record.partner_id.id}
                            attachment.write(values)
                    msg = message.browse(history.id)
                    vals = {'res_id': record.partner_id.id, 'model': 'res.partner', 'subject' : _("Message moved from Lead %s : %s") % (record.id, history.subject)}
                    msg.write(vals)
            for attachment in record.attachments:
                values = {'res_id': record.partner_id.id, 'res_model': 'res.partner', 'partner_id': record.partner_id.id}
                attachment.write(values)
            record.partner_id.message_post(body=re.sub(r"\r|\n|(\r\n)", "<br />", record.description or ''), subject=_("Description from Lead %s") % (record.id), type='comment')
    
    @api.depends('DestCLI')
    @api.multi
    def _search_cli_name(self):
        for record in self:
            if record.DestCLI:
                record.DestCLIName = self.env['ama.cli'].search([('cli', '=', record.DestCLI)])
    
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
        
        if defaults['name'].startswith('Anruf im CC'):
            for line in mail.html2plaintext(msg.get('body','')).split('\n'):
                line = line.strip()
                if line.startswith('CallID:'):
                    try:
                        cid = line.split(':', 1)[1].strip()
                        if cid.isdigit():
                            lead_id = self.pool.get('crm.lead').search(cr,uid,[('CallID','=',cid)])
                            lead = self.pool.get('crm.lead').browse(cr,uid,lead_id)
                            if lead and lead[0]:
                                lead[0].message_post(body=msg.get('body',''), subject=msg.get('subject') or _("No Subject"), type='comment')
                                return
                    except:
                        _logger.error('Error with CallCenter Mail with %s' % line)
        
        if defaults['name'].startswith('Fax an'):
            defaults['description'] = 'Automatically generated from fax'
            defaults['medium_id'] = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'ama_website_crm.crm_t_m_fax')
            error_description = []
            
            # error_description.append(str(msg))
            
            for line in mail.html2plaintext(msg.get('body', '')).split('\n'):
                line = line.strip()
                if line.startswith('CallID:'):
                    try:
                        cid = line.split(':', 1)[1]
                        if cid.isdigit():
                            defaults['CallID'] = cid
                        else:
                            if line not in error_description:
                                error_description.append(line)
                    except:
                        if line not in error_description:
                            error_description.append(line)
                if line.startswith('SNR:'):
                    try:
                        defaults['SNR'] = line.split(':', 1)[1]
                    except:
                        if line not in error_description:
                            error_description.append(line)
                if line.startswith('ACDGroup:'):
                    try:
                        acd = line.split(':', 1)[1]
                        if acd.isdigit():
                            defaults['ACDGroup'] = acd
                        else:
                            if line not in error_description:
                                error_description.append(line)
                    except:
                        if line not in error_description:
                            error_description.append(line)
                if line.startswith('DDI2:'):
                    try:
                        tmp = line.split(':', 1)[1]
                        if tmp != '(-1)':
                            defaults['DDI2'] = line.split(':', 1)[1]
                    except:
                        if line not in error_description:
                            error_description.append(line)
                if line.startswith('CLI:'):
                
                    cli_t = False
                    try:
                        cli_t = line.split(':', 1)[1].replace(' ', '')
                    except:
                        if line not in error_description:
                            error_description.append(line)
                    if cli_t and (cli_t.isdigit() or (cli_t.startswith('+') and cli_t[1:].isdigit())):
                        if self.pool.get('res.users').browse(cr, uid, uid).company_id.country_id:
                            countrycode = self.pool.get('res.users').browse(cr, uid, uid).company_id.country_id.code
                        elif self.pool.get('res.users').browse(cr, uid, uid).country_id:
                            countrycode = self.pool.get('res.users').browse(cr, uid, uid).country_id.code
                        else:
                            countrycode = None
                            
                        try:    
                            cli = phonenumbers.format_number(phonenumbers.parse(cli_t, countrycode), phonenumbers.PhoneNumberFormat.E164)
                            _logger.debug("initial value: '%s' updated value: '%s'", cli_t, cli)
    	                except:
                            if cli_t.startswith('+') and cli_t[1:].isdigit():
                                try:
                                    cli = phonenumbers.format_number(phonenumbers.parse(cli_t[1:], countrycode), phonenumbers.PhoneNumberFormat.E164)
                                    _logger.debug("wrong initial value: '%s' updated value: '%s'", cli_t, cli)
                                except:
                                    if line not in error_description:
                                        error_description.append(line)
                                        _logger.debug("phonenumber seems not to be valid (extra test without +): '%s'", cli_t)
                                        cli = False
                            else:
                                if line not in error_description:
                                    error_description.append(line)
                                    _logger.debug("phonenumber seems not to be valid: '%s'", cli_t)
                                    cli = False
                            
                        i = 0
                        partner_ids = False
                        partner = False
                        
                        while cli and not partner_ids and i<3:
                            partner_ids = self.pool.get('res.partner').search(cr, uid, ['|',('phone', 'like', cli[:len(cli)-i]),'|',('mobile', 'like', cli[:len(cli)-i]),('fax', 'like', cli[:len(cli)-i])])
                            i += 1
                            # defaults['description'] += "\nSuchlauf fuer: " + cli[:len(cli)-i]
                        if not partner_ids:
                            i = 0
                            cli_t = False
                            try:
                                cli_t = cli.split('+49', 1)[1]
                            except:
                                if line not in error_description:
                                    error_description.append(line)
                            if cli_t:
                                cli = cli_t
                                while not partner_ids and i<3:
                                    partner_ids = self.pool.get('res.partner').search(cr, uid, ['|',('phone', 'like', cli[:len(cli)-i]),'|',('mobile', 'like', cli[:len(cli)-i]),('fax', 'like', cli[:len(cli)-i])])
                                    i += 1
                                    # defaults['description'] += "\nSuchlauf fuer: " + cli[:len(cli)-i]
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
                                            if tmp_parent.phone and tmp_parent.phone.startswith(cli[:len(cli)-(i-1)]) or tmp_parent.mobile and tmp_parent.mobile.startswith(cli[:len(cli)-(i-1)]) or tmp_parent.fax and tmp_parent.fax.startswith(cli[:len(cli)-(i-1)]):
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
                        if partner:
                            defaults['partner_id'] = partner.id
                            defaults.update(self.on_change_partner_id(cr, uid, None, partner.id, context=context)['value'])
                            defaults['section_id'] = partner.section_id.id
                            defaults['name'] = partner.name
                        else:
                            defaults['description'] += "\nFehler beim Kontaktsuchen - es wurde kein passender Kontakt gefunden fuer die CLI: " + cli
                    else:
                        if line not in error_description:
                            error_description.append(line)
                
                if line.startswith('CallStart:'):
                    try:
                        cs = line.split(':', 1)[1]
                        tz = pytz.timezone(self.pool.get('res.users').browse(cr, uid, uid).partner_id.tz) or pytz.utc
                        defaults['CallStart'] = tz.localize(datetime.datetime.strptime(cs, '%d.%m.%Y %H:%M')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M')
                    except:
                        if line not in error_description:
                            error_description.append(line)
                if line.startswith('HSekunden:'):
                    try:
                        hsec = line.split(':', 1)[1]
                    except:
                        if line not in error_description:
                            error_description.append(line)
                    if hsec and hsec.isdigit():
                        defaults['TotalSec'] = int(math.ceil(float(hsec) / 100))
                    else:
                        if line not in error_description:
                            error_description.append(line)
                if error_description:
                    defaults['description'] += '\nDatatype Mismatch (Parse Fax): '
                    for l in error_description:
                        defaults['description'] += '\n' + l
                        
            if msg.get('attachments'):
                defaults['attachmentType'] = 'order_fax'
                defaults['attachmentName'] = 'Bestellung'
                if defaults.get('CallStart'):
                    defaults['attachmentName'] +=  '_%s' % datetime.datetime.strftime(datetime.datetime.strptime(defaults['CallStart'], '%Y-%m-%d %H:%M'), '%Y%m%d')
                else:
                    defaults['attachmentName'] +=  '_%s' % datetime.datetime.today().strftime('%Y%m%d')
                if defaults.get('DDI2'):
                    defaults['attachmentName'] +=  '_%s' % defaults['DDI2']
                if defaults.get('CLI'):
                    if defaults['CLI'].startswith('+'):
                        defaults['attachmentName'] += '_%s' % defaults['CLI'].replace('+', '00', 1)
                    else:
                        defaults['attachmentName'] += '_%s' % defaults['CLI']
                if defaults.get('CallID'):
                    defaults['attachmentName'] +=  '_%s' % defaults['CallID']
                
            
            '''if msg.get('attachments'):
                for attachment in msg.get('attachments'):
                    defaults['description'] += '\nALT: ' + str(attachment)
                    attachment = list(attachment)
                    if attachment[0]:
                        attachment[0] = 'Fax'
                        if defaults['CallStart']:
                            attachment[0] += '_%s' % defaults['CallStart']
                            attachment[0] += '_%s' % datetime.strftime(datetime.strptime(defaults['CallStart'], '%Y-%m-%d %H:%M:%S'), '%Y%m%d')
                        else:
                            attachment[0] += '_%s' % datetime.now()
                        attachment[0] += '.pdf'
                    attachment = tuple(attachment)
                    defaults['description'] += '\nNEU: ' + str(attachment)    '''
                        
                        
        defaults.update(custom_values)
        return super(ama_website_crm, self).message_new(cr, uid, msg, custom_values=defaults, context=context)
        
class ama_crm_lead2opportunity_partner(models.TransientModel):
    _inherit = ['crm.lead2opportunity.partner']
    
    def default_get(self, cr, uid, fields, context=None):
        lead_obj = self.pool.get('crm.lead')

        res = super(ama_crm_lead2opportunity_partner, self).default_get(cr, uid, fields, context=context)
        if context.get('active_id'):
            tomerge = [int(context['active_id'])]

            partner_id = res.get('partner_id')
            lead = lead_obj.browse(cr, uid, int(context['active_id']), context=context)
            email = lead.partner_id and lead.partner_id.email or lead.email_from

            tomerge.extend(self._get_duplicated_leads(cr, uid, partner_id, email, include_lost=True, context=context))
            tomerge = list(set(tomerge))

            if 'action' in fields and not res.get('action'):
                res.update({'action' : partner_id and 'exist' or 'create'})
            if 'partner_id' in fields:
                res.update({'partner_id' : partner_id})
            if 'name' in fields:
                res.update({'name' : 'convert'})
            if 'opportunity_ids' in fields and len(tomerge) >= 2:
                res.update({'opportunity_ids': tomerge})
            if lead.user_id:
                res.update({'user_id': lead.user_id.id})
            if lead.section_id:
                res.update({'section_id': lead.section_id.id})
        return res
        
class ama_mail_thread(models.Model):
    _inherit = ['mail.thread']

    def message_parse(self, cr, uid, message, save_original=False, context=None):
        """Parses a string or email.message.Message representing an
           RFC-2822 email, and returns a generic dict holding the
           message details.

           :param message: the message to parse
           :type message: email.message.Message | string | unicode
           :param bool save_original: whether the returned dict
               should include an ``original`` attachment containing
               the source of the message
           :rtype: dict
           :return: A dict with the following structure, where each
                    field may not be present if missing in original
                    message::

                    { 'message_id': msg_id,
                      'subject': subject,
                      'from': from,
                      'to': to,
                      'cc': cc,
                      'body': unified_body,
                      'attachments': [('file1', 'bytes'),
                                      ('file2', 'bytes')}
                    }
        """
        msg_dict = {
            'type': 'email',
        }
        if not isinstance(message, Message):
            if isinstance(message, unicode):
                # Warning: message_from_string doesn't always work correctly on unicode,
                # we must use utf-8 strings here :-(
                message = message.encode('utf-8')
            message = email.message_from_string(message)

        message_id = message['message-id']
        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = "<%s@localhost>" % time.time()
            _logger.debug('Parsing Message without message-id, generating a random one: %s', message_id)
        msg_dict['message_id'] = message_id

        if message.get('Subject'):
            msg_dict['subject'] = decode(message.get('Subject'))

        # Envelope fields not stored in mail.message but made available for message_new()
        msg_dict['from'] = decode(message.get('from'))
        msg_dict['to'] = decode(message.get('to'))
        msg_dict['cc'] = decode(message.get('cc'))
        msg_dict['email_from'] = decode(message.get('from'))
        partner_ids = self._message_find_partners(cr, uid, message, ['To', 'Cc'], context=context)
        msg_dict['partner_ids'] = [(4, partner_id) for partner_id in partner_ids]

        if message.get('Date'):
            try:
                date_hdr = decode(message.get('Date'))
                parsed_date = dateutil.parser.parse(date_hdr, fuzzy=True)
                if parsed_date.utcoffset() is None:
                    # naive datetime, so we arbitrarily decide to make it
                    # UTC, there's no better choice. Should not happen,
                    # as RFC2822 requires timezone offset in Date headers.
                    stored_date = parsed_date.replace(tzinfo=pytz.utc)
                else:
                    stored_date = parsed_date.astimezone(tz=pytz.utc)
            except Exception:
                _logger.warning('Failed to parse Date header %r in incoming mail '
                                'with message-id %r, assuming current date/time.',
                                message.get('Date'), message_id)
                stored_date = datetime.datetime.now()
            msg_dict['date'] = stored_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)

        if message.get('In-Reply-To'):
            parent_ids = self.pool.get('mail.message').search(cr, uid, [('message_id', '=', decode(message['In-Reply-To'].strip()))])
            if parent_ids:
                msg_dict['parent_id'] = parent_ids[0]

        if message.get('References') and 'parent_id' not in msg_dict:
            msg_list =  mail_header_msgid_re.findall(decode(message['References']))
            parent_ids = self.pool.get('mail.message').search(cr, uid, [('message_id', 'in', [x.strip() for x in msg_list])])
            if parent_ids:
                msg_dict['parent_id'] = parent_ids[0]

        msg_dict['body'], msg_dict['attachments'] = self._message_extract_payload(message, save_original=save_original)
        
        #need to check why old name stays and why parameter files with date
        '''if msg_dict['attachments']:
            if msg_dict['subject'] and msg_dict['subject'].startswith('Fax an'):
                for attachment in msg_dict['attachments']:
                    attachment = list(attachment)
                    if attachment[0]:
                        # if msg_dict['date']:
                        #     attachment[0] = 'Fax_%s_%s' % datetime.datetime.strftime(datetime.datetime.strptime(msg_dict['date'], '%Y-%m-%d %H:%M:%S'), '%Y%m%d'), attachment[0]
                        # else:
                            attachment[0] = 'Fax_%s' % attachment[0]
                    attachment = tuple(attachment)'''
        return msg_dict


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
            
class ama_attachment_partner(models.Model):
    _inherit = ['res.partner']
    
    attachments = fields.One2many('ir.attachment', 'partner_id')

class ama_cli(models.Model):
    _name = 'ama.cli'
    
    cli = fields.Char('Agent ID')
    name = fields.Char('Agent Name')

