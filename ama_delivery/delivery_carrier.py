# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning

import logging

_logger = logging.getLogger(__name__)

class delivery_carrier_ext(models.Model):
    _inherit = 'delivery.carrier'
    
    res_model = fields.Many2one('ir.model', ondelete='restrict', string='spezielles Model')
    product = fields.Char('Produkt-ID')
    procedure = fields.Char('Verfahren')
    #accountNumber_test = fields.Char('Abrechnungsnummer Sandbox')
