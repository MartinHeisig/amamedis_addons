# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning
from datetime import date, datetime, timedelta

import logging
_logger = logging.getLogger(__name__)


class ama_dun_account_payment_term(models.Model):
    _inherit = "account.payment.term"
    
    is_remindable = fields.Boolean('Automatische Zahlungserinnerungen', default=True, help='Ist der Haken gesetzt, ist das automatische Zahlungserinnerungssystem aktiviert. Dauer und Art wird ueber die Verkaufsteams eingestellt')
    
class ama_dun_account_invoice(models.Model):
    _inherit = "account.invoice"
    
    @api.multi
    @api.depends('reminder_level','reminder_sent_ze1','reminder_sent_ze2','reminder_sent_ze3')
    def _compute_sent(self):
        for record in self:
            if record.reminder_level:
                if record.reminder_level == 'ze1' and record.reminder_sent_ze1:
                    record.reminder_sent = True
                elif record.reminder_level == 'ze2' and record.reminder_sent_ze2:
                    record.reminder_sent = True
                elif record.reminder_level == 'ze3' and record.reminder_sent_ze3:
                    record.reminder_sent = True
                else:
                    record.reminder_sent = False
            else:
                record.reminder_sent = False
                
    @api.multi
    def action_reminder_sent(self):
        self.ensure_one()
        template = False
        section = self.partner_id.is_company and self.partner_id.section_id or self.partner_id.parent_id.section_id
        if section:
            if self.reminder_level == 'ze3' and section.ze3_email:
                template = section.ze3_email
            if self.reminder_level == 'ze2' and section.ze2_email:
                template = section.ze2_email
            if self.reminder_level == 'ze1' and section.ze1_email:
                template = section.ze1_email
            
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
            mark_reminder_as_sent=self.reminder_level,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
            
    @api.model
    def _set_reminder_level(self, days_execute=[]):
        if date.today().isoweekday() in days_execute:
            _logger.info('Ich wollte heute arbeiten aber durfte nicht')
            return
        ids = self.search([('state', '=', 'open'),('type','=','out_invoice')])
        
        for record in ids:
            section = record.partner_id.is_company and record.partner_id.section_id or record.partner_id.parent_id.section_id
            if record.date_due and section:
                date_diff = date.today() - datetime.strptime(record.date_due, '%Y-%m-%d').date()
                email_act = False
                # automatic only works if all of this activated
                #       - no email send before
                #       - automatism activated
                #       - payment-term is set to automatism
                #       - invoice per email checked in partner form
                if date_diff.days >= section.ze3_days:
                    record.reminder_level = 'ze3'
                    if not record.reminder_sent_ze3 and record.reminder_auto and record.payment_term.is_remindable and record.partner_id.invoice_email:
                        try:
                            msg_id = self.env['email.template'].browse(section.ze3_email.id).send_mail(record.id, True, True)
                            if msg_id:
                                record.reminder_sent_ze3 = True
                        except Exception, e:
                            _logger.exception("Failed to send automatic payment reminder email %s: %s" % (record.number, unicode(e)))
                            record.message_post(body=str(e), subtype='mail.mt_comment',)
                elif date_diff.days >= section.ze2_days:
                    record.reminder_level = 'ze2'
                    if not record.reminder_sent_ze2 and record.reminder_auto and record.payment_term.is_remindable and record.partner_id.invoice_email:
                        try:
                            msg_id = self.env['email.template'].browse(section.ze2_email.id).send_mail(record.id, True, True)
                            if msg_id:
                                record.reminder_sent_ze2 = True
                        except Exception, e:
                            _logger.exception("Failed to send automatic payment reminder email %s: %s" % (record.number, unicode(e)))
                            record.message_post(body=str(e), subtype='mail.mt_comment',)
                elif date_diff.days >= section.ze1_days:
                    record.reminder_level = 'ze1'
                    if not record.reminder_sent_ze1 and record.reminder_auto and record.payment_term.is_remindable and record.partner_id.invoice_email:
                        try:
                            msg_id = self.env['email.template'].browse(section.ze1_email.id).send_mail(record.id, True, True)
                            if msg_id:
                                record.reminder_sent_ze1 = True
                        except Exception, e:
                            _logger.exception("Failed to send automatic payment reminder email %s: %s" % (record.number, unicode(e)))
                            record.message_post(body=str(e), subtype='mail.mt_comment',)
                        
                        
    
    @api.multi
    @api.depends('date_due','section_id','partner_id')
    def _compute_due_ze1(self):
        for record in self:
            section = record.partner_id.is_company and record.partner_id.section_id or record.partner_id.parent_id.section_id
            if record.date_due and section and section.ze1_days_due:
                record.reminder_due_date_ze1 = datetime.strptime(record.date_due, '%Y-%m-%d') + timedelta(days = section.ze1_days_due)
        
    @api.multi
    @api.depends('date_due','section_id','partner_id')
    def _compute_due_ze2(self):
        for record in self:
            section = record.partner_id.is_company and record.partner_id.section_id or record.partner_id.parent_id.section_id
            if record.date_due and section and section.ze2_days_due:
                record.reminder_due_date_ze2 = datetime.strptime(record.date_due, '%Y-%m-%d') + timedelta(days = section.ze2_days_due)
        
    @api.multi
    @api.depends('date_due','section_id','partner_id')
    def _compute_due_ze3(self):
        for record in self:
            section = record.partner_id.is_company and record.partner_id.section_id or record.partner_id.parent_id.section_id
            if record.date_due and section and section.ze3_days_due:
                record.reminder_due_date_ze3 = datetime.strptime(record.date_due, '%Y-%m-%d') + timedelta(days = section.ze3_days_due)
        
                
    
    # date_due2 = fields.Date(string='Due Date 2')
    reminder_level = fields.Selection([('ze1', 'Erste'),('ze2', 'Zweite'),('ze3', 'Dritte')], string='Stufe')
    reminder_sent = fields.Boolean('Aktuelle Stufe versendet', default=False, compute='_compute_sent', help='Markiert ob die Zahlungserinnerung fuer die aktuelle Stufe versendet wurde', store=True)
    reminder_sent_ze1 = fields.Boolean('1. Stufe versendet', default=False)
    reminder_sent_ze2 = fields.Boolean('2. Stufe versendet', default=False)
    reminder_sent_ze3 = fields.Boolean('3. Stufe versendet', default=False)
    reminder_due_date_ze1 = fields.Date(string='Neue Fälligkeit 1. Stufe', compute='_compute_due_ze1')
    reminder_due_date_ze2 = fields.Date(string='Neue Fälligkeit 2. Stufe', compute='_compute_due_ze2')
    reminder_due_date_ze3 = fields.Date(string='Neue Fälligkeit 3. Stufe', compute='_compute_due_ze3')
    reminder_auto = fields.Boolean('Automatisch versenden', default=True)
    
    
