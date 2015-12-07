# -*- coding: utf-8 -*-
from openerp import http

from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.tools.translate import _
from openerp.osv import osv

import pytz

import datetime
import urllib


class AmaWebsiteCrm(http.Controller):
    
    def create_lead(self, request, values, kwargs):
        """ Allow to be overrided """
        cr, context = request.cr, request.context
        return request.registry['crm.lead'].create(cr, SUPERUSER_ID, values, context=dict(context, mail_create_nosubscribe=True))

    @http.route(['/crm/createlead'], type='http', auth="public", website=True)
    def contactus(self, **kwargs):
        def dict_to_str(title, dictvar):
            ret = "\n\n%s" % title
            for field in dictvar:
                ret += "\n%s" % field
            return ret

        _TECHNICAL = ['show_info', 'view_from', 'view_callback']  # Only use for behavior, don't stock it
        _BLACKLIST = ['id', 'create_uid', 'create_date', 'write_uid', 'write_date', 'user_id', 'active']  # Allow in description
        _REQUIRED = []  # Could be improved including required from model

        post_description = []  # Info to add after the message
        error_description = []
        values = {}

        values['medium_id'] = request.registry['ir.model.data'].xmlid_to_res_id(request.cr, SUPERUSER_ID, 'crm.crm_medium_phone')
        # values['section_id'] = request.registry['ir.model.data'].xmlid_to_res_id(request.cr, SUPERUSER_ID, 'website.salesteam_website_sales')

        for field_name, field_value in kwargs.items():
            if field_name in request.registry['crm.lead']._fields and field_name not in _BLACKLIST:
                if field_name in ['CallID', 'ACDGroup'] and not field_value.isdigit():
                    error_description.append("%s: %s" % (field_name, field_value))
                else:
                    values[field_name] = field_value
            elif field_name not in _TECHNICAL:  # allow to add some free fields or blacklisted field like ID
                post_description.append("%s: %s" % (field_name, field_value))

        if values.get("CLI"):
            values["name"] = 'Call from ' + values.get("CLI")
        elif values.get("CallID"):
            values["name"] = 'CallID: ' + values.get("CallID")
        else:
            values["name"] = "Call to Callcenter"
                
        values['description'] = "Automatically generated from phone call"
        # description is required, so it is always already initialized
        if error_description:
            values['description'] += dict_to_str(_("Datatype Mismatch: "), error_description)
        if post_description:
            values['description'] += dict_to_str(_("Custom Fields: "), post_description)

        lead_id = self.create_lead(request, dict(values, user_id=False), kwargs)
        values.update(lead_id=lead_id)
        
        lead = request.registry['crm.lead'].browse(request.cr, SUPERUSER_ID, lead_id)
        cli = lead.CLI
        if cli:
            lead.name = "Call from " + cli
            i = 0
            partner_ids = False
            partner = False
            
            '''
            TODO: CallStart wird irgendwo um eine Stunde erhöht, sie Interessent Diekmann Fr 4.12. 17:28
            http://85.232.6.132/web?debug=#id=1633&view_type=form&model=crm.lead&menu_id=275&action=334
            
            erzeugt durch:
            2015-12-04 16:28:54,656 26051 INFO amamedis2 werkzeug: 127.0.0.1 - - [04/Dec/2015 16:28:54] "GET /crm/updatelead?CallID=928621243&AgentSec=17&ACDGroup=76331&DestCLI=51351&DDI2=88&CLI=00493411286310&CallID2=928621244&CallID3=0&CallStart=12%2F04%2F2015%2017%3A28%3A17&TotalSec=22&DialoutStart=0&DialoutSec=0&DialoutDest=0& HTTP/1.0" 204 -

            '''
            
            while not partner_ids and i<3:
                partner_ids = request.registry['res.partner'].search(request.cr, SUPERUSER_ID, ['|',('phone', 'like', cli[:len(cli)-i]),'|',('mobile', 'like', cli[:len(cli)-i]),('fax', 'like', cli[:len(cli)-i])])
                i += 1
            if partner_ids:
                if len(partner_ids) > 1:
                    # tmp_partner_ids = Set([]) # Achtung: Hier drin sind Partner, nicht deren IDs
                    tmp_partner_ids = set()
                    for tmp_partner_id in partner_ids:
                        tmp_partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, tmp_partner_id)
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
                        lead.description += "\nFehler beim Kontaktsuchen - es gab mehrere Treffer:"
                        for partner in tmp_partner_ids:
                            # partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, id)
                            lead.description += "\nID: " + partner.id + " Name: " + partner.name
                    else:
                        # partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, tmp_partner_ids[0])
                        partner = tmp_partner_ids.pop()
                else:
                    partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, partner_ids[0])
            
            if partner:
                partner_name = (partner.parent_id and partner.parent_id.name) or (partner.is_company and partner.name) or False
                lead.partner_id = partner.id
                lead.partner_name = partner_name
                lead.contact_name = (not partner.is_company and partner.name) or False
                lead.title = partner.title and partner.title.id or False
                lead.street = partner.street
                lead.street2 = partner.street2
                lead.city = partner.city
                lead.state_id = partner.state_id and partner.state_id.id or False
                lead.country_id = partner.country_id and partner.country_id.id or False
                lead.email_from = partner.email
                lead.phone = partner.phone
                lead.mobile = partner.mobile
                lead.fax = partner.fax
                lead.zip = partner.zip
                lead.function = partner.function
                lead.name = partner.name
                lead.section_id = partner.section_id
            else:
                lead.phone = lead.CLI

        # return self.get_contactus_response(values, kwargs)
        
