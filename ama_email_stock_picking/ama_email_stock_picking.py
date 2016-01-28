# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning

import openerp.tools.mail as mail

class ama_partner_email_templates(models.Model):
    _inherit = 'res.partner'
    
    # mail_template_account_invoice = fields.Many2one(comodel_name='email.template', domain="[('model', '=', 'account.invoice')]", ondelete='set null', string='Rechnung')
    # mail_template_purchase_order = fields.Many2one(comodel_name='email.template', domain="[('model', '=', 'purchase.order')]", ondelete='set null', string='Bestellung')
    # mail_template_sale_order = fields.Many2one(comodel_name='email.template', domain="[('model', '=', 'sale.order')]", ondelete='set null', string='Angebot/Auftrag')
    mail_template_stock_picking = fields.Many2one(comodel_name='email.template', domain="[('model', '=', 'stock.picking')]", ondelete='set null', string='Lieferschein')

class ama_email_stock_picking(models.Model):
    _inherit = ['stock.picking']
    
    def action_delivery_note_send(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        dn = self.pool.get('stock.picking').browse(cr, uid, ids[0])
        if dn.picking_type_id and dn.picking_type_id.id == ir_model_data.get_object_reference(cr, uid, 'stock_dropshipping', 'picking_type_dropship')[1]:
            src_partner = dn.partner_id
        else:
            src_partner = dn.picking_type_id.default_location_src_id.partner_id
        if src_partner and self.pool.get('res.partner').browse(cr, uid, src_partner.id).mail_template_stock_picking:
            template_id = self.pool.get('res.partner').browse(cr, uid, src_partner.id).mail_template_stock_picking.id
        else:
            try:
                template_id = ir_model_data.get_object_reference(cr, uid, 'ama_email_stock_picking', 'email_template_stock_picking_default')[1]
            except ValueError:
                template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = dict()
        ctx.update({
            'default_model': 'stock.picking',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
'''       
class ama_mail_compose_message(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    # res_attachment_ids = fields.Many2one('ir.attachment', 'Odoo Anhänge', domain=[('res_model','=',result['model']),('res_id','=',result['res_id'])])
    # res_attachment_ids = fields.Many2many('ir.attachment', 'mail_compose_message_ir_attachments_rel', 'wizard_id', 'attachment_id', 'Attachments', domain=[('res_model','=',model),('res_id','=',res_id)])
    # res_attachment_ids = fields.Many2many('ir.attachment', 'mail_compose_message_ir_attachments_rel', 'wizard_id', 'attachment_id', 'Attachments',)
    # res_attachment_ids = fields.Many2one('ir.attachment', 'Odoo Anhang')
    
    @api.multi
    def add_res_attachment(self, context={}):
        for record in self:
            if context.get('att_id'):
                record.attachment_ids.append(self.env['ir.attachment'].browse(context.get('att_id')))
        return
'''