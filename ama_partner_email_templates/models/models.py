# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.osv import osv

class ama_partner_email_templates(models.Model):
    _inherit = 'res.partner'
    
    mail_template_account_invoice = fields.Many2one(comodel_name='email.template', domain="[('model', '=', 'account.invoice')]", ondelete='set null', string='Rechnung')
    mail_template_purchase_order = fields.Many2one(comodel_name='email.template', domain="[('model', '=', 'purchase.order')]", ondelete='set null', string='Bestellung')
    mail_template_sale_order = fields.Many2one(comodel_name='email.template', domain="[('model', '=', 'sale.order')]", ondelete='set null', string='Angebot/Auftrag')
    mail_template_stock_picking = fields.Many2one(comodel_name='email.template', domain="[('model', '=', 'stock.picking')]", ondelete='set null', string='Lieferschein')

    
class ama_purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    def wkf_send_rfq(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        if not context:
            context= {}
        ir_model_data = self.pool.get('ir.model.data')
        try:
            if context.get('send_rfq', False):
                template_id = ir_model_data.get_object_reference(cr, uid, 'purchase', 'email_template_edi_purchase')[1]
            else:
                raise osv.except_osv(('self.partner_id'), (self.partner_id)) 
                if self.partner_id.mail_template_purchase_order:
                    template_id = self.partner_id.mail_template_purchase_order.id
                elif self.partner_id.parent_id.mail_template_purchase_order:
                    template_id = self.partner_id.parent_id.mail_template_purchase_order.id
                else:
                    template_id = ir_model_data.get_object_reference(cr, uid, 'purchase', 'email_template_edi_purchase_done')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = dict(context)
        ctx.update({
            'default_model': 'purchase.order',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
    