class AmaWebsiteCrm2(http.Controller):       
    @http.route(['/crm/updatelead'], type='http', auth="public", website=True)
    def contactus(self, **kwargs):
        def dict_to_str(title, dictvar):
            ret = "\n\n%s" % title
            for field in dictvar:
                ret += "\n%s" % field
            return ret

        _TECHNICAL = ['show_info', 'view_from', 'view_callback']  # Only use for behavior, don't stock it
        _BLACKLIST = ['id', 'create_uid', 'create_date', 'write_uid', 'write_date', 'user_id', 'active']  # Allow in description
        _REQUIRED = []  # Could be improved including required from model

        error_description = []
        post_description = []  # Info to add after the message
        values = {}
        
        for field_name, field_value in kwargs.items():
            if field_name in request.registry['crm.lead']._fields and field_name not in _BLACKLIST:
                if field_name in ['AgentSec', 'CallID', 'CallID2', 'CallID3', 'TotalSec', 'DialoutSec'] and not field_value.isdigit():
                    error_description.append("%s: %s" % (field_name, field_value))
                else:
                    values[field_name] = field_value
            elif field_name not in _TECHNICAL:  # allow to add some free fields or blacklisted field like ID
                post_description.append("%s: %s" % (field_name, field_value))

        if values.get("CallID") and values['CallID'] != '0':
            lead_ids = request.registry['crm.lead'].search(request.cr, SUPERUSER_ID, [('CallID', '=', values['CallID'])])
            
            for leadID in lead_ids:
                lead = request.registry['crm.lead'].browse(request.cr, SUPERUSER_ID, leadID)
                su = request.registry['res.users'].browse(request.cr, SUPERUSER_ID, SUPERUSER_ID)
                tz = pytz.timezone(su.partner_id.tz) or pytz.utc
                if values.get('DestCLI') and values['DestCLI'] != '0':
                    lead.DestCLI = values['DestCLI']
                if values.get('AgentSec'):
                    lead.AgentSec = values['AgentSec']
                if values.get('CallID2') and values['CallID2'] != '0':
                    lead.CallID2 = values['CallID2']
                if values.get('CallID3') and values['CallID3'] != '0':
                    lead.CallID3 = values['CallID3']
                    if values.get('DialoutStart') and values['DialoutStart'] != '0':
                        try:
                            lead.DialoutStart = tz.localize(datetime.datetime.strptime(urllib.unquote(values['DialoutStart']).decode('utf8'), '%m/%d/%Y %H:%M:%S')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
                        except ValueError, TypeError:
                            error_description.append("%s: %s" % ('DialoutStart', values['DialoutStart']))
                    if values.get('DialoutSec'):
                        lead.DialoutSec = values['DialoutSec']
                    if values.get('DialoutDest') and values['DialoutDest'] != '0':
                        lead.DialoutDest = values['DialoutDest']
                if values.get('CallStart') and values['CallStart'] != '0':
                    try:
                        lead.CallStart = tz.localize(datetime.datetime.strptime(urllib.unquote(values['CallStart']).decode('utf8'), '%m/%d/%Y %H:%M:%S')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError, TypeError:
                        error_description.append("%s: %s" % ('CallStart', values['CallStart']))
                if values.get('TotalSec'):
                    lead.TotalSec = values['TotalSec']
                if error_description:
                    lead.description += dict_to_str(_("Datatype Mismatch (Update): "), error_description)
                if post_description:
                    lead.description += dict_to_str(_("Custom Fields (Update): "), post_description)
 