# -*- coding: utf-8 -*-

from openerp import models, fields, api

class ama_carrier_bag_layout_res_partner(models.Model):
    _inherit = ['res.partner']
    
    layout_ids = fields.Many2many(comodel_name='ama.product.layout.carrier_bag', relation='ama_layout_carrier_bag_res_partner_rel', column1='partner_id', column2='layout_id', string='Tragetaschen-Layouts')
    
class ama_carrier_bag_layout_ir_attachment(models.Model):
    _inherit = ['ir.attachment']
    
    dir_google = fields.Char('Verzeichnis Google-Drive')
    dir_owncloud = fields.Char('Verzeichnis Owncloud')
    
    is_bag_layout = fields.Boolean('Anhang ist Tragetaschenlayout')
    bag_layout_id = fields.Many2one('ama.product.layout.carrier_bag', 'zugehöriges Tragetaschen-Layout')
    bag_layout_size = fields.Many2one('ama.product.attribute.size', 'Größe')
    bag_layout_description = fields.Char('Motivbezeichnung')
    bag_layout_number = fields.Char('Motivnummer')
    
class ama_product_layout_carrier_bag(models.Model):
    _name = 'ama.product.layout.carrier_bag'
    _description = 'Layout Tragetasche'
    
    name = fields.Char('Bezeichnung')
    attachment_ids = fields.One2many('ir.attachment', 'bag_layout_id', 'Layout-Dateien')
    partner_ids = fields.Many2many(comodel_name='res.partner', relation='ama_layout_carrier_bag_res_partner_rel', column1='layout_id', column2='partner_id', string='Partner')
    color_ids = fields.Many2many(comodel_name='ama.product.attribute.color', relation='ama_layout_carrier_bag_attribute_color_rel', column1='layout_id', column2='color_id', string='Farben')
    color_count = fields.Integer('Farbanzahl', compute='_compute_color_count')
    # product_tmpl_id = fields.Many2one('product.template', 'Product Template')
    # value_id = fields.Many2one('product.attribute.value', 'Product Attribute Value', required=True)
    
    @api.multi
    @api.depends('color_ids')
    def _compute_color_count(self):
        for record in self:
            record.color_count = len(record.color_ids)
    
class ama_product_attribute_size(models.Model):
    _name = 'ama.product.attribute.size'
    _description = 'Groesse'
    
    name = fields.Char('Bezeichnung', compute='_compute_name')
    height = fields.Char('Höhe', required=True)
    width = fields.Char('Breite', required=True)
    depth = fields.Char('Tiefe')
    
    @api.multi
    @api.depends('height', 'width', 'depth')
    def _compute_name(self):
        for record in self:
            record.name = ' x '.join(filter(None,[record.height, record.width, record.depth]))

class ama_product_attribute_color(models.Model):
    _name = 'ama.product.attribute.color'
    _description = 'Farbe'
    
    name = fields.Char('Bezeichnung', required=True)
    value = fields.Char('Farbwert')
    
class ama_product_attribute_extra(models.Model):
    _name = 'ama.product.attribute.extra'
    _description = 'Attributserweiterung'
    
    name = fields.Char('Bezeichnung')
    res_model = fields.Many2one('ir.model', 'Model der Attributserweiterung', required=True)
    attribute_id = fields.Many2one('product.attribute', 'Elternattribut', required=True)
    value_extra_ids = fields.One2many('ama.product.attribute.extra.value', 'attribute_extra_id', 'Werte')
    
class ama_product_attribute_extra_value(models.Model):
    _name = 'ama.product.attribute.extra.value'
    _description = 'Attributswerterweiterung'
    
    name = fields.Char('Bezeichnung')
    res_id = fields.Integer('ID des Datensatzes aus dem in der Attributserweiterung hinterlegten Models', required=True)
    attribute_extra_id = fields.Many2one('ama.product.attribute.extra', 'zugehörige Attributserweiterung', required=True)
    attribute_value_ids = fields.Many2many(comodel_name='product.attribute.value', relation='ama_attribute_extra_value_attribute_value_rel', column1='value_extra_id', column2='value_id', string='Elternwerte')
    
class ama_product_attribute(models.Model):
    _inherit = ['product.attribute']
    
    attribute_extra_ids = fields.One2many('ama.product.attribute.extra', 'attribute_id', 'Attributserweiterungen')
    
class ama_product_attribute_value(models.Model):
    _inherit = ['product.attribute.value']
    
    value_extra_ids = fields.Many2many(comodel_name='ama.product.attribute.extra.value', relation='ama_attribute_extra_value_attribute_value_rel', column1='value_id', column2='value_extra_id', string='Werterweiterungen')