class ama_dun_sales_team(models.Model):
    _inherit = 'crm.case.section'
    
    ze1_days = fields.Integer(string='Tage', help='Tage nach Faelligkeit, an dem die Erinnerung verschickt wird')
    ze1_days_due = fields.Integer(string='neue Frist', help='Nachfrist nach eigentlicher Frist in Tagen fuer die Zahlungsaufforderung')
    ze1_email = fields.Many2one('email.template', domain=[('model', '=', 'account.invoice')], string='Vorlage', help='E-Mail-Vorlage die verwendet werden soll')
    ze2_days = fields.Integer(string='Tage', help='Tage nach Faelligkeit, an dem die Erinnerung verschickt wird')
    ze2_days_due = fields.Integer(string='neue Frist', help='Nachfrist nach eigentlicher Frist in Tagen fuer die Zahlungsaufforderung')
    ze2_email = fields.Many2one('email.template', domain=[('model', '=', 'account.invoice')], string='Vorlage', help='E-Mail-Vorlage die verwendet werden soll')
    ze3_days = fields.Integer(string='Tage', help='Tage nach Faelligkeit, an dem die Erinnerung verschickt wird')
    ze3_days_due = fields.Integer(string='neue Frist', help='Nachfrist nach eigentlicher Frist in Tagen fuer die Zahlungsaufforderung')
    ze3_email = fields.Many2one('email.template', domain=[('model', '=', 'account.invoice')], string='Vorlage', help='E-Mail-Vorlage die verwendet werden soll')
    
    
class ama_dun_mail_compose_message(models.Model):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self):
        context = self._context
        # _logger.debug('Ich sende: %s' % str(context.get('mark_reminder_as_sent')))
        if context.get('default_model') == 'account.invoice' and \
                context.get('default_res_id') and context.get('mark_reminder_as_sent'):
            invoice = self.env['account.invoice'].browse(context['default_res_id'])
            #invoice = invoice.with_context(mail_post_autofollow=True)
            # _logger.info(str(context['mark_reminder_as_sent']))
            if context['mark_reminder_as_sent'] == 'ze1':
                invoice.write({'reminder_sent_ze1': True})
                # invoice.message_post(body=("Erste Zahlungserinnerung gesendet"))
            elif context['mark_reminder_as_sent'] == 'ze2':
                invoice.write({'reminder_sent_ze2': True})
                # invoice.message_post(body=("Zweite Zahlungserinnerung gesendet"))
            elif context['mark_reminder_as_sent'] == 'ze3':
                invoice.write({'reminder_sent_ze3': True})
                # invoice.message_post(body=("Dritte Zahlungserinnerung gesendet"))
        return super(ama_dun_mail_compose_message, self).send_mail()
    