# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning

class ama_dun_res_partner(models.Model):
    _inherit = "res.partner"
    
    invoice_email = fields.Boolean('per E-Mail', default=True, help='Rechnungen werden per E-Mail versendet')
    invoice_fax = fields.Boolean('per Fax', default=False, help='Rechnungen werden per Fax versendet')
    invoice_letter = fields.Boolean('per Post', default=False, help='Rechnungen werden per Post versendet')
    