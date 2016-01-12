# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning
from openerp.tools.translate import _

import logging


_logger = logging.getLogger(__name__)

class ama_crm_make_sale(models.TransientModel):
    _inherit = ['crm.make.sale']
    
    messageBehavior = fields.Selection([
        ('none', "Nicht verschieben"),
        ('order', "Zum Auftrag verschieben"),
        ('partner', "Zum Partner verschieben"),
    ], default='order', required=True, string='Nachrichten verschieben?')

    attachmentBehavior = fields.Selection([
        ('none', "Nicht verschieben"),
        ('order', "Zum Auftrag verschieben"),
        ('partner', "Zum Partner verschieben"),
    ], default='order', required=True, string='Anhänge verschieben?')

    def makeOrder(self, cr, uid, ids, context=None):
        """
        This function  create Quotation on given case.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm make sales' ids
        @param context: A standard dictionary for contextual values
        @return: Dictionary value of created sales order.
        """
        # update context: if come from phonecall, default state values can make the quote crash lp:1017353
        context = dict(context or {})
        context.pop('default_state', False)        
        
        case_obj = self.pool.get('crm.lead')
        sale_obj = self.pool.get('sale.order')
        partner_obj = self.pool.get('res.partner')
        data = context and context.get('active_ids', []) or []

        for make in self.browse(cr, uid, ids, context=context):
            partner = make.partner_id
            partner_addr = partner_obj.address_get(cr, uid, [partner.id],
                    ['default', 'invoice', 'delivery', 'contact'])
            pricelist = partner.property_product_pricelist.id
            fpos = partner.property_account_position and partner.property_account_position.id or False
            payment_term = partner.property_payment_term and partner.property_payment_term.id or False
            new_ids = []
            for case in case_obj.browse(cr, uid, data, context=context):
                if not partner and case.partner_id:
                    partner = case.partner_id
                    fpos = partner.property_account_position and partner.property_account_position.id or False
                    payment_term = partner.property_payment_term and partner.property_payment_term.id or False
                    partner_addr = partner_obj.address_get(cr, uid, [partner.id],
                            ['default', 'invoice', 'delivery', 'contact'])
                    pricelist = partner.property_product_pricelist.id
                if False in partner_addr.values():
                    raise osv.except_osv(_('Insufficient Data!'), _('No address(es) defined for this customer.'))

                vals = {
                    'origin': _('Opportunity: %s') % str(case.id),
                    'section_id': case.section_id and case.section_id.id or False,
                    'categ_ids': [(6, 0, [categ_id.id for categ_id in case.categ_ids])],
                    'partner_id': partner.id,
                    'pricelist_id': pricelist,
                    'partner_invoice_id': partner_addr['invoice'],
                    'partner_shipping_id': partner_addr['delivery'],
                    'date_order': fields.datetime.now(),
                    'fiscal_position': fpos,
                    'payment_term':payment_term,
                    'note': sale_obj.get_salenote(cr, uid, [case.id], partner.id, context=context),
                }
                if partner.id:
                    vals['user_id'] = partner.user_id and partner.user_id.id or uid
                new_id = sale_obj.create(cr, uid, vals, context=context)
                sale_order = sale_obj.browse(cr, uid, new_id, context=context)
                case_obj.write(cr, uid, [case.id], {'ref': 'sale.order,%s' % new_id})
                new_ids.append(new_id)
                message = _("Opportunity has been <b>converted</b> to the quotation <em>%s</em>.") % (sale_order.name)
                case.message_post(body=message)
                if make.messageBehavior == 'order':
                    message = self.pool.get('mail.message')
                    for history in case.message_ids:
                        if history.type != 'notification':
                            message.write(cr, uid, history.id, {
                                    'res_id': new_id,
                                    'model': 'sale.order',
                                    'subject' : _("Message moved from Lead %s : %s") % (case.id, history.subject)
                            }, context=context)
                if make.messageBehavior == 'partner':
                    message = self.pool.get('mail.message')
                    for history in case.message_ids:
                        if history.type != 'notification':
                            message.write(cr, uid, history.id, {
                                    'res_id': partner.id,
                                    'model': 'res.partner',
                                    'subject' : _("Message moved from Lead %s : %s") % (case.id, history.subject)
                            }, context=context)
                if make.attachmentBehavior == 'order':
                    attach_obj = self.pool.get('ir.attachment')
                    order_attachments = attach_obj.browse(cr, uid, attach_obj.search(cr, uid, [('res_model', '=', 'sale.order'), ('res_id', '=', new_id)], context=context), context=context)

                    #counter of all attachments to move. Used to make sure the name is different for all attachments
                    count = 1
                    attachments = attach_obj.browse(cr, uid, attach_obj.search(cr, uid, [('res_model', '=', 'crm.lead'), ('res_id', '=', case.id)], context=context), context=context)
                    for attachment in attachments:
                        values = {'res_id': new_id, 'res_model': 'sale.order',}
                        '''for attachment_in_saleorder in order_attachments:
                            if attachment.name == attachment_in_saleorder.name:
                                values['name'] = "%s (%s)" % (attachment.name, count,)
                        count+=1'''
                        attachment.write(values)
                    
                if make.attachmentBehavior == 'partner':
                    attach_obj = self.pool.get('ir.attachment')
                    order_attachments = attach_obj.browse(cr, uid, attach_obj.search(cr, uid, [('res_model', '=', 'res.partner'), ('res_id', '=', partner.id)], context=context), context=context)

                    #counter of all attachments to move. Used to make sure the name is different for all attachments
                    count = 1
                    attachments = attach_obj.browse(cr, uid, attach_obj.search(cr, uid, [('res_model', '=', 'crm.lead'), ('res_id', '=', case.id)], context=context), context=context)
                    for attachment in attachments:
                        values = {'res_id': partner.id, 'res_model': 'res.partner',}
                        '''for attachment_in_respartner in order_attachments:
                            if attachment.name == attachment_in_respartner.name:
                                tmpname = attachment.name.rsplit('.', 1)
                                if len(tmpname) > 1:
                                    values['name'] = "%s (%s).%s" % (tmpname[0], count, tmpname[1])
                                else:
                                    values['name'] = "%s (%s)" % (attachment.name, count,)
                        count+=1'''
                        attachment.write(values)
                
            if make.close:
                case_obj.case_mark_won(cr, uid, data, context=context)
            if not new_ids:
                return {'type': 'ir.actions.act_window_close'}
            if len(new_ids)<=1:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name' : _('Quotation'),
                    'res_id': new_ids and new_ids[0]
                }
            else:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'sale.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name' : _('Quotation'),
                    'res_id': new_ids
                }
            return value
