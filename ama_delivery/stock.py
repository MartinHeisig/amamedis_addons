# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.tools.mail as mail
from openerp.tools.translate import _
from math import ceil
from subprocess import Popen, PIPE

import sys

import urllib
import PyPDF2
import base64
import datetime
import os
import shutil
import errno
import logging

from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds.plugin import MessagePlugin
from suds.wsse import *

import constants_dhl

reload(sys)
sys.setdefaultencoding('iso-8859-1')

_logger = logging.getLogger(__name__)

# logging.basicConfig(level=logging.NOTSET)

logging.getLogger('suds').setLevel(logging.WARNING) #WARNING
logging.getLogger('suds.client').setLevel(logging.DEBUG) #DEBUG
logging.getLogger('suds.transport').setLevel(logging.DEBUG)


class ama_cs_product_template(models.Model):
    _inherit = 'product.template'

    container_size = fields.Float('Gebindegröße', help="Anzahl der Produkte, die in ein Paket passen. Menge wird in der Standardmengeneinheit angegeben.")


class ama_stock_location_route(models.Model):
    _inherit = ['stock.location.route']
    
    # switches which actions should be automated when using this route
    auto_sale = fields.Boolean(string='Auto E-Mail Auftragsbestaetigung', help='Automatischer Versand E-Mail Auftragsbestaetigung', default=False)
    auto_purchase = fields.Boolean(string='Auto Annahme Bestellung', help='Automatische Bestaetigung des ERSTEN vorkalkulierten Lieferantenangebots', default=False)
    auto_stock = fields.Boolean(string='Auto Abwicklung Lieferung', help='Automatische Initiierung der Lieferung durch Versand E-Mail Lieferschein an Lager/Lieferant', default=False)
    auto_stock_carrier = fields.Boolean(string='Auto Bestellung Logistiker', help='Automatische Bestellung der Paketlabels beim verknüpften Logistiker', default=False)
    auto_invoice = fields.Boolean(string='Auto E-Mail Rechnung', help='Automatische Rechnungserstellung und Versendung nach Lieferung', default=False)

class ama_rq_stock_move(models.Model):
    _inherit = 'stock.move'
    
    @api.multi
    @api.onchange('release_quantity_check')
    def _onchange_release_quantity_check(self):
        for record in self:
            if not record.release_quantity_check:
                record.release_quantity_value = record.product_uom_qty
    
    release_quantity_value = fields.Float('Abrufmenge', help="Anzahl der Produkte für einzelnen Lagerabrufe in der gleichen Einheit, wie die Standardmengeneinheit.")
    release_quantity_check = fields.Boolean('Abrufmenge aktivieren', help="Nur wenn dieser Schalter gesetzt ist, wird die Abrufmenge geliefert, sonst die komplette Bestellmenge.")
    release_quantity_input = fields.Float('Abrufmenge', help="Eingabefeld für die Abrufmenge")

    
