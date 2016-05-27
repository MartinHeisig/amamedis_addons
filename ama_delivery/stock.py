# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools.translate import _
from math import ceil
from subprocess import Popen, PIPE

import urllib
import PyPDF2
import base64
import datetime
import os
import shutil
import errno
import logging

import constants_dhl

_logger = logging.getLogger(__name__)

class ama_stock_location_route(models.Model):
    _inherit = ['stock.location.route']
    
    # switches which actions should be automated when using this route
    auto_sale = fields.Boolean(string='Auto E-Mail Auftragsbestaetigung', help='Automatischer Versand E-Mail Auftragsbestaetigung', default=False)
    auto_purchase = fields.Boolean(string='Auto Annahme Bestellung', help='Automatische Bestaetigung des ERSTEN vorkalkulierten Lieferantenangebots', default=False)
    auto_stock = fields.Boolean(string='Auto Abwicklung Lieferung', help='Automatische Initiierung der Lieferung durch Versand E-Mail Lieferschein an Lager/Lieferant', default=False)
    auto_stock_carrier = fields.Boolean(string='Auto Bestellung Logistiker', help='Automatische Bestellung der Paketlabels beim verknüpften Logistiker')
    auto_invoice = fields.Boolean(string='Auto E-Mail Rechnung', help='Automatische Rechnungserstellung und Versendung nach Lieferung', default=False)

class ama_rq_stock_move(models.Model):
    _inherit = 'stock.move'
    
    @api.multi
    @api.onchange('release_quantity_check')
    def _onchange_release_quantity_check(self):
        for record in self:
            if not record.release_quantity_check:
                record.release_quantity_value = record.product_uom_qty
    
    '''@api.multi
    @api.depends('product_uom_qty','release_quantity_check','release_quantity_input')
    def _compute_release_quantity(self):
        for record in self:
            if not record.release_quantity_check:
                record.release_quantity_value = record.product_uom_qty
            else:
                if record.release_quantity_input < 0:
                    raise Warning('Fehlerhafte Abrufmenge','Abrufmenge muss größer gleich 0 sein.')
                elif record.release_quantity_input > record.product_uom_qty:
                    raise Warning('Fehlerhafte Abrufmenge','Abrufmenge muss kleiner gleich der Bestellmenge sein.')
                else:
                    record.release_quantity_value = record.release_quantity_input'''
                
    '''@api.multi
    @api.constrains('release_quantity_input')
    def _check_release_quantity(self):
        for record in self:
            if not record.backorder_id:
                if record.release_quantity_input < 0:
                    raise Warning('Fehlerhafte Abrufmenge','Abrufmenge muss größer gleich 0 sein.')
                if record.release_quantity_input > record.product_uom_qty:
                    raise Warning('Fehlerhafte Abrufmenge','Abrufmenge muss kleiner gleich der Bestellmenge sein.')'''
                
    # , compute='_compute_release_quantity'
    release_quantity_value = fields.Float('Abrufmenge', help="Anzahl der Produkte für einzelnen Lagerabrufe in der gleichen Einheit, wie die Standardmengeneinheit.")
    release_quantity_check = fields.Boolean('Abrufmenge aktivieren', help="Nur wenn dieser Schalter gesetzt ist, wird die Abrufmenge geliefert, sonst die komplette Bestellmenge.")
    release_quantity_input = fields.Float('Abrufmenge', help="Eingabefeld für die Abrufmenge")

    
