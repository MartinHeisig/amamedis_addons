# -*- coding: utf-8 -*-
from openerp import http

# class AmaPartnerEmailTemplates(http.Controller):
#     @http.route('/ama_partner_email_templates/ama_partner_email_templates/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ama_partner_email_templates/ama_partner_email_templates/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ama_partner_email_templates.listing', {
#             'root': '/ama_partner_email_templates/ama_partner_email_templates',
#             'objects': http.request.env['ama_partner_email_templates.ama_partner_email_templates'].search([]),
#         })

#     @http.route('/ama_partner_email_templates/ama_partner_email_templates/objects/<model("ama_partner_email_templates.ama_partner_email_templates"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ama_partner_email_templates.object', {
#             'object': obj
#         })