class ama_del_stock_picking(models.Model):
    _inherit = ['stock.picking']
    _order = 'date desc'
    
    @api.model
    def _first_install(self):
        # method only needed to convert the data from the old moduls to this new one
        # if need of use, check if the module dhl_delivery is added as dependency in __openerp__.py file
        model = self.env['ir.model'].search([('model','=','dhl.delivery')], limit=1)
        if model:
            prod_ids = self.env['product.template'].search([])
            # get the container_size / pieces_per_box
            for pid in prod_ids:
                pid.container_size = pid.pcs_per_box
            
            line_ids = self.env['sale.order.line'].search([('release_quantity','!=',False)])
            for line in line_ids:
                line.release_quantity_check = True
                line.release_quantity_value = line.release_quantity
                
            line_ids = self.env['stock.move'].search([('release_quantity','!=',False)])
            for line in line_ids:
                line.release_quantity_check = True
                line.release_quantity_value = line.release_quantity
                
            self.env['stock.picking'].search([])._get_origin()
            self.env['stock.picking'].search([])._compute_date_done()
                
            dhl_ids = self.env[model.model].search([])
            for id in dhl_ids:
                if id.name and not self.env['stock.dhl.picking.unit'].search([('name','=',id.name)]):
                    # Create new dhl delivery object
                    picking_unit = self.env['stock.dm.picking.unit'].create({
                        'code' : id.name,
                        'stock_picking_id' : id.delivery_order.id,
                        'delivery_carrier_id' : self.env.ref('ama_delivery.dm1').id,
                        #'delivery_carrier_id' : id.delivery_order.carrier_id.id or 1,
                        })
                    dhl_picking_unit = self.env['stock.dhl.picking.unit'].create({
                        'name' : id.name,
                        'stock_dm_picking_unit_id' : picking_unit.id,
                        'ownership' : True,
                        'stock_dm_state_id' : (id.state == 'deleted' and self.env.ref('ama_delivery.dms80').id) or self.env.ref('ama_delivery.dms10').id,
                        #'stock_dm_state_id' : id.state == 'deleted' and self.env['stock.dm.state'].search([('sequence','=','80')], limit=1).id or self.env['stock.dm.state'].search([('sequence','=','10')], limit=1).id,
                        })
                    picking_unit.update({
                        'delivery_carrier_res_id' : dhl_picking_unit.id
                        })
                    _logger.debug('Es wurde folgendes Objekt erzeugt: ' + picking_unit.name)
                                                
    
    @api.multi
    @api.depends('carrier_id')
    def _compute_dhl_check(self):
        for record in self:
            if record.carrier_id and record.carrier_id.partner_id.id == 5299:
                record.dhl_check=True
            else:
                record.dhl_check=False
    
    
    @api.multi
    def do_enter_transfer_details(self, picking):
        for record in self:
            
            if record.dhl_check:
                if record.del_is_company and not record.del_name1:
                    raise Warning('Fehlender Versandname','Zum Nutzen des Versands muss mindestens das Feld Versandname 1 (Firmenname) gesetzt sein.')
                if not record.del_is_company and not record.del_name1:
                    raise Warning('Fehlender Versandname','Zum Nutzen des Versands muss mindestens das Feld Versandname 3 (Personenname) gesetzt sein.')
                if not record.del_is_company and not record.del_name1_parent:
                    raise Warning('Fehlender Versandname','Zum Nutzen des Versands muss mindestens das Feld Versandname 1 (Firmenname) gesetzt sein.')
                if not record.delivery_address_id.zip:
                    raise Warning('Fehlende Postleitzahl', 'Im verwendeten Lieferkontakt ist keine Postleitzahl eingetragen')
                if record.delivery_address_id.country_id.code == 'DE' and len(record.delivery_address_id.zip) != 5:
                    raise Warning('Falsche Postleitzahl', 'Für den Versand in Deutschland wird eine 5stellige Postleitzahl benötigt')
                if not record.delivery_address_id.city:
                    raise Warning('Fehlende Stadt', 'Im verwendeten Lieferkontakt ist keine Stadt eingetragen')
                if not record.delivery_address_id.street_name:
                    raise Warning('Fehlende Strasse', 'Im verwendeten Lieferkontakt ist keine Strasse eingetragen')
                if not record.delivery_address_id.street_number:
                    raise Warning('Fehlende Hausnummer', 'Im verwendeten Lieferkontakt ist keine Hausnummer eingetragen')
            
                _logger.debug(picking)
                #_logger.debug(self._context)
                #super(ama_del_stock_picking, self).do_enter_transfer_details()
        return super(ama_del_stock_picking, self).do_enter_transfer_details()
    
    auto_stock_carrier = fields.Boolean(string='Automatische Bestellung beim Logistiker', help='Automatische Bestellung der Paketlabels beim verknüpften Logistiker', default=False)
    auto_invoice = fields.Boolean(string='Automatischer E-Mail-Versand der Rechnung', help='Automatische Rechnungserstellung und Versendung nach Lieferung', default=False)
    auto_stock = fields.Boolean(string='Automatischer E-Mail-Versand des Lieferscheins', help='Automatischer Versand der E-Mail mit Lieferschein und Versandlabels nach Bestaetigen der Lieferung', default=False)
    mail_sent = fields.Boolean(string='Lieferschein versendet', help='Lieferschein und Versandlabel wurden per E-Mail versendet', default=False)
    delivery_done = fields.Boolean(string='Lieferung vollzogen', compute='_compute_delivery_done', help='Markiert ob alle zugehoerigen Sendungen abgeschlossen sind.', default=False)
    del_date = fields.Date(string='Erwartetes Lieferdatum', compute='_compute_date_done', help='Datum an dem die Rechnung spaetestens generiert wird.', default=False, store=True)
    
    carrier_label = fields.Many2one('ir.attachment', ondelete='restrict', string="Frachtführer Label", readonly=True, store=True)
    carrier_label_printer = fields.Many2one('printing.printer', string="Labeldrucker", store=True, default=lambda self: self.env['printing.printer'].search([('default','=',True)], limit=1))
    carrier_status_code = fields.Char('Frachtführer Status-Code', readonly=True)
    carrier_status_message = fields.Char('Frachtführer Status-Message', readonly=True)
    
    dhl_check = fields.Boolean(string='Lieferant ist DHL', compute='_compute_dhl_check', default=False, store=True)
    stock_dm_picking_unit_ids = fields.One2many(comodel_name='stock.dm.picking.unit', inverse_name='stock_picking_id', string="Sendescheine")
    
    del_is_company = fields.Boolean(related='delivery_address_id.is_company', readonly=True)
    del_name1 = fields.Char(related='delivery_address_id.del_name1', store=True)
    del_name2 = fields.Char(related='delivery_address_id.del_name2', store=True)
    del_name1_parent = fields.Char(related='delivery_address_id.parent_id.del_name1', store=True)
    del_name2_parent = fields.Char(related='delivery_address_id.parent_id.del_name2', store=True)
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True
        
    @api.multi
    @api.depends('date_done', 'move_lines.product_id.sale_delay', 'move_lines.product_id.seller_ids.delay')
    def _compute_date_done(self):
        for record in self:
            date_start = (record.date_done and fields.Date.from_string(record.date_done)) or datetime.today().date()
            max_days = 0
            
            if record.move_lines:
                if record.picking_type_id and record.picking_type_id.id == self.env['ir.model.data'].get_object_reference('stock_dropshipping', 'picking_type_dropship')[1]:
                    for ml in record.move_lines:
                        for s in ml.product_id.seller_ids:
                            if s.name == record.partner_id:
                                max_days = max(max_days, s.delay)
                else:
                    max_days = max(ml.product_id.sale_delay for ml in record.move_lines)
            
            record.del_date = date_start + timedelta(days = max_days)
                    
        
    @api.multi
    @api.depends('stock_dm_picking_unit_ids')
    def _compute_delivery_done(self):
        for record in self:
            if record.state != 'done':
                record.delivery_done = False
            else:
                if record.del_date <= fields.Date.today():
                    record.delivery_done = True
                else:
                    if record.stock_dm_picking_unit_ids and all(pu.stock_dm_state_id and pu.stock_dm_state_id.sequence in [50, 80] for pu in record.stock_dm_picking_unit_ids):
                        record.delivery_done = True
                    else:
                        record.delivery_done = False
                    
                    
                '''if not record.stock_dm_picking_unit_ids:
                    record.delivery_done = True
                else:
                    record.delivery_done = True
                    for pu in record.stock_dm_picking_unit_ids:
                        if not pu.stock_dm_state_id or (pu.stock_dm_state_id and pu.stock_dm_state_id.sequence not in [50, 80]):
                            record.delivery_done = False
                            break'''
            
    
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
                template_id = ir_model_data.get_object_reference(cr, uid, 'ama_delivery', 'email_template_stock_picking_default')[1]
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
            'attachment_ids': [dn.carrier_label.id],
            'mark_dn_as_sent': True
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
    
    @api.multi
    def action_print_label(self):
        for record in self:
            if record.carrier_label and record.carrier_label_printer:
                datas = base64.decodestring(record.carrier_label.datas)
                record.carrier_label_printer.print_document(False, datas, 'pdf')
    
    
    def force_delivery_note_send(self, cr, uid, ids, context=None):
        for picking_id in ids:
            email_act = self.action_delivery_note_send(cr, uid, [picking_id], context=context)
            if email_act and email_act.get('context'):
                composer_obj = self.pool['mail.compose.message']
                composer_values = {}
                email_ctx = email_act['context']
                template_values = [
                    email_ctx.get('default_template_id'),
                    email_ctx.get('default_composition_mode'),
                    email_ctx.get('default_model'),
                    email_ctx.get('default_res_id'),
                ]
                composer_values.update(composer_obj.onchange_template_id(cr, uid, None, *template_values, context=context).get('value', {}))
                if not composer_values.get('email_from'):
                    composer_values['email_from'] = self.browse(cr, uid, picking_id, context=context).company_id.email
                for key in ['attachment_ids', 'partner_ids']:
                    if composer_values.get(key):
                        composer_values[key] = [(6, 0, composer_values[key])]
                pick = self.pool.get('stock.picking').browse(cr, uid, picking_id)
                _logger.debug('vor: %s' % str(composer_values))
                if pick.carrier_label:
                    composer_values['attachment_ids'].append((4, pick.carrier_label.id, 0))
                _logger.debug('nach: %s' % str(composer_values))
                composer_id = composer_obj.create(cr, uid, composer_values, context=email_ctx)
                composer_obj.send_mail(cr, uid, [composer_id], context=email_ctx)
                #pick.mail_sent = True
        return True
        
