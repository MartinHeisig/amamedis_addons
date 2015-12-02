# -*- coding: utf-8 -*-
from openerp import http

from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.tools.translate import _


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

        post_file = []  # List of file to add to ir_attachment once we have the ID
        post_description = []  # Info to add after the message
        values = {}

        values['medium_id'] = request.registry['ir.model.data'].xmlid_to_res_id(request.cr, SUPERUSER_ID, 'crm.crm_medium_phone')
        # values['section_id'] = request.registry['ir.model.data'].xmlid_to_res_id(request.cr, SUPERUSER_ID, 'website.salesteam_website_sales')

        for field_name, field_value in kwargs.items():
            if field_name in request.registry['crm.lead']._fields and field_name not in _BLACKLIST:
                values[field_name] = field_value
            elif field_name not in _TECHNICAL:  # allow to add some free fields or blacklisted field like ID
                post_description.append("%s: %s" % (field_name, field_value))

        if values.get("CLI"):
            '''partner_ids = request.registry['res.partner'].search(request.cr, SUPERUSER_ID, [('phone', 'like', values['CLI'])])
            partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, partner_ids)
            if partner and partner[0]:
                values["partner_id"] = partner[0].id
                values["name"] = partner[0].name
            else:'''
            values["name"] = 'Call from ' + values.get("CLI")
        elif values.get("CallID"):
            values["name"] = 'CallID: ' + values.get("CallID")
        else:
            values["name"] = "Call to Callcenter"
                
        # fields validation : Check that required field from model crm_lead exists
        error = set(field for field in _REQUIRED if not values.get(field))

        # need to check where error report has to be sent
        '''if error:
            values = dict(values, error=error, kwargs=kwargs.items())
            return request.website.render(kwargs.get("view_from", "website.contactus"), values)'''

        values['description'] = "Automatically generated from phone call"
        # description is required, so it is always already initialized
        if post_description:
            values['description'] += dict_to_str(_("Custom Fields: "), post_description)

        '''if kwargs.get("show_info"):
            post_description = []
            environ = request.httprequest.headers.environ
            post_description.append("%s: %s" % ("IP", environ.get("REMOTE_ADDR")))
            post_description.append("%s: %s" % ("USER_AGENT", environ.get("HTTP_USER_AGENT")))
            post_description.append("%s: %s" % ("ACCEPT_LANGUAGE", environ.get("HTTP_ACCEPT_LANGUAGE")))
            post_description.append("%s: %s" % ("REFERER", environ.get("HTTP_REFERER")))
            values['description'] += dict_to_str(_("Environ Fields: "), post_description)'''

        lead_id = self.create_lead(request, dict(values, user_id=False), kwargs)
        values.update(lead_id=lead_id)
        
        lead = request.registry['crm.lead'].browse(request.cr, SUPERUSER_ID, lead_id)
        cli = lead.CLI
        if cli:
            lead.name = "Call from " + cli
            i = 0
            partner_ids = False
            while not partner_ids and i<3:
                partner_ids = request.registry['res.partner'].search(request.cr, SUPERUSER_ID, [('phone', 'like', cli[:len(cli)-i])])
                i += 1
            if partner_ids and partner_ids[0]:
                partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, partner_ids[0])
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
                lead.name = partner_name or partner.name
                
        
        # request.registry['crm.lead'].browse(request.cr, SUPERUSER_ID, lead_id)._search_partner()
        
        '''if values['CLI']:
            lead = request.registry['crm.lead'].browse(request.cr, SUPERUSER_ID, lead_id)
            lead.CLI = values['CLI']'''
            
        '''if lead_id:
            for field_value in post_file:
                attachment_value = {
                    'name': field_value.filename,
                    'res_name': field_value.filename,
                    'res_model': 'crm.lead',
                    'res_id': lead_id,
                    'datas': base64.encodestring(field_value.read()),
                    'datas_fname': field_value.filename,
                }
                request.registry['ir.attachment'].create(request.cr, SUPERUSER_ID, attachment_value, context=request.context)'''

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

        post_file = []  # List of file to add to ir_attachment once we have the ID
        post_description = []  # Info to add after the message
        values = {}

        for field_name, field_value in kwargs.items():
            if field_name in request.registry['crm.lead']._fields and field_name not in _BLACKLIST:
                values[field_name] = field_value
            elif field_name not in _TECHNICAL:  # allow to add some free fields or blacklisted field like ID
                post_description.append("%s: %s" % (field_name, field_value))

                
        
            
        if values.get("CallID"):
            lead_ids = request.registry['crm.lead'].search(request.cr, SUPERUSER_ID, [('CallID', '=', values['CallID'])])
            
            for leadID in lead_ids:
                lead = request.registry['crm.lead'].browse(request.cr, SUPERUSER_ID, leadID)
                if values.get('DestCLI'):
                    lead.DestCLI = values['DestCLI']
                if values.get('AgentSec'):
                    lead.AgentSec = values['AgentSec']
                if post_description:
                    lead.description += dict_to_str(_("Custom Fields (Update): "), post_description)
 