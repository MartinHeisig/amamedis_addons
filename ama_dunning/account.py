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
        # assert len(self) == 1, 'This option should only be used for a single id at a time.'
        # template = self.env.ref(use_template, False)
        template = False
        if self.section_id:
            if self.reminder_level == 'ze3' and self.section_id.ze3_email:
                template = self.section_id.ze3_email
                self.reminder_sent_ze3 = True
            if self.reminder_level == 'ze2' and self.section_id.ze2_email:
                template = self.section_id.ze2_email
                self.reminder_sent_ze2 = True
            if self.reminder_level == 'ze1' and self.section_id.ze1_email:
                template = self.section_id.ze1_email
                self.reminder_sent_ze1 = True
            
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        # _logger.info(str(template.user_signature))
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
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
    
    @api.multi
    def _send_reminder(self):
        self.ensure_one()
        email_act = self.action_reminder_sent()
        if email_act and email_act.get('context'):
            composer_obj = self.env['mail.compose.message']
            composer_values = {}
            email_ctx = email_act['context']
            template_values = [
                email_ctx.get('default_template_id'),
                email_ctx.get('default_composition_mode'),
                email_ctx.get('default_model'),
                email_ctx.get('default_res_id'),
            ]
            composer_values.update(composer_obj.onchange_template_id(*template_values).get('value', {}))
            for key in ['attachment_ids', 'partner_ids']:
                if composer_values.get(key):
                    composer_values[key] = [(6, 0, composer_values[key])]
            composer_id = composer_obj.create(composer_values, context=email_ctx)
            # _logger.info(str(composer_id.author_id))
            _logger.info(str(composer_id.model))
            # _logger.info(str(composer_id.template_id.user_signature))
            composer_id.author_id = self.user_id.partner_id.id
            # composer_id.is_log = True
            # _logger.info(str(composer_id.author_id))
            # _logger.info(str(composer_id.is_log))
            composer_id.send_mail()
            
            
    @api.model
    def _set_reminder_level(self):
        ids = self.search([('state', '=', 'open')])
        
        for record in ids:
            if record.date_due2 and record.section_id:
                date_diff = date.today() - datetime.strptime(record.date_due2, '%Y-%m-%d').date()
                email_act = False
                if date_diff.days > record.section_id.ze3_days:
                    record.reminder_level = 'ze3'
                    # automatic only works if all of this activated
                    #       - no email send before
                    #       - automatism activated
                    #       - payment-term is set to automatism
                    #       - invoice per email checked in partner form
                    if not record.reminder_sent_ze3 and record.reminder_auto and record.payment_term.is_remindable and record.partner_id.invoice_email:
                        record._send_reminder()
                        # record.reminder_sent_ze3 = True
                        # email_act = record.action_reminder_sent('ama_dunning.email_template_invoice_reminder_third')
                elif date_diff.days > record.section_id.ze2_days:
                    record.reminder_level = 'ze2'
                    if not record.reminder_sent_ze2 and record.reminder_auto and record.payment_term.is_remindable and record.partner_id.invoice_email:
                        record._send_reminder()
                        # record.reminder_sent_ze2 = True
                        # email_act = record.action_reminder_sent('ama_dunning.email_template_invoice_reminder_second')
                elif date_diff.days > record.section_id.ze1_days:
                    record.reminder_level = 'ze1'
                    if not record.reminder_sent_ze1 and record.reminder_auto and record.payment_term.is_remindable and record.partner_id.invoice_email:
                        record._send_reminder()
                        # record.reminder_sent_ze1 = True
                        # email_act = record.action_reminder_sent('ama_dunning.email_template_invoice_reminder_first')
                        
    
    @api.multi
    @api.depends('date_due','section_id')
    def _compute_due_ze1(self):
        for record in self:
            if record.date_due and record.section_id and record.section_id.ze1_days and record.section_id.ze1_days_due:
                record.reminder_due_date_ze1 = datetime.strptime(record.date_due, '%Y-%m-%d') + timedelta(days = record.section_id.ze1_days + record.section_id.ze1_days_due)
        
    @api.multi
    @api.depends('date_due','section_id')
    def _compute_due_ze2(self):
        for record in self:
            if record.date_due and record.section_id and record.section_id.ze2_days and record.section_id.ze2_days_due:
                record.reminder_due_date_ze2 = datetime.strptime(record.date_due, '%Y-%m-%d') + timedelta(days = record.section_id.ze2_days + record.section_id.ze2_days_due)
        
    @api.multi
    @api.depends('date_due','section_id')
    def _compute_due_ze3(self):
        for record in self:
            if record.date_due and record.section_id and record.section_id.ze3_days and record.section_id.ze3_days_due:
                record.reminder_due_date_ze3 = datetime.strptime(record.date_due, '%Y-%m-%d') + timedelta(days = record.section_id.ze3_days + record.section_id.ze3_days_due)
        
                
    
    date_due2 = fields.Date(string='Due Date 2')
    reminder_level = fields.Selection([('ze1', 'Erste Zahlungserinnerung'),('ze2', 'Zweite Zahlungserinnerung'),('ze3', 'Dritte Zahlungserinnerung')], string='Zahlungserinnerungsstufe')
    reminder_sent = fields.Boolean('Zahlungserinnerung versendet', default=False, compute='_compute_sent', help='Markiert ob die Zahlungserinnerung fuer das aktuelle Level versendet wurde', store=True)
    reminder_sent_ze1 = fields.Boolean('Erste Zahlungserinnerung versendet', default=False)
    reminder_sent_ze2 = fields.Boolean('Zweite Zahlungserinnerung versendet', default=False)
    reminder_sent_ze3 = fields.Boolean('Dritte Zahlungserinnerung versendet', default=False)
    reminder_due_date_ze1 = fields.Date(string='Fälligkeit erste Zahlungserinnerung', compute='_compute_due_ze1')
    reminder_due_date_ze2 = fields.Date(string='Fälligkeit zweite Zahlungserinnerung', compute='_compute_due_ze2')
    reminder_due_date_ze3 = fields.Date(string='Fälligkeit dritte Zahlungserinnerung', compute='_compute_due_ze3')
    reminder_auto = fields.Boolean('Zahlungserinnerungen aktiv', default=True)
    
    
class ama_dun_sales_team(models.Model):
    _inherit = 'crm.case.section'
    
    ze1_days = fields.Integer(string='Tage', help='Tage nach Faelligkeit, an dem die Erinnerung verschickt wird')
    ze1_days_due = fields.Integer(string='neue Frist', help='Frist in Tagen fuer die Zahlungsaufforderung')
    ze1_email = fields.Many2one('email.template', domain=[('model', '=', 'account.invoice')], string='Vorlage', help='E-Mail-Vorlage die verwendet werden soll')
    ze2_days = fields.Integer(string='Tage', help='Tage nach Faelligkeit, an dem die Erinnerung verschickt wird')
    ze2_days_due = fields.Integer(string='neue Frist', help='Frist in Tagen fuer die Zahlungsaufforderung')
    ze2_email = fields.Many2one('email.template', domain=[('model', '=', 'account.invoice')], string='Vorlage', help='E-Mail-Vorlage die verwendet werden soll')
    ze3_days = fields.Integer(string='Tage', help='Tage nach Faelligkeit, an dem die Erinnerung verschickt wird')
    ze3_days_due = fields.Integer(string='neue Frist', help='Frist in Tagen fuer die Zahlungsaufforderung')
    ze3_email = fields.Many2one('email.template', domain=[('model', '=', 'account.invoice')], string='Vorlage', help='E-Mail-Vorlage die verwendet werden soll')
    