class mail_compose_message(models.Model):
    _inherit = 'mail.compose.message'

    @api.v7
    def send_mail(self, cr, uid, ids, context=None):
        context = context or {}
        if context.get('default_model') == 'stock.picking' and context.get('default_res_id') and context.get('mark_dn_as_sent'):
            #context = dict(context, mail_post_autofollow=True)
            self.pool.get('stock.picking').browse(cr, uid, context['default_res_id'], context=context).mail_sent = True
            #self.pool.get('sale.order').signal_workflow(cr, uid, [context['default_res_id']], 'quotation_sent')
        return super(mail_compose_message, self).send_mail(cr, uid, ids, context=context)
        
    
class ama_del_stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'
    
    @api.v7
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(ama_del_stock_transfer_details, self).default_get(cr, uid, fields, context=context)
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        items = []
        packs = []
        if not picking.pack_operation_ids:
            picking.do_prepare_partial()
        for op in picking.pack_operation_ids:
            # _logger.info(str(op.product_qty) + " und " + str(op.linked_move_operation_ids.move_id.release_quantity_value))
            item = {
                'packop_id': op.id,
                'product_id': op.product_id.id,
                'product_uom_id': op.product_uom_id.id,
                # 'quantity': op.product_qty,
                'quantity': (not picking.backorder_id and op.linked_move_operation_ids.move_id.release_quantity_check and (op.linked_move_operation_ids.move_id.release_quantity_value or '0')) or op.product_qty,
                'package_id': op.package_id.id,
                'lot_id': op.lot_id.id,
                'sourceloc_id': op.location_id.id,
                'destinationloc_id': op.location_dest_id.id,
                'result_package_id': op.result_package_id.id,
                'date': op.date, 
                'owner_id': op.owner_id.id,
            }
            if op.product_id:
                items.append(item)
            elif op.package_id:
                packs.append(item)
        res.update(item_ids=items)
        res.update(packop_ids=packs)
        return res

    @api.multi
    def do_detailed_transfer(self):
        for record in self:
            parcels = 0
            
            _logger.debug('START')
            for item in record.item_ids:
                _logger.debug(item.product_id.container_size)
                if item.product_id.container_size != 0:
                    _logger.debug('item.quantity ' + str(float(item.quantity)))
                    _logger.debug('item.product_uom_id.factor ' + str(item.product_uom_id.factor))
                    quantity = float(item.quantity) / item.product_uom_id.factor
                    _logger.debug('quantity ' + str(quantity))
                    _logger.debug('item.product_id.container_size ' + str(float(item.product_id.container_size)))
                    pcs_per_box = float(item.product_id.container_size) / item.product_id.uom_id.factor
                    _logger.debug('pcs_per_box ' + str(pcs_per_box))
                    parcels += int(ceil(quantity / pcs_per_box))
                    _logger.info('quantity: ' + str(quantity) + ' pcs_per_box: ' + str(pcs_per_box) + ' parcels: ' + str(parcels))
                else:
                    if item.product_id.name:
                        _logger.error('Lieferung: Fuer das Produkt \"' + item.product_id.name.encode('utf-8') + '\" ist keine Gebindegroesse hinterlegt.')
                        raise Warning(('Lieferung'), ('Fuer das Produkt \"' + item.product_id.name.encode('utf-8') + '\" ist keine Gebindegroesse hinterlegt.'))
            _logger.debug('ENDE')
            
            record.picking_id.number_of_packages = parcels
            
            if record.picking_id.auto_stock_carrier and record.picking_id.dhl_check:
                _logger.info('Initiiere DHL-Versand fuer Lieferschein %s' % (record.picking_id.name))
                #parcels = 0
                sender = None
                # changed to sender all time amamedis
                # if need of single warehouse each time need to be fixed in the lines below because of no partner in source_loc while dropshipping
                company = record.picking_id.company_id
                sender = company.partner_id
                
                # Get number of parcels to send
                # _logger.info(str(record.item_ids))
                '''for item in record.item_ids:
                    #_logger.info(item.product_id.container_size)
                    if item.product_id.container_size != 0:
                        # Get sender address
                        #if not sender:
                            #if record.picking_id.picking_type_id and record.picking_id.picking_type_id.id == record.env['ir.model.data'].get_object_reference('stock_dropshipping', 'picking_type_dropship')[1]:
                                #sender = record.picking_id.partner_id
                            #else:
                                #sender = item.sourceloc_id.partner_id
                        _logger.debug('item.quantity ' + str(float(item.quantity)))
                        _logger.debug('item.product_uom_id.factor ' + str(item.product_uom_id.factor))
                        quantity = float(item.quantity) / item.product_uom_id.factor
                        _logger.debug('quantity ' + str(quantity))
                        _logger.debug('item.product_id.container_size ' + str(float(item.product_id.container_size)))
                        pcs_per_box = float(item.product_id.container_size) / item.product_id.uom_id.factor
                        _logger.debug('pcs_per_box ' + str(pcs_per_box))
                        parcels += int(ceil(quantity / pcs_per_box))
                        _logger.info('quantity: ' + str(quantity) + ' pcs_per_box: ' + str(pcs_per_box) + ' parcels: ' + str(parcels))
                    else:
                        if item.product_id.name:
                            _logger.error(('Fehler'), ('Fuer das Produkt \"' + item.product_id.name.encode('utf-8') + '\" ist keine Gebindegroesse hinterlegt.'))'''
                # Error handling
                if parcels == 0:
                    _logger.error('DHL Versand: Die Anzahl der berechneten Pakete ist null!')
                    raise Warning(('DHL Versand'), ('Die Anzahl der berechneten Pakete ist null!'))
                else:
                    _logger.info('Berechnete Anzahl an Paketen ist %s' % (str(parcels)))
                if not sender:
                    _logger.error('DHL Versand: Absender für die Pakete konnte nicht gesetzt werden. Bitte Route waehlen, bzw. Eigentuemer des Lagers setzen von dem Versand wird.')
                    raise Warning(('DHL Versand'), ('Absender für die Pakete konnte nicht gesetzt werden. Bitte Route waehlen, bzw. Eigentuemer des Lagers setzen von dem Versand wird.'))
                if (sender.street == '' or sender.city == '' or sender.zip == ''):
                    _logger.error('DHL Versand: Absendeadresse (Eigentümer des Lagers) ist unvollstaendig.')
                    raise Warning(('DHL Versand'), ('Absendeadresse (Eigentümer des Lagers) ist unvollstaendig.'))
                if not company.del_oc_local_dir:
                    _logger.error('DHL Versand Einstellungen: Bitte lokales owncloud Verzeichnis angeben.')
                    raise Warning('DHL Versand Einstellungen', 'Bitte lokales owncloud Verzeichnis angeben.')
                                
                recipient = record.picking_id.delivery_address_id
                
                if not recipient:
                    _logger.error(('DHL Versand: Empfaenger für die Pakete konnte nicht gesetzt werden. Ursache: Lieferschein enthaelt keine Auftragszeilen oder diesen ist kein Empfaenger zugeordnet.'))
                    raise Warning(('DHL Versand'), ('Empfaenger für die Pakete konnte nicht gesetzt werden. Ursache: Lieferschein enthaelt keine Auftragszeilen oder diesen ist kein Empfaenger zugeordnet.'))
                if (recipient.street == '' or recipient.city == '' or recipient.zip == ''):
                    _logger.error('DHL Versand: Lieferadresse ist unvollstaendig.')
                    raise Warning(('DHL Versand'), ('Lieferadresse ist unvollstaendig.'))
                
                parcels_todo = parcels
                max_request = (company.sandbox_dhl and 10) or 30
                _logger.debug('parcels_todo %s max_request %s' % (str(parcels_todo),str(max_request)))
                
                location = (company.sandbox_dhl and company.endpoint_order_dhl_test) or company.endpoint_order_dhl
                cig_username = (company.sandbox_dhl and company.cig_user_dhl_test) or (company.api_order_dhl == '1' and company.cig_user_dhl) or (company.api_order_dhl == '2' and company.cig_user_dhl2)
                cig_password = (company.sandbox_dhl and company.cig_pass_dhl_test) or (company.api_order_dhl == '1' and company.cig_pass_dhl) or (company.api_order_dhl == '2' and company.cig_pass_dhl2)
                intraship_username = (company.sandbox_dhl and company.intraship_user_dhl_test) or (company.api_order_dhl == '1' and company.intraship_user_dhl) or (company.api_order_dhl == '2' and company.gkp_user_dhl)
                intraship_password = (company.sandbox_dhl and company.intraship_pass_dhl_test) or (company.api_order_dhl == '1' and company.intraship_pass_dhl) or (company.api_order_dhl == '2' and company.gkp_pass_dhl)
                ekp = (company.sandbox_dhl and company.ekp_dhl_test) or company.ekp_dhl
                partner_id = (company.sandbox_dhl and company.partner_id_dhl_test) or company.partner_id_dhl
                
                pdf = PyPDF2.PdfFileMerger()
                receive_error = 0
                
                while parcels_todo > 0 and receive_error in range(3):
                    i = 1
                    
                    if company.api_order_dhl == '1':
                    
                        WSDL_URL = u'https://cig.dhl.de/cig-wsdls/com/dpdhl/wsdl/geschaeftskundenversand-api/1.0/geschaeftskundenversand-api-1.0.wsdl'
                        client = Client(WSDL_URL, prettyxml=True, faults=True, location=location, transport=HttpAuthenticated(username = cig_username, password = cig_password), nosend=False, plugins=[MyPlugin()])
                    
                        authentification = client.factory.create('ns1:AuthentificationType')
                        authentification.user = intraship_username
                        authentification.signature = intraship_password
                        client.set_options(soapheaders=authentification)

                        version = client.factory.create('cis:Version')
                        version.majorRelease = u'1'
                        version.minorRelease = u'0'
                        
                        shipmentOrders = []
                        parcels_request = min(parcels_todo,max_request)

                        while i <= parcels_request:
                            _logger.debug('i %s <= parcels_request %s' % (str(i),str(parcels_request)))
                            shipmentItem = client.factory.create('ns0:ShipmentItemDDType')
                            shipmentItem.WeightInKG = u'31.5'
                            shipmentItem.PackageType = 'PK'

                            attendance = client.factory.create('ns0:Attendance')
                            attendance.partnerID = partner_id

                            shipmentDetails = client.factory.create('ns0:ShipmentDetailsDDType')
                            shipmentDetails.ProductCode = u'EPN'
                            shipmentDetails.EKP = ekp
                            shipmentDetails.Attendance = attendance
                            shipmentDetails.CustomerReference = record.picking_id.orig_order.name or record.picking_id.name or ''
                            shipmentDetails.ShipmentDate = datetime.today().date().strftime('%Y-%m-%d')
                            shipmentDetails.ShipmentItem = shipmentItem

                            company_s_cis = client.factory.create('ns1:Company')
                            company_s_cis.name1 = sender.del_name1 and sender.del_name1.strip()
                            company_s_cis.name2 = sender.del_name2 and sender.del_name2.strip() or ''

                            company_s = client.factory.create('ns0:Company')
                            company_s.Company = company_s_cis

                            zip_s = client.factory.create('ns1:ZipType')
                            zip_s.germany = sender.zip and sender.zip[:5].strip()

                            origin_s = client.factory.create('ns1:CountryType')
                            origin_s.country = (sender.country_id and sender.country_id.name and sender.country_id.name.strip()) or u'Deutschland'
                            origin_s.countryISOCode = (sender.country_id and sender.country_id.code and sender.country_id.code.strip()) or u'DE'

                            address_s = client.factory.create('ns1:Address')
                            address_s.streetName = sender.street_name and sender.street_name[:40].strip()
                            address_s.streetNumber = sender.street_number and sender.street_number[:7].strip() or '1'
                            address_s.city = sender.city and sender.city[:50].strip()
                            address_s.Zip = zip_s
                            address_s.Origin = origin_s

                            #communication_s = client.factory.create('ns1:CommunicationType')
                            #communication_s.email = u''

                            shipper = client.factory.create('ns0:ShipperDDType')
                            shipper.Company = company_s
                            shipper.Address = address_s
                            #shipper.Communication = communication_s

                            company_r_cis = client.factory.create('ns1:Company')
                            company_r_cis.name1 = (not recipient.is_company and recipient.parent_id.del_name1) or recipient.del_name1
                            company_r_cis.name2 = (not recipient.is_company and (recipient.parent_id.del_name2 or recipient.del_name1)) or recipient.del_name2 or ''

                            company_r = client.factory.create('ns0:Company')
                            company_r.Company = company_r_cis

                            zip_r = client.factory.create('ns1:ZipType')
                            zip_r.germany = recipient.zip and recipient.zip[:5].strip()

                            origin_r = client.factory.create('ns1:CountryType')
                            origin_r.country = (recipient.country_id and recipient.country_id.name and recipient.country_id.name.strip()) or u'Deutschland'
                            origin_r.countryISOCode = (recipient.country_id and recipient.country_id.code and recipient.country_id.code.strip()) or u'DE'

                            address_r = client.factory.create('ns1:Address')
                            address_r.streetName = recipient.street_name and recipient.street_name[:40].strip()
                            address_r.streetNumber = recipient.street_number and recipient.street_number[:7].strip() or '1'
                            address_r.city = recipient.city and recipient.city[:50].strip()
                            address_r.Zip = zip_r
                            address_r.Origin = origin_r

                            #communication_r = client.factory.create('ns1:CommunicationType')
                            #communication_r.email = u''

                            receiver = client.factory.create('ns0:ReceiverDDType')
                            receiver.Company = company_r
                            receiver.Address = address_r
                            receiver.CompanyName3 = (not recipient.is_company and recipient.parent_id.del_name2 and recipient.del_name1) or ''
                            #receiver.Communication = communication_r

                            shipment = client.factory.create('ns0:Shipment')
                            shipment.ShipmentDetails = shipmentDetails
                            shipment.Shipper = shipper
                            shipment.Receiver = receiver

                            shipmentOrder = client.factory.create('ns0:ShipmentOrderDDType')
                            shipmentOrder.SequenceNumber = str(i)
                            shipmentOrder.Shipment = shipment

                            shipmentOrders.append(shipmentOrder)

                            request = client.factory.create('ns0:CreateShipmentDDRequest')
                            request.Version = version
                            request.ShipmentOrder.append(shipmentOrder)
                            
                            i += 1
                            parcels_todo -= 1
                            
                            createShipmentResponse = False
                            #createShipmentResponse = client.factory.create('ns0:CreateShipmentResponse')
                            #_logger.debug(createShipmentResponse)
                            
                        try:
                            createShipmentResponse = client.service.createShipmentDD(version, shipmentOrders)
                        except Exception as e:
                            record.picking_id.message_post(subtype='mt_comment', subject='Fehler DHL-Versand (Server)', body=unicode(e))
                            record.picking_id.carrier_status_code = 'Server-Fehler'
                            record.picking_id.carrier_status_message = str(e)
                            _logger.error('Fehler DHL-Versand (Server)', unicode(e))
                            raise Warning('Fehler DHL-Versand (Server)', unicode(e))
                            
                        #_logger.debug('Resultat')
                        if createShipmentResponse:
                            _logger.debug(str(createShipmentResponse))
                            if createShipmentResponse.status is not None:
                                statusCode = createShipmentResponse.status and createShipmentResponse.status.StatusCode and str(createShipmentResponse.status.StatusCode)
                                statusMessage = createShipmentResponse.status and createShipmentResponse.status.StatusMessage and str(createShipmentResponse.status.StatusMessage)
                                record.picking_id.carrier_status_code = statusCode
                                record.picking_id.carrier_status_message = statusMessage
                                _logger.debug('Request ergab den Statuscode %s mit der Nachricht %s' % (statusCode, statusMessage))
                                if statusCode == 0:
                                    if createShipmentResponse.CreationState is not None:
                                        for element in createShipmentResponse.CreationState:
                                            shipmentNumber = element.ShipmentNumber and element.ShipmentNumber.shipmentNumber and str(element.ShipmentNumber.shipmentNumber)
                                            labelURL = element.Labelurl and str(element.Labelurl)
                                            _logger.debug('%s - %s' % (shipmentNumber, labelURL))
                                            if shipmentNumber:
                                                # Create new dhl delivery object
                                                picking_unit = record.env['stock.dm.picking.unit'].create({
                                                    'code' : shipmentNumber,
                                                    'stock_picking_id' : record.picking_id.id,
                                                    'delivery_carrier_id' : record.picking_id.carrier_id.id,
                                                    })
                                                dhl_picking_unit = record.env['stock.dhl.picking.unit'].create({
                                                    'name' : shipmentNumber,
                                                    'stock_dm_picking_unit_id' : picking_unit.id,
                                                    'ownership' : True
                                                    })
                                                picking_unit.update({
                                                    'delivery_carrier_res_id' : dhl_picking_unit.id
                                                    })
                                                path = "/opt/dhl/pdf/" + (company.sandbox_dhl and 'TEST_' or '') + shipmentNumber + ".pdf"
                                                
                                                attempts = 0
                                                for attempts in range(3):
                                                    try:
                                                        urllib.urlretrieve(labelURL, path)
                                                        pdf.append(PyPDF2.PdfFileReader(path, 'rb'))
                                                        break
                                                        # attempts = 4
                                                    except:
                                                        attempts += 1
                                                        _logger.debug('Fehlgeschlagener Versuch beim Herunterladen des DHL Sendescheins als PDF. URL: ' + labelURL)
                                                        if attempts == 3:
                                                            # Sendung löschen und Pakete_ToDo eins hochzählen
                                                            dhl_picking_unit.action_delete()
                                                            parcels_todo += 1
                                                            receive_error += 1
                                                            _logger.error('DHL Versand', 'Konnte DHL Sendeschein nicht als PDF herunterladen. URL: ' + labelURL)
                                                            raise Warning('DHL Versand', 'Konnte DHL Sendeschein nicht als PDF herunterladen. URL: ' + labelURL)
                                    else:
                                        record.picking_unit.message_post(subtype='mt_comment', subject='Fehler DHL-Versand (Request)', body='Request-Antwort enthielt keine Sendungsdaten' % (statusCode, statusMessage))
                                        _logger.error('Fehler DHL-Versand (Request)', 'Request-Antwort enthielt keine Sendungsdaten' % (statusCode, statusMessage))
                                        raise Warning('Fehler DHL-Versand (Request)', 'Request-Antwort enthielt keine Sendungsdaten' % (statusCode, statusMessage))
                                else:
                                    record.picking_id.message_post(subtype='mt_comment', subject='Fehler DHL-Versand (Request)', body='Request ergab den Statuscode %s mit der Nachricht %s' % (statusCode, statusMessage))
                                    _logger.error('Fehler DHL-Versand (Request)', 'Request ergab den Statuscode %s mit der Nachricht %s' % (statusCode, statusMessage))
                                    raise Warning('Fehler DHL-Versand (Request)', 'Request ergab den Statuscode %s mit der Nachricht %s' % (statusCode, statusMessage))
                        else:
                            record.picking_id.carrier_status_code = 'Request-Fehler'
                            record.picking_id.carrier_status_message = 'Abfrage lieferte kein Ergebnis'
                            _logger.error('Request-Fehler', 'Abfrage lieferte kein Ergebnis')
                            raise Warning('Request-Fehler', 'Abfrage lieferte kein Ergebnis')
                    
                    elif company.api_order_dhl == '2':
                        
                        #WSDL_URL = u'file:///opt/dhl/geschaeftskundenversand-api-2.1.wsdl'
                        WSDL_URL = u'https://cig.dhl.de/cig-wsdls/com/dpdhl/wsdl/geschaeftskundenversand-api/2.1/geschaeftskundenversand-api-2.1.wsdl'
                        #WSDL_URL = u'https://cig.dhl.de/cig-wsdls/com/dpdhl/wsdl/geschaeftskundenversand-api/2.0/geschaeftskundenversand-api-2.0.wsdl'
                        client = Client(WSDL_URL, prettyxml=True, faults=True, location=location, transport=HttpAuthenticated(username = cig_username, password = cig_password), nosend=False, plugins=[MyPlugin()])
                    
                        authentification = client.factory.create('cis:AuthentificationType')
                        authentification.user = intraship_username.encode('iso-8859-1')
                        authentification.signature = intraship_password.encode('iso-8859-1')
                        client.set_options(soapheaders=authentification)

                        version = client.factory.create('ns1:Version')
                        version.majorRelease = u'2'
                        version.minorRelease = u'1'

                        shipmentOrders = []
                        parcels_request = min(parcels_todo,max_request)

                        while i <= parcels_request:
                            _logger.debug('i %s <= parcels_request %s' % (str(i),str(parcels_request)))
                            shipmentItem = client.factory.create('ShipmentItemType')
                            shipmentItem.weightInKG = u'31.5'

                            shipmentDetails = client.factory.create('ShipmentDetailsTypeType')
                            shipmentDetails.product = record.picking_id.carrier_id.product.encode('iso-8859-1')
                            shipmentDetails.accountNumber = (''.join([ekp or '', record.picking_id.carrier_id.procedure or '', partner_id or ''])).encode('iso-8859-1')
                            shipmentDetails.customerReference = record.picking_id.orig_order.name.encode('iso-8859-1') or record.picking_id.name.encode('iso-8859-1') or ''
                            shipmentDetails.shipmentDate = (datetime.today().date().strftime('%Y-%m-%d')).encode('iso-8859-1')
                            shipmentDetails.ShipmentItem = shipmentItem

                            name_s = client.factory.create('ns0:NameType')
                            name_s.name1 = sender.del_name1 and sender.del_name1.strip().encode('iso-8859-1')
                            name_s.name2 = sender.del_name2 and sender.del_name2.strip().encode('iso-8859-1') or ''

                            origin_s = client.factory.create('ns0:CountryType')
                            origin_s.country = (sender.country_id and sender.country_id.name and sender.country_id.name.strip().encode('iso-8859-1')) or u'Deutschland'
                            origin_s.countryISOCode = (sender.country_id and sender.country_id.code and sender.country_id.code.strip().encode('iso-8859-1')) or u'DE'

                            address_s = client.factory.create('ns0:NativeAddressType')
                            _logger.debug(sys.stdout.encoding)
                            _logger.debug(type(sender.street_name[:40].strip()))
                            address_s.streetName = sender.street_name and sender.street_name[:40].strip().encode('iso-8859-1')
                            address_s.streetNumber = sender.street_number and sender.street_number[:7].strip().encode('iso-8859-1') or u'1'
                            address_s.zip = sender.zip and sender.zip[:5].strip().encode('iso-8859-1')
                            address_s.city = sender.city and sender.city[:50].strip().encode('iso-8859-1')
                            address_s.Origin = origin_s

                            #communication_s = client.factory.create('ns0:CommunicationType')
                            #communication_s.email = u''

                            shipper = client.factory.create('ShipperType')
                            shipper.Name = name_s
                            shipper.Address = address_s
                            #shipper.Communication = communication_s

                            origin_r = client.factory.create('ns0:CountryType')
                            origin_r.country = (recipient.country_id and recipient.country_id.name and recipient.country_id.name.strip().encode('iso-8859-1')) or u'Deutschland'
                            origin_r.countryISOCode = (recipient.country_id and recipient.country_id.code and recipient.country_id.code.strip().encode('iso-8859-1')) or u'DE'

                            address_r = client.factory.create('ns0:ReceiverNativeAddressType')
                            
                            address_r.name2 = (not recipient.is_company and ((recipient.parent_id.del_name2 and recipient.parent_id.del_name2.encode('iso-8859-1')) or (recipient.del_name1 and recipient.del_name1.encode('iso-8859-1')))) or (recipient.del_name2 and recipient.del_name2.encode('iso-8859-1')) or ''
                            address_r.name3 = (not recipient.is_company and recipient.parent_id.del_name2 and recipient.del_name1 and recipient.del_name1.encode('iso-8859-1')) or ''
                            address_r.streetName = recipient.street_name and recipient.street_name[:40].strip().encode('iso-8859-1')
                            address_r.streetNumber = recipient.street_number and recipient.street_number[:7].strip().encode('iso-8859-1') or u'1'
                            address_r.zip = recipient.zip and recipient.zip[:5].strip().encode('iso-8859-1')
                            address_r.city = recipient.city and recipient.city[:50].strip().encode('iso-8859-1')
                            address_r.Origin = origin_r

                            #communication_r = client.factory.create('ns0:CommunicationType')
                            #communication_r.email = u''

                            receiver = client.factory.create('ReceiverType')
                            receiver.name1 = (not recipient.is_company and recipient.parent_id.del_name1 and recipient.parent_id.del_name1.encode('iso-8859-1')) or (recipient.del_name1 and recipient.del_name1.encode('iso-8859-1'))
                            receiver.Address = address_r
                            #receiver.Communication = communication_r

                            shipment = client.factory.create('Shipment')
                            shipment.ShipmentDetails = shipmentDetails
                            shipment.Shipper = shipper
                            shipment.Receiver = receiver

                            shipmentOrder = client.factory.create('ns1:ShipmentOrderType')
                            shipmentOrder.sequenceNumber = str(i)
                            shipmentOrder.Shipment = shipment

                            shipmentOrders.append(shipmentOrder)

                            i += 1
                            parcels_todo -= 1
                            
                            createShipmentOrderResponse = False
                            #createShipmentOrderResponse = client.factory.create('bcs:CreateShipmentOrderResponse')
                            
                        try:
                            _logger.debug(sys.getdefaultencoding())
                            createShipmentOrderResponse = client.service.createShipmentOrder(Version = version, ShipmentOrder = shipmentOrders)
                        except Exception as e:
                            record.picking_id.message_post(subtype='mt_comment', subject='Fehler DHL-Versand (Server)', body=unicode(e))
                            record.picking_id.carrier_status_code = 'Server-Fehler'
                            record.picking_id.carrier_status_message = unicode(e)
                            _logger.error('Fehler DHL-Versand (Server)', unicode(e))
                            raise Warning('Fehler DHL-Versand (Server)', unicode(e))
                            
                        #_logger.debug('Resultat')
                        if createShipmentOrderResponse:
                            _logger.debug(str(createShipmentOrderResponse))
                            if createShipmentOrderResponse.Status is not None:
                                statusCode = createShipmentOrderResponse.Status and createShipmentOrderResponse.Status.statusCode and str(createShipmentOrderResponse.Status.statusCode)
                                statusMessage = createShipmentOrderResponse.Status and createShipmentOrderResponse.Status.statusMessage and createShipmentOrderResponse.Status.statusMessage[0]
                                record.picking_id.carrier_status_code = statusCode
                                record.picking_id.carrier_status_message = statusMessage
                                _logger.debug('Request ergab den Statuscode %s mit der Nachricht %s' % (statusCode, statusMessage))
                                if statusCode == 0:
                                    if createShipmentOrderResponse.CreationState is not None:
                                        for element in createShipmentOrderResponse.CreationState:
                                            shipmentNumber = element.LabelData and element.LabelData.shipmentNumber and str(element.LabelData.shipmentNumber)
                                            labelURL = element.LabelData and element.LabelData.labelUrl and str(element.LabelData.labelUrl)
                                            _logger.debug('%s - %s' % (shipmentNumber, labelURL))
                                            if shipmentNumber:
                                                # Create new dhl delivery object
                                                picking_unit = record.env['stock.dm.picking.unit'].create({
                                                    'code' : shipmentNumber,
                                                    'stock_picking_id' : record.picking_id.id,
                                                    'delivery_carrier_id' : record.picking_id.carrier_id.id,
                                                    })
                                                dhl_picking_unit = record.env['stock.dhl.picking.unit'].create({
                                                    'name' : shipmentNumber,
                                                    'stock_dm_picking_unit_id' : picking_unit.id,
                                                    'ownership' : True
                                                    })
                                                picking_unit.update({
                                                    'delivery_carrier_res_id' : dhl_picking_unit.id,
                                                    })
                                                path = "/opt/dhl/pdf/" + (company.sandbox_dhl and 'TEST_' or '') + shipmentNumber + ".pdf"
                                                
                                                attempts = 0
                                                for attempts in range(3):
                                                    try:
                                                        urllib.urlretrieve(labelURL, path)
                                                        pdf.append(PyPDF2.PdfFileReader(path, 'rb'))
                                                        break
                                                        # attempts = 4
                                                    except:
                                                        attempts += 1
                                                        _logger.debug('Fehlgeschlagener Versuch beim Herunterladen des DHL Sendescheins als PDF. URL: ' + labelURL)
                                                        if attempts == 3:
                                                            # Sendung löschen und Pakete_ToDo eins hochzählen
                                                            dhl_picking_unit.action_delete()
                                                            parcels_todo += 1
                                                            receive_error += 1
                                                            _logger.error('DHL Versand', 'Konnte DHL Sendeschein nicht als PDF herunterladen. URL: ' + labelURL)
                                                            raise Warning('DHL Versand', 'Konnte DHL Sendeschein nicht als PDF herunterladen. URL: ' + labelURL)
                                    else:
                                        record.picking_unit.message_post(subtype='mt_comment', subject='Fehler DHL-Versand (Request)', body='Request-Antwort enthielt keine Sendungsdaten' % (statusCode, statusMessage))
                                        _logger.error('Fehler DHL-Versand (Request)', 'Request-Antwort enthielt keine Sendungsdaten' % (statusCode, statusMessage))
                                        raise Warning('Fehler DHL-Versand (Request)', 'Request-Antwort enthielt keine Sendungsdaten' % (statusCode, statusMessage))
                                else:
                                    record.picking_id.message_post(subtype='mt_comment', subject='Fehler DHL-Versand (Request)', body='Request ergab den Statuscode %s mit der Nachricht %s' % (statusCode, statusMessage))
                                    _logger.error('Fehler DHL-Versand (Request)', 'Request ergab den Statuscode %s mit der Nachricht %s' % (statusCode, statusMessage))
                                    raise Warning('Fehler DHL-Versand (Request)', 'Request ergab den Statuscode %s mit der Nachricht %s' % (statusCode, statusMessage))
                        else:
                            record.picking_id.carrier_status_code = 'Request-Fehler'
                            record.picking_id.carrier_status_message = 'Abfrage lieferte kein Ergebnis'
                            _logger.error('Request-Fehler', 'Abfrage lieferte kein Ergebnis')
                            raise Warning('Request-Fehler', 'Abfrage lieferte kein Ergebnis')
                            
                
                if len(pdf.pages) > 0:
                    # Close PDF file and save
                    filename = (company.sandbox_dhl and 'TEST_' or '') + self.picking_id.name + "-DHL.pdf"
                    filename = filename.replace('/','_')
                    path = "/opt/dhl/pdf/" + filename
                    try:
                        pdf.write(path)
                        # Add PDF as attachment to delivery note
                        try:
                            attach_id = record.env['ir.attachment'].create({
                                'name':filename,
                                'datas_fname':filename,
                                'res_name': filename,
                                'type': 'binary',
                                'res_model': 'stock.picking',
                                'res_id': record.picking_id.id,
                                'datas': base64.b64encode(open(path, 'rb').read()),
                            })
                            record.picking_id.carrier_label = attach_id
                        except:
                            _logger.warning('DHL Versand', 'Konnte Sammelpdf nicht als Attachment hinzufügen.')
                            
                        # Copy pdf to synced owncloud directory
                        if not company.del_oc_local_dir[:-1] == '/':
                            oc_path = company.del_oc_local_dir + '/'
                        else:
                            oc_path = company.del_oc_local_dir
                        # Get name of the year and supplier name
                        # year = datetime.datetime.now().strftime('%Y')
                        # supplier = sender.name.replace(' ','_').replace('/','_')
                        # oc_path += year + '/' + supplier + '/DHL_Sendescheine/unversendet/'
                        # Make directory if not existing
                        try:
                            # os.makedirs(oc_path)
                            os.makedirs(company.del_oc_local_dir)
                        except OSError as exception:
                            if exception.errno != errno.EEXIST:
                                _logger.warning('DHL Versand OwnCloud', 'Konnte Verzeichnis nicht erstellen: ' + oc_path)
                        # if os.path.isdir(oc_path):
                        if os.path.isdir(company.del_oc_local_dir):
                            # Copy pdf to owncloud directory
                            shutil.copy(path, company.del_oc_local_dir)
                            # Sync owncloud
                            command = ['owncloudcmd']
                            # Arguments
                            arguments = [
                                    '-u', company.del_oc_user,
                                    '-p', company.del_oc_password,
                                    company.del_oc_local_dir,
                                    company.del_oc_remote_dir
                                    ]
                            command.extend(arguments)
                            # Execute owncloud syncing
                            out, err = Popen(command, stdin=PIPE, stdout=PIPE,
                                    stderr=PIPE).communicate()
                    except:
                        _logger.warning('DHL Versand', 'Konnte Sammelpdf nicht speichern. Pfad: ' + path)
            
                
            super(ama_del_stock_transfer_details, self).do_detailed_transfer()
            
            if record.picking_id.auto_stock:
                record.picking_id.force_delivery_note_send()
        return True                
                
                
