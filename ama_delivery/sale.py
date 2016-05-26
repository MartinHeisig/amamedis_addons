# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning

import logging

_logger = logging.getLogger(__name__)

class ama_sale_order(models.Model):
    _inherit = ['sale.order']
    
    @api.multi
    @api.onchange('order_line')
    def _validate_autochecks(self):
        for record in self:
            record.auto_sale = record.order_line and any(s.product_id.categ_id.route_ids and s.product_id.categ_id.route_ids[0].auto_sale or not s.product_id.categ_id.route_ids for s in record.order_line) or False
            record.auto_purchase = record.order_line and any(s.product_id.categ_id.route_ids and s.product_id.categ_id.route_ids[0].auto_purchase or not s.product_id.categ_id.route_ids for s in record.order_line) or False
            record.auto_stock = record.order_line and any(s.product_id.categ_id.route_ids and s.product_id.categ_id.route_ids[0].auto_stock or not s.product_id.categ_id.route_ids for s in record.order_line) or False
            record.auto_stock_carrier = record.order_line and any(s.product_id.categ_id.route_ids and s.product_id.categ_id.route_ids[0].auto_stock_carrier or not s.product_id.categ_id.route_ids for s in record.order_line) or False
            record.auto_invoice = record.order_line and any(s.product_id.categ_id.route_ids and s.product_id.categ_id.route_ids[0].auto_invoice or not s.product_id.categ_id.route_ids for s in record.order_line) or False
            
    @api.multi
    @api.depends('carrier_id')
    def _compute_dhl_check(self):
        for record in self:
            if record.carrier_id and record.carrier_id.partner_id.id == 5299:
                record.dhl_check=True
            else:
                record.dhl_check=False
                
    @api.multi
    @api.onchange('carrier_id','partner_shipping_id','partner_id')
    def _validate_dhl_address(self):
        for record in self:
            if record.partner_shipping_id:
                if record.partner_shipping_id.is_company:
                    # delivery contact is a company
                    # get contacts dhl_name1 or build it from contacts name
                    record.dhl_name1 = (record.partner_shipping_id.dhl_name1 and record.partner_shipping_id.dhl_name1.strip()) or (record.partner_shipping_id.name and record.partner_shipping_id.name.strip()[0:30])
                    # get contacts dhl_name2 (no need to get companys first name, its only needed for invoices)
                    record.dhl_name2 = (record.partner_shipping_id.dhl_name2 and record.partner_shipping_id.dhl_name2.strip())
                else:
                    # get contacts dhl_name1 or companys dhl_name1 or get it from companys name
                    record.dhl_name1 = (record.partner_shipping_id.dhl_name1 and record.partner_shipping_id.dhl_name1.strip()) or (record.partner_shipping_id.parent_id and ((record.partner_shipping_id.parent_id.dhl_name1 and record.partner_shipping_id.parent_id.dhl_name1.strip()) or record.partner_shipping_id.parent_id.name.strip()[0:30]))
                    # get it from dhl_name2 or build it from contacts name and first_name
                    record.dhl_name2 = (record.partner_shipping_id.dhl_name2 and record.partner_shipping_id.dhl_name2.strip()) or (len(' '.join([record.partner_shipping_id.first_name or '', record.partner_shipping_id.name or '']).strip()) <= 30 and ' '.join([record.partner_shipping_id.first_name or '', record.partner_shipping_id.name or '']).strip()) or record.partner_shipping_id.name.strip()[0:30]
                if record.partner_shipping_id.is_company or not record.partner_shipping_id.use_parent_address:
                    # delivery contact is a company or uses his own address
                    # get presaved dhl-fields or build them from contacts data
                    record.dhl_streetName = (record.partner_shipping_id.dhl_streetName and record.partner_shipping_id.dhl_streetName.strip()) or (record.partner_shipping_id.street_name and record.partner_shipping_id.street_name.strip()[0:30])
                    record.dhl_streetNumber = (record.partner_shipping_id.dhl_streetNumber and record.partner_shipping_id.dhl_streetNumber.strip()) or (record.partner_shipping_id.street_number and record.partner_shipping_id.street_number.strip()[0:7])
                    record.dhl_zip = (record.partner_shipping_id.dhl_zip and record.partner_shipping_id.dhl_zip.strip()) or (record.partner_shipping_id.zip and record.partner_shipping_id.zip.strip()[0:5])
                    record.dhl_city = (record.partner_shipping_id.dhl_city and record.partner_shipping_id.dhl_city.strip()) or (record.partner_shipping_id.city and record.partner_shipping_id.city.strip()[0:50])
                else:
                    # delivery address is a person and uses companys address
                    # get presaved dhl-fields from
                    record.dhl_streetName = (record.partner_shipping_id.dhl_streetName and record.partner_shipping_id.dhl_streetName.strip()) or (record.partner_shipping_id.parent_id and ((record.partner_shipping_id.parent_id.dhl_streetName and record.partner_shipping_id.parent_id.dhl_streetName.strip()[0:30]) or (record.partner_shipping_id.parent_id.street_name and record.partner_shipping_id.parent_id.street_name.strip()[0:30])))
                    record.dhl_streetNumber = (record.partner_shipping_id.dhl_streetNumber and record.partner_shipping_id.dhl_streetNumber.strip()) or (record.partner_shipping_id.parent_id and ((record.partner_shipping_id.parent_id.dhl_streetNumber and record.partner_shipping_id.parent_id.dhl_streetNumber.strip()[0:7]) or (record.partner_shipping_id.parent_id.street_number and record.partner_shipping_id.parent_id.street_number.strip()[0:7])))
                    record.dhl_zip = (record.partner_shipping_id.dhl_zip and record.partner_shipping_id.dhl_zip.strip()) or (record.partner_shipping_id.parent_id and ((record.partner_shipping_id.parent_id.dhl_zip and record.partner_shipping_id.parent_id.dhl_zip.strip()[0:5]) or (record.partner_shipping_id.parent_id.zip and record.partner_shipping_id.parent_id.zip.strip()[0:5])))
                    record.dhl_city = (record.partner_shipping_id.dhl_city and record.partner_shipping_id.dhl_city.strip()) or (record.partner_shipping_id.parent_id and ((record.partner_shipping_id.parent_id.dhl_city and record.partner_shipping_id.parent_id.dhl_city.strip()[0:50]) or (record.partner_shipping_id.parent_id.city and record.partner_shipping_id.parent_id.city.strip()[0:50])))
                record.dhl_phone = (record.partner_shipping_id.dhl_phone and record.partner_shipping_id.dhl_phone.strip()) or (record.partner_shipping_id.phone and record.partner_shipping_id.phone.strip()[0:20])
                record.dhl_email = (record.partner_shipping_id.dhl_email and record.partner_shipping_id.dhl_email.strip()) or (record.partner_shipping_id.email and record.partner_shipping_id.email.strip()[0:30])
    
    auto_sale = fields.Boolean(string='Auto E-Mail Auftragsbestaetigung', help='Automatischer Versand E-Mail Auftragsbestaetigung', default=False)
    auto_purchase = fields.Boolean(string='Auto Annahme Bestellung', help='Automatische Bestaetigung des ERSTEN vorkalkulierten Lieferantenangebots', default=False)
    auto_stock = fields.Boolean(string='Auto Abwicklung Lieferung', help='Automatische Initiierung der Lieferung durch Versand E-Mail Lieferschein an Lager/Lieferant', default=False)
    auto_stock_carrier = fields.Boolean(string='Auto Bestellung Logistiker', help='Automatische Bestellung der Paketlabels beim verknüpften Logistiker')
    auto_invoice = fields.Boolean(string='Auto E-Mail Rechnung', help='Automatische Rechnungserstellung und Versendung nach Lieferung', default=False)
    
    dhl_check = fields.Boolean(string='Lieferant ist DHL', compute=_compute_dhl_check, default=False)
    dhl_name1 = fields.Char('name1', related='partner_shipping_id.dhl_name1')
    dhl_name2 = fields.Char('name2', related='partner_shipping_id.dhl_name2')
    dhl_streetName = fields.Char('streetName', related='partner_shipping_id.dhl_streetName')
    dhl_streetName_parent = fields.Char('streetName', related='partner_shipping_id.parent_id.dhl_streetName')
    dhl_streetNumber = fields.Char('streetNumber', related='partner_shipping_id.dhl_streetNumber')
    dhl_streetNumber_parent = fields.Char('streetNumber', related='partner_shipping_id.parent_id.dhl_streetNumber')
    dhl_zip = fields.Char('zip', related='partner_shipping_id.dhl_zip')
    dhl_zip_parent = fields.Char('zip', related='partner_shipping_id.parent_id.dhl_zip')
    dhl_city = fields.Char('city', related='partner_shipping_id.dhl_city')
    dhl_city_parent = fields.Char('city', related='partner_shipping_id.parent_id.dhl_city')
    dhl_phone = fields.Char('phone', related='partner_shipping_id.dhl_phone')
    dhl_email = fields.Char('email', related='partner_shipping_id.dhl_email')
    
    del_is_company = fields.Boolean(related='partner_shipping_id.is_company', readonly=True)
    del_use_parent_address = fields.Boolean(related='partner_shipping_id.use_parent_address', readonly=True)
    del_name1_company = fields.Char(related='partner_shipping_id.name', readonly=True)
    del_name1_person = fields.Char(related='partner_shipping_id.parent_id.name', readonly=True)
    del_name2_company = fields.Char(related='partner_shipping_id.first_name', readonly=True)
    del_name2_person_first_name = fields.Char(related='partner_shipping_id.first_name', readonly=True)
    del_name2_person_name = fields.Char(related='partner_shipping_id.name', readonly=True)
    del_streetName = fields.Char(related='partner_shipping_id.street_name', readonly=True)
    del_streetNumber = fields.Char(related='partner_shipping_id.street_number', readonly=True)
    del_zip = fields.Char(related='partner_shipping_id.zip', readonly=True)
    del_city = fields.Char(related='partner_shipping_id.city', readonly=True)
    del_phone = fields.Char(related='partner_shipping_id.phone', readonly=True)
    del_email = fields.Char(related='partner_shipping_id.email', readonly=True)
    
    @api.multi
    def action_handle_order(self, context=None):
        for record in self:
            # log_text = 'Angebot ' + record.name + ' wurde bestaetigt mit folgenden Parametern: \n'
            # _logger.info(log_text)
            
            if not record.partner_id or not record.partner_invoice_id or not record.partner_shipping_id:
                raise except_orm('Fehler','Es wurde kein Kunde, Rechnungsadresse oder Lieferadresse ausgewählt')
            
            if record.dhl_check:
                if not record.dhl_name1:
                    if record.dhl_name2:
                        record.dhl_name1 = record.dhl_name2
                        record.dhl_name2 = ''
                    else:
                         raise except_orm('Fehler DHL-Daten','Es wurde kein Empfängername bei den DHL-formatierten Daten angegeben')
                if record.del_is_company:
                    if not record.dhl_streetName:
                        raise except_orm('Fehler DHL-Daten','Es wurde kein Strassenname bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_streetNumber:
                        raise except_orm('Fehler DHL-Daten','Es wurde keine Hausnummer bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_zip:
                        raise except_orm('Fehler DHL-Daten','Es wurde keine Postleitzahl bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_city:
                        raise except_orm('Fehler DHL-Daten','Es wurde kein Ort bei den DHL-formatierten Daten angegeben')
                if not record.del_is_company:
                    if not record.dhl_streetName_parent:
                        raise except_orm('Fehler DHL-Daten','Es wurde kein Strassenname bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_streetNumber_parent:
                        raise except_orm('Fehler DHL-Daten','Es wurde keine Hausnummer bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_zip_parent:
                        raise except_orm('Fehler DHL-Daten','Es wurde keine Postleitzahl bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_city_parent:
                        raise except_orm('Fehler DHL-Daten','Es wurde kein Ort bei den DHL-formatierten Daten angegeben')
                if not record.dhl_phone and not record.dhl_email:
                    raise except_orm('Fehler DHL-Daten','Es wurde weder eine Kontakttelefonnummer, noch eine Kontaktemail bei den DHL-formatierten Daten angegeben. Mindestens eins der beiden Felder muss ausgefüllt werden')
            
            record.action_button_confirm()
            
            if record.auto_sale:
                email_act = record.action_quotation_send()
                if email_act and email_act.get('context'):
                    composer_obj = self.env['mail.compose.message']
                    composer_values = {}
                    email_ctx = email_act['context']
                    template_values = [
                        email_ctx.get('default_template_id'),
                        email_ctx.get('default_composition_mode'),
                        email_ctx.get('default_model'),
                        email_ctx.get('default_res_id'),
                        # email_ctx.get('default_email_from'),
                    ]
                    composer_values.update(composer_obj.onchange_template_id(*template_values).get('value', {}))
                    # composer_values.update(composer_obj.onchange_template_id(cr, uid, None, *template_values, context=context).get('value', {}))
                    # if not composer_values.get('email_from'):
                        # composer_values['email_from'] = 'heisig@amamedis.de'
                        # composer_values['email_from'] = self.section_id.email_from
                        # composer_values['email_from'] = self.browse(cr, uid, order_id, context=context).company_id.email
                    for key in ['attachment_ids', 'partner_ids']:
                        if composer_values.get(key):
                            composer_values[key] = [(6, 0, composer_values[key])]
                    composer_id = composer_obj.create(composer_values, context=email_ctx)
                    composer_id.send_mail()
            
            po_ids = False
            if record.auto_purchase:
                po_ids = self.env['purchase.order'].search([('origin', '=', record.name)])
                for po in po_ids:
                    if po.order_line and po.order_line[0].product_id.categ_id.route_ids and po.order_line[0].product_id.categ_id.route_ids[0].auto_purchase:
                        po.signal_workflow('purchase_confirm')
            
            if record.auto_stock:
                sp_ids = self.env['stock.picking'].search([('origin', '=', record.name)])
                for sp in sp_ids:
                    sp.force_assign()
                if po_ids:
                    sp_ids = self.env['stock.picking'].search(['|',('origin', '=', record.name),('origin', '=', po_ids.name)])
                for sp in sp_ids:
                    # _logger.info(sp.name + ' ' + sp.origin)
                    sp.auto_stock_carrier = record.auto_stock_carrier and sp.move_lines and sp.move_lines[0] and sp.move_lines.product_id.categ_id.route_ids and sp.move_lines.product_id.categ_id.route_ids[0].auto_stock_carrier
                    ids = sp.id
                    if not isinstance(ids, list): ids = [ids]
                    ctx = self.env.context.copy()
                    # _logger.info(self._name + ' ' + record._name + ' ' + sp._name)
                    ctx.update({
                        'active_model': sp._name,
                        'active_ids': ids,
                        'active_id': ids and ids[0] or False
                        })
                    sp_transfer = self.env['stock.transfer_details'].with_context(ctx).create({'picking_id': ids and ids[0] or False})
                    
                    sp_transfer.do_detailed_transfer()


class ama_rq_sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    release_quantity_value = fields.Float('Abrufmenge', help="Anzahl der Produkte für einzelnen Lagerabrufe in der gleichen Einheit, wie die Standardmengeneinheit.")
    release_quantity_check = fields.Boolean('Abrufmenge aktivieren', help="Nur wenn dieser Schalter gesetzt ist, wird die Abrufmenge geliefert, sonst die komplette Bestellmenge.")
    
                
class ama_rq_procurement_order(models.Model):
    _inherit = 'procurement.order'

    '''release_quantity = fields.Float('Abrufmenge',
      help="Anzahl der Produkte für einzelnen Lagerabrufe in der gleichen "
           "Einheit, wie die Standardmengeneinheit.")'''
           
    @api.v7
    def _run_move_create(self, cr, uid, procurement, context=None):
        vals = super(ama_rq_procurement_order, self)._run_move_create(cr, uid, procurement, context)
        vals.update({
            'release_quantity_value': procurement.sale_line_id and procurement.sale_line_id.release_quantity_value,
            'release_quantity_check': procurement.sale_line_id and procurement.sale_line_id.release_quantity_check
            })
        return vals
                    