class ama_del_stock_picking(models.Model):
    _inherit = ['stock.picking']
    
    @api.multi
    @api.depends('carrier_id')
    def _compute_dhl_check(self):
        for record in self:
            if record.carrier_id and record.carrier_id.partner_id.id == 5299:
                record.dhl_check=True
            else:
                record.dhl_check=False
    
    @api.multi
    @api.onchange('carrier_id','delivery_address_id','partner_id')
    def _validate_dhl_address(self):
        for record in self:
            if record.delivery_address_id:
                if record.delivery_address_id.is_company:
                    # delivery contact is a company
                    # get contacts dhl_name1 or build it from contacts name
                    record.dhl_name1 = (record.delivery_address_id.dhl_name1 and record.delivery_address_id.dhl_name1.strip()) or (record.delivery_address_id.name and record.delivery_address_id.name.strip()[0:30])
                    # get contacts dhl_name2 (no need to get companys first name, its only needed for invoices)
                    record.dhl_name2 = (record.delivery_address_id.dhl_name2 and record.delivery_address_id.dhl_name2.strip())
                else:
                    # get contacts dhl_name1 or companys dhl_name1 or get it from companys name
                    record.dhl_name1 = (record.delivery_address_id.dhl_name1 and record.delivery_address_id.dhl_name1.strip()) or (record.delivery_address_id.parent_id and ((record.delivery_address_id.parent_id.dhl_name1 and record.delivery_address_id.parent_id.dhl_name1.strip()) or record.delivery_address_id.parent_id.name.strip()[0:30]))
                    # get it from dhl_name2 or build it from contacts name and first_name
                    record.dhl_name2 = (record.delivery_address_id.dhl_name2 and record.delivery_address_id.dhl_name2.strip()) or (len(' '.join([record.delivery_address_id.first_name or '', record.delivery_address_id.name or '']).strip()) <= 30 and ' '.join([record.delivery_address_id.first_name or '', record.delivery_address_id.name or '']).strip()) or record.delivery_address_id.name.strip()[0:30]
                if record.delivery_address_id.is_company or not record.delivery_address_id.use_parent_address:
                    # delivery contact is a company or uses his own address
                    # get presaved dhl-fields or build them from contacts data
                    record.dhl_streetName = (record.delivery_address_id.dhl_streetName and record.delivery_address_id.dhl_streetName.strip()) or (record.delivery_address_id.street_name and record.delivery_address_id.street_name.strip()[0:30])
                    record.dhl_streetNumber = (record.delivery_address_id.dhl_streetNumber and record.delivery_address_id.dhl_streetNumber.strip()) or (record.delivery_address_id.street_number and record.delivery_address_id.street_number.strip()[0:7])
                    record.dhl_zip = (record.delivery_address_id.dhl_zip and record.delivery_address_id.dhl_zip.strip()) or (record.delivery_address_id.zip and record.delivery_address_id.zip.strip()[0:5])
                    record.dhl_city = (record.delivery_address_id.dhl_city and record.delivery_address_id.dhl_city.strip()) or (record.delivery_address_id.city and record.delivery_address_id.city.strip()[0:50])
                else:
                    # delivery address is a person and uses companys address
                    # get presaved dhl-fields from partner
                    record.dhl_streetName_parent = (record.delivery_address_id.parent_id and ((record.delivery_address_id.parent_id.dhl_streetName and record.delivery_address_id.parent_id.dhl_streetName.strip()[0:30]) or (record.delivery_address_id.parent_id.street_name and record.delivery_address_id.parent_id.street_name.strip()[0:30])))
                    record.dhl_streetNumber_parent = (record.delivery_address_id.parent_id and ((record.delivery_address_id.parent_id.dhl_streetNumber and record.delivery_address_id.parent_id.dhl_streetNumber.strip()[0:7]) or (record.delivery_address_id.parent_id.street_number and record.delivery_address_id.parent_id.street_number.strip()[0:7])))
                    record.dhl_zip_parent = (record.delivery_address_id.parent_id and ((record.delivery_address_id.parent_id.dhl_zip and record.delivery_address_id.parent_id.dhl_zip.strip()[0:5]) or (record.delivery_address_id.parent_id.zip and record.delivery_address_id.parent_id.zip.strip()[0:5])))
                    record.dhl_city_parent = (record.delivery_address_id.parent_id and ((record.delivery_address_id.parent_id.dhl_city and record.delivery_address_id.parent_id.dhl_city.strip()[0:50]) or (record.delivery_address_id.parent_id.city and record.delivery_address_id.parent_id.city.strip()[0:50])))
                record.dhl_phone = (record.delivery_address_id.dhl_phone and record.delivery_address_id.dhl_phone.strip()) or (record.delivery_address_id.phone and record.delivery_address_id.phone.strip()[0:20])
                record.dhl_email = (record.delivery_address_id.dhl_email and record.delivery_address_id.dhl_email.strip()) or (record.delivery_address_id.email and record.delivery_address_id.email.strip()[0:30])
    
    @api.multi
    @api.constrains('dhl_name1','dhl_name2','dhl_streetName','dhl_streetNumber','dhl_zip','dhl_city','dhl_streetName_parent','dhl_streetNumber_parent','dhl_zip_parent','dhl_city_parent','dhl_phone','dhl_email')
    def _check_dhl_address(self):
        for record in self:
            if record.dhl_check:
                if not record.dhl_name1:
                    if record.dhl_name2:
                        record.dhl_name1 = record.dhl_name2
                        record.dhl_name2 = ''
                    else:
                        raise Warning('Fehlerhafte DHL-Daten','Es wurde kein Empfängername bei den DHL-formatierten Daten angegeben')
                if record.del_is_company:
                    if not record.dhl_streetName:
                        raise Warning('Fehlerhafte DHL-Daten','Es wurde kein Strassenname bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_streetNumber:
                        raise Warning('Fehlerhafte DHL-Daten','Es wurde keine Hausnummer bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_zip:
                        raise Warning('Fehlerhafte DHL-Daten','Es wurde keine Postleitzahl bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_city:
                        raise Warning('Fehlerhafte DHL-Daten','Es wurde kein Ort bei den DHL-formatierten Daten angegeben')
                if not record.del_is_company:
                    if not record.dhl_streetName_parent:
                        raise Warning('Fehlerhafte DHL-Daten','Es wurde kein Strassenname bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_streetNumber_parent:
                        raise Warning('Fehlerhafte DHL-Daten','Es wurde keine Hausnummer bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_zip_parent:
                        raise Warning('Fehlerhafte DHL-Daten','Es wurde keine Postleitzahl bei den DHL-formatierten Daten angegeben')
                    if not record.dhl_city_parent:
                        raise Warning('Fehlerhafte DHL-Daten','Es wurde kein Ort bei den DHL-formatierten Daten angegeben')
                if not record.dhl_phone and not record.dhl_email:
                    raise Warning('Fehlerhafte DHL-Daten','Es wurde weder eine Kontakttelefonnummer, noch eine Kontaktemail bei den DHL-formatierten Daten angegeben. Mindestens eins der beiden Felder muss ausgefüllt werden')
    
    auto_stock_carrier = fields.Boolean(string='Auto Bestellung Logistiker', help='Automatische Bestellung der Paketlabels beim verknüpften Logistiker', default=False)
    auto_invoice = fields.Boolean(string='Auto E-Mail Rechnung', help='Automatische Rechnungserstellung und Versendung nach Lieferung', default=False)
    
    carrier_label = fields.Many2one('ir.attachment', ondelete='restrict', string="Frachtführer Label", readonly=True, store=True)
    
    dhl_check = fields.Boolean(string='Lieferant ist DHL', compute=_compute_dhl_check, default=False, store=True)
    dhl_name1 = fields.Char('name1', related='delivery_address_id.dhl_name1', store=True)
    dhl_name2 = fields.Char('name2', related='delivery_address_id.dhl_name2', store=True)
    dhl_streetName = fields.Char('streetName', related='delivery_address_id.dhl_streetName', store=True)
    dhl_streetName_parent = fields.Char('streetName', related='delivery_address_id.parent_id.dhl_streetName', store=True)
    dhl_streetNumber = fields.Char('streetNumber', related='delivery_address_id.dhl_streetNumber', store=True)
    dhl_streetNumber_parent = fields.Char('streetNumber', related='delivery_address_id.parent_id.dhl_streetNumber', store=True)
    dhl_zip = fields.Char('zip', related='delivery_address_id.dhl_zip', store=True)
    dhl_zip_parent = fields.Char('zip', related='delivery_address_id.parent_id.dhl_zip', store=True)
    dhl_city = fields.Char('city', related='delivery_address_id.dhl_city', store=True)
    dhl_city_parent = fields.Char('city', related='delivery_address_id.parent_id.dhl_city', store=True)
    dhl_phone = fields.Char('phone', related='delivery_address_id.dhl_phone', store=True)
    dhl_email = fields.Char('email', related='delivery_address_id.dhl_email', store=True)
    
    del_is_company = fields.Boolean(related='delivery_address_id.is_company', readonly=True)
    del_use_parent_address = fields.Boolean(related='delivery_address_id.use_parent_address', readonly=True)
    del_name1_company = fields.Char(related='delivery_address_id.name', readonly=True)
    del_name1_person = fields.Char(related='delivery_address_id.parent_id.name', readonly=True)
    del_name2_company = fields.Char(related='delivery_address_id.first_name', readonly=True)
    del_name2_person_first_name = fields.Char(related='delivery_address_id.first_name', readonly=True)
    del_name2_person_name = fields.Char(related='delivery_address_id.name', readonly=True)
    del_streetName = fields.Char(related='delivery_address_id.street_name', readonly=True)
    del_streetNumber = fields.Char(related='delivery_address_id.street_number', readonly=True)
    del_zip = fields.Char(related='delivery_address_id.zip', readonly=True)
    del_city = fields.Char(related='delivery_address_id.city', readonly=True)
    del_phone = fields.Char(related='delivery_address_id.phone', readonly=True)
    del_email = fields.Char(related='delivery_address_id.email', readonly=True)
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True
    
class ama_del_stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'
    
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

    '''
    Helper function that converts a dictionary of the shipment arguments to a string
    of arguments using only the keys that have a value assigned to it.
    '''
    # Should be removed when change to model is done
    def _assamble_shipment_arguments(self, vals):
        res = []
        for key, value in vals.iteritems():
          if value and value.strip() != '':
            argument = [key + '=' + value.encode('iso-8859-1').strip()]
            res.extend(argument)
        return res

    def _parseJavaOutput(self, out):
        splitted_output = out.split('\n')
        out_dict = {}
        for pair in splitted_output:
          if '==' in pair:
            splitted_pair = pair.split("==")
            out_dict[splitted_pair[0]] = splitted_pair[1]
        return out_dict
    # End should be removed


    @api.multi
    def do_detailed_transfer(self):
        for record in self:
            if record.picking_id.auto_stock_carrier and record.picking_id.dhl_check:
                parcels = 0
                sender = None
                # changed to sender all time amamedis
                # if need of single warehouse each time need to be fixed in the lines below because of no partner in source_loc while dropshipping
                company = record.picking_id.company_id
                sender = company.partner_id
                
                # Get number of parcels to send
                # _logger.info(str(record.item_ids))
                for item in record.item_ids:
                    _logger.info(item.product_id.pcs_per_box)
                    if item.product_id.pcs_per_box != 0:
                        # Get sender address
                        '''if not sender:
                            if record.picking_id.picking_type_id and record.picking_id.picking_type_id.id == record.env['ir.model.data'].get_object_reference('stock_dropshipping', 'picking_type_dropship')[1]:
                                sender = record.picking_id.partner_id
                            else:
                                sender = item.sourceloc_id.partner_id'''
                        quantity = float(item.quantity) / item.product_uom_id.factor
                        pcs_per_box = float(item.product_id.pcs_per_box) / item.product_id.uom_id.factor
                        parcels += int(ceil(quantity / pcs_per_box))
                        _logger.info('quantity: ' + str(quantity) + ' pcs_per_box: ' + str(pcs_per_box) + ' parcels: ' + str(parcels))
                    else:
                        if item.product_id.name:
                            _logger.error(('Fehler'), ('Fuer das Produkt \"' + item.product_id.name.encode('utf-8') + '\" ist keine Gebindegroesse hinterlegt.'))
                # Error handling
                if parcels == 0:
                    _logger.error(('Fehler'), ('Die Anzahl der berechneten Pakete ist null!'))
                if not sender:
                    _logger.error(('Fehler'), ('Absender für die Pakete konnte nicht gesetzt werden. Bitte Route waehlen, bzw. Eigentuemer des Lagers setzen von dem Versand wird.'))
                if (sender.street == '' or sender.city == '' or sender.zip == ''):
                    _logger.error(('DHL Versand'), ('Absendeadresse (Eigentümer des Lagers) ist unvollstaendig.'))
                if not company.oc_local_dir:
                    _logger.error('DHL Versand Einstellungen','Bitte lokales owncloud Verzeichnis angeben.')
                                
                receiver = record.picking_id.delivery_address_id
                # receiver = record.picking_id.move_lines[0].partner_id
                if not receiver:
                    _logger.error(('Fehler'), ('Empfaenger für die Pakete konnte nicht gesetzt werden. Ursache: Lieferschein enthaelt keine Auftragszeilen oder diesen ist kein Empfaenger zugeordnet.'))
                if (receiver.street == '' or receiver.city == '' or receiver.zip == ''):
                    _logger.error(('DHL Versand'), ('Lieferadresse ist unvollstaendig.')) 

                # Prepare call of Java tool
                
                # Set arguments
                vals = {
                        # Receiver details
                        constants_dhl.RC_CONTACT_EMAIL : receiver.dhl_email and receiver.dhl_email.strip(),
                        constants_dhl.RC_CONTACT_PHONE : receiver.dhl_phone and receiver.dhl_phone.strip(),
                        # constants_dhl.RC_COMPANY_NAME : (receiver.is_company and receiver.dhl_name1 and receiver.dhl_name1.strip()) or (receiver.parent_id and receiver.parent_id.dhl_name1 and receiver.parent_id.dhl_name1.strip()),
                        # constants_dhl.RC_COMPANY_NAME_2 : not receiver.is_company and receiver.dhl_name2 and receiver.dhl_name2.strip(),
                        constants_dhl.RC_COMPANY_NAME : receiver.dhl_name1 and receiver.dhl_name1.strip(),
                        constants_dhl.RC_COMPANY_NAME_2 : receiver.dhl_name2 and receiver.dhl_name2.strip(),
                        constants_dhl.RC_LOCAL_CITY : ((receiver.is_company or not receiver.use_parent_address) and receiver.dhl_city and receiver.dhl_city.strip()) or (receiver.parent_id and receiver.parent_id.dhl_city and receiver.parent_id.dhl_city.strip()),
                        constants_dhl.RC_LOCAL_STREET : ((receiver.is_company or not receiver.use_parent_address) and receiver.dhl_streetName and receiver.dhl_streetName.strip()) or (receiver.parent_id and receiver.parent_id.dhl_streetName and receiver.parent_id.dhl_streetName.strip()),
                        constants_dhl.RC_LOCAL_STREETNR : ((receiver.is_company or not receiver.use_parent_address) and receiver.dhl_streetNumber and receiver.dhl_streetNumber.strip()) or (receiver.parent_id and receiver.parent_id.dhl_streetNumber and receiver.parent_id.dhl_streetNumber.strip()),
                        constants_dhl.RC_LOCAL_ZIP : ((receiver.is_company or not receiver.use_parent_address) and receiver.dhl_zip and receiver.dhl_zip.strip()) or (receiver.parent_id and receiver.parent_id.dhl_zip and receiver.parent_id.dhl_zip.strip()),
                        constants_dhl.NUMBER_OF_SHIPMENTS : str(parcels),
                        constants_dhl.CUSTOMER_REFERENCE : record.picking_id.name and record.picking_id.name.strip(),
                        # Sender details
                        constants_dhl.SH_COMPANY_NAME : sender.dhl_name1 and sender.dhl_name1.strip(),
                        constants_dhl.SH_STREET : sender.dhl_streetName and sender.dhl_streetName.strip(),
                        constants_dhl.SH_STREET_NR : sender.dhl_streetNumber and sender.dhl_streetNumber.strip(),
                        constants_dhl.SH_CITY : sender.dhl_city and sender.dhl_city.strip(),
                        constants_dhl.SH_ZIP : sender.dhl_zip and sender.dhl_zip.strip(),
                        constants_dhl.SH_CONTACT_EMAIL : sender.dhl_email and sender.dhl_email.strip(),
                        constants_dhl.SH_CONTACT_PHONE : sender.dhl_phone and sender.dhl_phone.strip(),
                        # Options and Credentials
                        constants_dhl.METHOD : 'createShipment',
                        constants_dhl.TEST : company.dhl_test and 'True' or False,
                        constants_dhl.INTRASHIP_USER : (company.dhl_test and company.dhl_order_intraship_user_test) or company.dhl_order_intraship_user,
                        constants_dhl.INTRASHIP_PASSWORD : (company.dhl_test and company.dhl_order_intraship_password_test) or company.dhl_order_intraship_password,
                        constants_dhl.EKP : company.dhl_order_ekp,
                        constants_dhl.PARTNER_ID : company.dhl_order_partner_id,
                        }
                # _logger.info("Anfrage nach Zusammenbau: " + str(vals))
                arguments = record._assamble_shipment_arguments(vals)
                _logger.info("Anfrage (Latin-1) an JAVA: " + str(arguments))
                # print arguments
                # Call Java program
                program_name = "./dhl.jar"
                command = ["java", "-jar", "./dhl.jar"]
                command.extend(arguments)
                # _logger.info(str(command))
                out, err = Popen(command, stdin=PIPE, stdout=PIPE,
                        stderr=PIPE, cwd="/opt/dhl").communicate()
                # Raise error if we get content in stderr
                
                _logger.info("Antwort JAVA (DHL): " + str(out))
                if err != '':
                    _logger.error('DHL Versand - Java', err)
                else:
                    # Parse output from Java tool
                    splitted_output = out.split('\n')
                    # Open PDF for merging DHL delivery slips to one file
                    pdf = PyPDF2.PdfFileMerger()
                    for line in splitted_output:
                        # Get DHL deliveries
                        if '==' in line:
                            splitted_line = line.split("==")
                            shipment_number = splitted_line[0]
                            shipment_url = splitted_line[1]
                            # Create new dhl delivery object
                            picking_unit = record.env['stock.dm.picking.unit'].create({
                                'code' : shipment_number,
                                'stock_picking_id' : record.picking_id.id,
                                'delivery_carrier_id' : record.picking_id.carrier_id.id,
                                })
                            dhl_picking_unit = record.env['stock.dhl.picking.unit'].create({
                                'name' : shipment_number,
                                'stock_dm_picking_unit_id' : picking_unit.id
                                })
                            picking_unit.update({
                                'delivery_carrier_res_id' : dhl_picking_unit.id
                                })
                            # Download PDF and merge
                            path = "/opt/dhl/pdf/" + shipment_number + ".pdf"
                            try:
                                urllib.urlretrieve(shipment_url, path)
                                pdf.append(PyPDF2.PdfFileReader(path, 'rb'))
                            except:
                                _logger.error('DHL Versand', 'Konnte DHL Sendeschein nicht als PDF herunterladen. Ist das Verzeichnis /opt/dhl/pdf fuer den odoo Benutzer schreibbar und  vorhanden?\nURL: ' + shipment_url)
                    # Check for status message
                        if '::' in line:
                            splitted_line = line.split("::")
                            status_code = splitted_line[0]
                            status_message = splitted_line[1]
                            if not status_code == '0':
                                _logger.error('DHL Versand - Java',
                                        status_message)
                    # Close PDF file and save
                    filename = record.picking_id.name + "-DHL.pdf"
                    filename = filename.replace('/','_')
                    path = "/opt/dhl/pdf/" + filename
                    try:
                        pdf.write(path)
                    except:
                        res = {'warning': {
                                          'title': _('Warnung'),
                                          'message': _('Konnte Sammelpdf nicht speichern. Pfad: ' + path)
                                          }
                              }
                        return res
                    # Add PDF as attachment to delivery note
                    try:
                        attach_id = record.env['ir.attachment'].create({
                            'name':filename,
                            'res_name': filename,
                            'type': 'binary',
                            'res_model': 'stock.picking',
                            'res_id': record.picking_id.id,
                            'datas': base64.b64encode(open(path, 'rb').read()),
                        })
                        record.picking_id.carrier_label = attach_id
                    except:
                        res = {'warning': {
                                          'title': _('Warnung'),
                                          'message': _('Konnte PDF nicht als Attachment hinzufügen.')
                                          }
                              }
                        return res
                    # Copy pdf to synced owncloud directory
                    if not company.oc_local_dir[:-1] == '/':
                        oc_path = company.oc_local_dir + '/'
                    else:
                        oc_path = company.oc_local_dir
                    # Get name of the year and supplier name
                    # year = datetime.datetime.now().strftime('%Y')
                    # supplier = sender.name.replace(' ','_').replace('/','_')
                    # oc_path += year + '/' + supplier + '/DHL_Sendescheine/unversendet/'
                    # Make directory if not existing
                    try:
                        # os.makedirs(oc_path)
                        os.makedirs(company.oc_local_dir)
                    except OSError as exception:
                        if exception.errno != errno.EEXIST:
                            msg = 'Konnte Verzeichnis nicht erstellen \'' + oc_path
                            res = {'warning': {
                                                'title': _('Warnung'),
                                                'message': msg,
                                              }
                                  }
                            return res
                    # if os.path.isdir(oc_path):
                    if os.path.isdir(company.oc_local_dir):
                        # Copy pdf to owncloud directory
                        shutil.copy(path, company.oc_local_dir)
                        # Sync owncloud
                        command = ['owncloudcmd']
                        # Arguments
                        arguments = [
                                '-u', company.oc_user,
                                '-p', company.oc_password,
                                company.oc_local_dir,
                                company.oc_remote_dir
                                ]
                        command.extend(arguments)
                        # Execute owncloud syncing
                        out, err = Popen(command, stdin=PIPE, stdout=PIPE,
                                stderr=PIPE).communicate()

        # Call super method
        super(ama_del_stock_transfer_details, self).do_detailed_transfer()
        return True