class MyPlugin(MessagePlugin):

    def marshalled(self, context):
        #_logger.debug('Marshalled')
        
        for body_element in context.envelope.childAtPath('Body'):
            #_logger.debug(body_element.name)
            if body_element.name == 'CreateShipmentDDRequest':
                for element in body_element:
                    #_logger.debug(element.name)
                    if element.name == 'Version':
                        element.setPrefix('ns0')
                    if element.name == 'ShipmentOrder':
                        if element.childAtPath('Shipment/ShipmentDetails/EKP') is not None:
                            element.childAtPath('Shipment/ShipmentDetails/EKP').setPrefix('ns0')
                        if element.childAtPath('Shipment/ShipmentDetails/Attendance/partnerID') is not None:
                            element.childAtPath('Shipment/ShipmentDetails/Attendance/partnerID').setPrefix('ns0')
            elif body_element.name == 'CreateShipmentOrderRequest':
                for element in body_element:
                    #_logger.debug(element.name)
                    if element.name == 'ShipmentOrder':
                        if element.childAtPath('Shipment/ShipmentDetails/accountNumber') is not None:
                            element.childAtPath('Shipment/ShipmentDetails/accountNumber').setPrefix('ns0')
                        if element.childAtPath('Shipment/Receiver/name1') is not None:
                            element.childAtPath('Shipment/Receiver/name1').setPrefix('ns0')
