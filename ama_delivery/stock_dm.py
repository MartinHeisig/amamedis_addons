# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning

import logging

_logger = logging.getLogger(__name__)


'''class stock_picking_pu(models.Model):
    _inherit = 'stock.picking'
    #Erweiterung des Lieferscheins

    stock_dm_picking_unit_ids = fields.One2many(comodel_name='stock.dm.picking.unit', inverse_name='stock_picking_id', string="Sendescheine")'''


class stock_dm_picking_unit(models.Model):
    _name = 'stock.dm.picking.unit'
    '''ungebrandete Sendung'''

    name = fields.Char(string='Name', compute='_compute_name', help='Logistiker-Sendungsnummer')
    code = fields.Char(string='Sendungsnummer', help='Sendungsnummer', required=True)
    stock_picking_id = fields.Many2one('stock.picking', ondelete='restrict', string='Lieferschein', help='Lieferschein, zu dem diese Sendung gehoert', required=True)
    order_date = fields.Datetime(string='erstellt am', related='stock_picking_id.date_done')
    delivery_carrier_id = fields.Many2one('delivery.carrier', ondelete='restrict', string='Logistiker', help='Auslieferungsmethode fuer diese Sendung', required=True)
    delivery_carrier_res_model = fields.Many2one('ir.model', string='Datenmodell des Lieferanten', related='delivery_carrier_id.res_model', help='Der Auslieferungsmethode (dem Logistiker) zugewiesenes Datenmodell', store=True, readonly=True)
    delivery_carrier_res_id = fields.Integer(string='ID im Datenmodell des Lieferanten', help='DatensatzID im jeweiligen Modell des Logistikers')
    stock_dm_state_id = fields.Many2one('stock.dm.state', string='Status der Lieferung', compute='_compute_carrier_state', ondelete='restrict', help='Interner Status der Sendung')
    partner_id = fields.Many2one('res.partner', string='Lieferkontakt', related='stock_picking_id.delivery_address_id', help='Lieferkontakt bzw. -adresse der Sendung', store=True, readonly=True)
    
    @api.multi
    @api.depends('code','delivery_carrier_id.name')
    def _compute_name(self):
        for record in self:
            if record.code and record.delivery_carrier_id and record.delivery_carrier_id.name:
                record.name = ' - '.join([record.delivery_carrier_id.name, record.code])
    
    @api.multi
    @api.depends('delivery_carrier_res_model','delivery_carrier_res_id')
    def _compute_carrier_state(self):
        for record in self:
            if record.delivery_carrier_res_model and record.delivery_carrier_res_id and record.delivery_carrier_res_id > 0:
                carrier_picking_unit = self.env[record.delivery_carrier_res_model.model].browse(record.delivery_carrier_res_id)
                if carrier_picking_unit and hasattr(self.env[record.delivery_carrier_res_model.model], "stock_dm_state_id") and carrier_picking_unit.stock_dm_state_id:
                    record.stock_dm_state_id = carrier_picking_unit.stock_dm_state_id
                    
    @api.multi
    def tracking(self):
        for record in self:
            if record.delivery_carrier_res_model and record.delivery_carrier_res_id and record.delivery_carrier_res_id > 0:
                carrier_picking_unit = self.env[record.delivery_carrier_res_model.model].browse(record.delivery_carrier_res_id)
                if carrier_picking_unit:
                    attribute = getattr(self.env[record.delivery_carrier_res_model.model], "tracking", None)
                    if callable(attribute):
                        carrier_picking_unit.tracking()

    @api.multi
    def open_carrier_picking_unit(self):
        for record in self:
            return {
                'name':'Show Logician',
                'view_type':'form',
                'view_mode':'form',
                'res_model':record.delivery_carrier_res_model.model,
                'type':'ir.actions.act_window',
                'res_id':record.delivery_carrier_res_id,
                'domain':[('id','=',record.delivery_carrier_res_id)]
            }

class stock_dm_state(models.Model):
    _name = 'stock.dm.state'
    _order = 'sequence asc'
    '''allgemeiner Lieferstatus'''
    
    name = fields.Char(string="State", compute='_get_name')
    name_en = fields.Char(string="State_en")
    name_de = fields.Char(string="State_de")
    sequence = fields.Integer(string="Sequence")

    @api.multi
    @api.depends('name_en', 'name_de')
    def _get_name(self):
        for record in self:
            if self.env.user.lang == "de_DE":
                record.name = record.name_de
            else:
                record.name = record.name_en
