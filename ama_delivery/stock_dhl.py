# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning
from requests.auth import HTTPBasicAuth
from datetime import datetime
from subprocess import Popen, PIPE

import logging
import binascii
import pytz
import requests
import time
import xmltodict
import HTMLParser

import constants_dhl

from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds.plugin import MessagePlugin
from suds.wsse import *

h = HTMLParser.HTMLParser()

_logger = logging.getLogger(__name__)

logging.getLogger('suds').setLevel(logging.WARNING) #WARNING
logging.getLogger('suds.client').setLevel(logging.DEBUG)
logging.getLogger('suds.transport').setLevel(logging.DEBUG)


class stock_dhl_picking_unit(models.Model):
    _name = 'stock.dhl.picking.unit'
    '''DHL-gebrandete Sendung'''
    
    name = fields.Char(string='Name', help='Sendungsnummer', required=True)
    stock_dhl_ice_id = fields.Many2one('stock.dhl.ice', ondelete='restrict', string="ICE", readonly=True, store=True) #, compute='_compute_ice'
    stock_dhl_ric_id = fields.Many2one('stock.dhl.ric', ondelete='restrict', string="RIC", compute='_compute_ric', readonly=True, store=True)
    stock_dhl_ttpro_id = fields.Many2one('stock.dhl.ttpro', ondelete='restrict', string="TTpro", compute='_compute_ttpro', readonly=True, store=True)
    stock_dm_picking_unit_id = fields.Many2one('stock.dm.picking.unit', string='Sendung', ondelete='restrict', help='Zugehoerige interne Sendung', store=True,) # required=True)
    stock_dm_state_id = fields.Many2one('stock.dm.state', string='Status der Lieferung', ondelete='restrict', readonly=True, store=True, default=lambda self: self.env['stock.dm.state'].search([('sequence','=','10')], limit=1)) #, compute='_compute_stock_dm_state_id'
    image = fields.Binary(string="Signature", compute='_compute_image', readonly=True, store=True)
    stock_dhl_event_ids = fields.One2many(comodel_name='stock.dhl.event', inverse_name='stock_dhl_picking_unit_id', string="Events")
    stock_dhl_event_ids_2 = fields.One2many(comodel_name='stock.dhl.event', inverse_name='stock_dhl_picking_unit_id', string="DHL Events")
    partner_id = fields.Many2one('res.partner', string='Lieferkontakt', related='stock_dm_picking_unit_id.partner_id', help='Lieferkontakt bzw. -adresse der Sendung', store=True, readonly=True)
    error = fields.Char(string='Fehlermeldung')
    error_occurred = fields.Boolean(default=False)
    stock_dhl_status_id = fields.Many2one('stock.dhl.status', ondelete='restrict', string="DHL Status", compute='_compute_status', readonly=True, store=True)
    auto_tracking = fields.Boolean(string='Automatische Sendungsverfolgung', default=True, help='Legt fest ob die Sendung weiterhin verfolgt wird')
    error_counter = fields.Integer(string='Anzahl Tracking-Fehler', default=False, help='Erreicht der Zaehler 5 wird nicht mehr automatisch getrackt.')
    ownership = fields.Boolean(string='Eigene Sendung', default=False, help='Legt fest, mit welcher Methode die Sendung verfolgt wird, da es hier Unterschiede zwischen eigenen und fremden Sendungen gibt.')
    
    stock_dhl_ice_code = fields.Char(related='stock_dhl_ice_id.code', string="ICE-Code", readonly=True)
    stock_dhl_ice_text = fields.Char(related='stock_dhl_ice_id.text', string="ICE-Text", readonly=True)
    stock_dhl_ric_code = fields.Char(related='stock_dhl_ric_id.code', string="RIC-Code", readonly=True)
    stock_dhl_ric_text = fields.Char(related='stock_dhl_ric_id.text', string="RIC-Text", readonly=True)
    stock_dhl_ttpro_code = fields.Char(related='stock_dhl_ttpro_id.code', string="TTpro-Code", readonly=True)
    stock_dhl_ttpro_text = fields.Char(related='stock_dhl_ttpro_id.text', string="TTpro-Text", readonly=True)
    stock_dhl_status_text = fields.Char(related='stock_dhl_status_id.text', string="Status-Text", readonly=True)
    new_image_received = fields.Boolean(default=False)
    
    # not displayed fields
    # DHL response fields
    dhl_airway_bill_number = fields.Char(string="airway-bill-number")
    dhl_code = fields.Char(string="code")
    dhl_delivery_event_flag = fields.Char(string="delivery-event-flag", default='0')
    dhl_dest_country = fields.Char(string="dest-country")
    dhl_division = fields.Char(string="division")
    dhl_domestic_id = fields.Char(string="domestic-id")
    dhl_error = fields.Char(string="error")
    dhl_error_status = fields.Char(string="error-status")
    dhl_event_country = fields.Char(string="event-country")
    dhl_event_location = fields.Char(string="event-location")
    dhl_ice = fields.Char(string="ice")
    dhl_identifier_type = fields.Char(string="identifier-type")
    dhl_international_flag = fields.Char(string="international-flag")
    dhl_leitcode = fields.Char(string="leitcode")
    dhl_matchcode = fields.Char(string="matchcode")
    dhl_order_preferred_delivery_date = fields.Char(string="order-preferred-delivery_date")
    dhl_origin_country = fields.Char(string="origin-country")
    dhl_pan_recipient_address = fields.Char(string="pan-recipient-address")
    dhl_pan_recipient_city = fields.Char(string="pan-recipient-city")
    dhl_pan_recipient_name = fields.Char(string="pan-recipient-name")
    dhl_pan_recipient_postalcode = fields.Char(string="pan-recipient-postalcode")
    dhl_pan_recipient_street = fields.Char(string="pan-recipient-street")
    dhl_piece_code = fields.Char(string="piece-code")
    dhl_piece_customer_reference = fields.Char(string="piece-customer-reference")
    dhl_piece_id = fields.Char(string="piece-id")
    dhl_piece_identifier = fields.Char(string="piece-identifier")
    dhl_product_code = fields.Char(string="product-code")
    dhl_product_key = fields.Char(string="product-key")
    dhl_product_name = fields.Char(string="product-name")
    dhl_pslz_nr = fields.Char(string="pslz-nr")
    dhl_recipient_city = fields.Char(string="recipient-city")
    dhl_recipient_id = fields.Char(string="recipient-id")
    dhl_recipient_id_text = fields.Char(string="recipient-id-text")
    dhl_recipient_name = fields.Char(string="recipient-name")
    dhl_recipient_street = fields.Char(string="recipient-street")
    dhl_ric = fields.Char(string="ric")
    dhl_routing_code_ean = fields.Char(string="routing-code-ean")
    dhl_ruecksendung = fields.Char(string="ruecksendung")
    dhl_searched_piece_code = fields.Char(string="searched-piece-code")
    dhl_searched_ref_no = fields.Char(string="searched-ref-no")
    dhl_shipment_code = fields.Char(string="shipment-code")
    dhl_shipment_customer_reference = fields.Char(string="shipment-customer-reference")
    dhl_shipment_height = fields.Char(string="shipment-height")
    dhl_shipment_length = fields.Char(string="shipment-length")
    dhl_shipment_weight = fields.Char(string="shipment-weight")
    dhl_shipment_width = fields.Char(string="shipment-width")
    dhl_shipper_address = fields.Char(string="shipper-address")
    dhl_shipper_city = fields.Char(string="shipper-city")
    dhl_shipper_name = fields.Char(string="shipper-name")
    dhl_shipper_street = fields.Char(string="shipper-street")
    dhl_short_status = fields.Char(string="short-status")
    dhl_standard_event_code = fields.Char(string="standard-event-code")
    dhl_status = fields.Char(string="status")
    dhl_status_liste = fields.Char(string="status-liste")
    dhl_status_timestamp = fields.Char(string="status-timestamp")
    dhl_upu = fields.Char(string="upu")
    dhl_image = fields.Text(string="signature")
    dhl_image_event_date = fields.Char(string="signature-event-date")
    dhl_image_mime_type = fields.Char(string="signature-mime-type")
    
    _sql_constraints = [
            ('name_unique',
             'UNIQUE(name)',
             "Sendungen sind einmalig und koennen nicht dupliziert werden.\nFalls es sich um eine regulaere Sendung handelt, pruefen Sie ob Ihr Ihnen zugewiesener Nummernpool zu klein ist."),
            ]
    
    '''@api.multi
    @api.depends('dhl_ice')
    def _compute_ice(self):
        for record in self:
            record.stock_dhl_ice_id = self.env['stock.dhl.ice'].search([('code','=',record.dhl_ice)], limit=1)
            _logger.debug(len(record.stock_dm_state_id))
            _logger.debug(record.stock_dm_state_id)
            if not record.stock_dm_state_id or record.stock_dhl_ice_id.stock_dm_state_id.sequence > record.stock_dm_state_id.sequence:
                #record.stock_dm_state_id = record.stock_dhl_ice_id.stock_dm_state_id
                record.write({'stock_dm_state_id': record.stock_dhl_ice_id.stock_dm_state_id.id})
                _logger.debug('Hier bin ich')
                _logger.debug(record.stock_dm_state_id)'''
    
    '''@api.multi
    @api.onchange('dhl_ice')
    def _onchange_dhl_ice(self):
        for record in self:
            _logger.debug('Neuer ICE-Code?')
            _logger.debug(record.stock_dhl_ice_id)
            record.stock_dhl_ice_id = self.env['stock.dhl.ice'].search([('code','=',self.dhl_ice)], limit=1)
            _logger.debug(record.stock_dhl_ice_id)
            if record.stock_dhl_ice_id and record.stock_dhl_ice_id.stock_dm_state_id:
                if not record.stock_dm_state_id:
                    record.stock_dm_state_id = record.stock_dhl_ice_id.stock_dm_state_id
                else:
                    if record.stock_dm_state_id.sequence and (record.stock_dm_state_id.sequence == 70 or (record.stock_dhl_ice_id.stock_dm_state_id.sequence and record.stock_dm_state_id.sequence < record.stock_dhl_ice_id.stock_dm_state_id.sequence)):
                        record.stock_dm_state_id = record.stock_dhl_ice_id.stock_dm_state_id'''

    @api.multi
    @api.depends('dhl_ric')
    def _compute_ric(self):
        for record in self:
            record.stock_dhl_ric_id = self.env['stock.dhl.ric'].search([('code','=',record.dhl_ric)], limit=1)

    @api.multi
    @api.depends('dhl_standard_event_code')
    def _compute_ttpro(self):
        for record in self:
            record.stock_dhl_ttpro_id = self.env['stock.dhl.ttpro'].search([('code','=',record.dhl_standard_event_code)], limit=1)

    @api.multi
    @api.depends('dhl_image')
    def _compute_image(self):
        for record in self:
            if record.dhl_image:
                record.image = binascii.b2a_base64(binascii.a2b_hex(record.dhl_image))
                
    @api.multi
    @api.depends('dhl_code')
    def _compute_status(self):
        for record in self:
            if record.dhl_code:
                record.stock_dhl_status_id = self.env['stock.dhl.status'].search([('code','=',record.dhl_code)], limit=1)

    '''@api.multi
    @api.depends('stock_dhl_ice_id')
    def _compute_stock_dm_state_id(self):
        for record in self:
            if not record.stock_dm_state_id or record.stock_dhl_ice_id.stock_dm_state_id.sequence > record.stock_dm_state_id.sequence:
                _logger.debug(record.stock_dm_state_id)
                record.stock_dm_state_id = record.stock_dhl_ice_id.stock_dm_state_id
                _logger.debug(record.stock_dm_state_id)'''
                
    @api.multi
    @api.onchange('stock_dm_state_id')
    def _onchange_stock_dm_state_id(self):
        for record in self:
            if record.stock_dm_picking_unit_id:
                record.stock_dm_picking_unit_id.stock_dm_state_id = record.stock_dm_state_id
                
    @api.multi
    @api.onchange('stock_dhl_status_id')
    def _onchange_stock_dhl_status_id(self):
        for record in self:
            if record.stock_dhl_status_id:
                if record.stock_dhl_status_id.code != '0':
                    record.error = record.stock_dhl_status_id.name
                else:
                    record.error = ''
    
    @api.multi
    @api.onchange('error_counter')
    def _onchange_error_counter(self):
        for record in self:
            _logger.debug('Bin ich hier?')
            if record.error_counter >= 5:
                record.auto_tracking = False
            else:
                record.auto_tracking = True
    
    '''@api.multi
    @api.onchange('stock_dm_picking_unit_id')
    def _onchange_stock_dm_picking_unit(self):
        for record in self:
            if record.stock_dm_picking_unit_id:
                record.stock_dm_picking_unit_id.delivery_carrier_res_id = record.NewId
                raise except_orm('TEST',record.NewId)'''
    
    @api.multi
    def raise_id(self):
        for record in self:
            if record.stock_dm_picking_unit_id:
                record.stock_dm_picking_unit_id.delivery_carrier_res_id = record.id
                
    @api.model
    def synchronize_cron(self):
        _logger.info('Ich bins der CronJob')
        
        # get all undelivered packages
        ids = self.search([('dhl_delivery_event_flag', '!=', '1')])
        _logger.info(str(ids))
        ids.tracking()
        
        # get all delivered packages without image received
        ids = self.search([('dhl_delivery_event_flag', '=', '1'),('dhl_dest_country', '=', 'DE'),('dhl_image', '=', False)])
        _logger.info(str(ids))
        ids.tracking()
        
            
    
    @api.multi
    def tracking(self):
        for record in self:
        
            language_code = "de"
            sleep_time = (record.stock_dm_picking_unit_id.stock_picking_id.company_id.sandbox_dhl and 10) or 1
            try:
                piece_code = record.name
            except Exception as e:
                raise e
            test = record.stock_dm_picking_unit_id.stock_picking_id.company_id.sandbox_dhl
            if test:
                endpoint = record.stock_dm_picking_unit_id.stock_picking_id.company_id.endpoint_track_dhl_test
                appname = record.stock_dm_picking_unit_id.stock_picking_id.company_id.zt_user_dhl_test
                password = record.stock_dm_picking_unit_id.stock_picking_id.company_id.zt_pass_dhl_test
                cig_user = record.stock_dm_picking_unit_id.stock_picking_id.company_id.cig_user_dhl_test
                cig_pass = record.stock_dm_picking_unit_id.stock_picking_id.company_id.cig_pass_dhl_test
            else:
                endpoint = record.stock_dm_picking_unit_id.stock_picking_id.company_id.endpoint_track_dhl
                appname = record.stock_dm_picking_unit_id.stock_picking_id.company_id.zt_user_dhl
                password = record.stock_dm_picking_unit_id.stock_picking_id.company_id.zt_pass_dhl
                cig_user = record.stock_dm_picking_unit_id.stock_picking_id.company_id.cig_user_dhl
                cig_pass = record.stock_dm_picking_unit_id.stock_picking_id.company_id.cig_pass_dhl
                
            if record.dhl_delivery_event_flag != '1' and record.auto_tracking:
        
                method = "d-get-piece-detail"
                #method = "get-status-for-public-user"
                xml_response = ''
                xml_response_dict = ''

                request = '<?xml version="1.0" encoding="UTF-8"?><data '
                request += constants_dhl.APPNAME + '=\"' + appname + '\" '
                request += constants_dhl.PASSWORD + '=\"' + password + '\" '
                request += constants_dhl.LANGUAGE_CODE + '=\"' + language_code + '\" '
                request += constants_dhl.REQUEST + '=\"' + method + '\" '

                #request += '><data '
                request += constants_dhl.PIECE_CODE + '=\"' + piece_code + '\"/>'
                #request += '</data>'
                
                headers = {'Content-Type': 'text/xml'}
                payload = {'xml': request}

                _logger.info(request)
                
                try:
                    r = requests.get(endpoint, params=payload, auth=HTTPBasicAuth(cig_user, cig_pass), headers=headers)

                    if r.status_code == 200:
                        r.encoding = "utf-8"
                        xml_response = r.text
                        _logger.info(xml_response)
                    else:
                        record.error_occurred = True
                        record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                        record.error = "Fehler beim Tracking der DHL Sendung '" + str(record.name) + "'. Server sendet Statuscode " + str(r.status_code) + " mit Inhalt: '" + str(r.text) + "'."
                        _logger.error("Fehler beim Tracking der DHL Sendung '" + str(record.name) + "'. Server sendet Statuscode " + str(r.status_code) + " mit Inhalt: '" + str(r.text) + "'.")
                        record.stock_dm_state_id = self.env.ref('ama_delivery.dms70').id
                        if record.error_counter >= 5:
                            record.auto_tracking = False
                        else:
                            record.auto_tracking = True

                except Exception as e:
                    record.error_occurred = True
                    record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                    record.error = "Fehler beim Tracking der DHL Sendung '" + str(record.name) + "'. HTTP-Request fehlgeschlagen: " + str(e)
                    _logger.error("Fehler beim Tracking der DHL Sendung '" + str(record.name) + "'. HTTP-Request fehlgeschlagen: " + str(e))
                    record.stock_dm_state_id = self.env.ref('ama_delivery.dms70').id
                    if record.error_counter >= 5:
                        record.auto_tracking = False
                    else:
                        record.auto_tracking = True


                if xml_response.startswith('<?xml'):
                    # XML parsen
                    xml_response_dict = xmltodict.parse(xml_response)
                    
                    record.dhl_code = xml_response_dict['data']['@' + constants_dhl.CODE]
                    
                    if record.dhl_code != '0':
                        record.error_occurred = True
                        record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                        record.dhl_error = xml_response_dict['data']['@' + constants_dhl.ERROR]
                        record.error = record.dhl_error
                        _logger.error(record.dhl_code + ": " + xml_response_dict['data']['@' + constants_dhl.ERROR])
                        record.stock_dm_state_id = self.env.ref('ama_delivery.dms70').id
                        if record.error_counter >= 5:
                            record.auto_tracking = False
                        else:
                            record.auto_tracking = True
                    else:
                        record.error_occurred = False
                        record.error_counter = False
                        record.error = ''
                        record.dhl_airway_bill_number = xml_response_dict['data']['data']['@' + constants_dhl.AIRWAY_BILL_NUMBER]
                        record.dhl_delivery_event_flag = xml_response_dict['data']['data']['@' + constants_dhl.DELIVERY_EVENT_FLAG]
                        record.dhl_dest_country = xml_response_dict['data']['data']['@' + constants_dhl.DEST_COUNTRY]
                        record.dhl_division = xml_response_dict['data']['data']['@' + constants_dhl.DIVISION]
                        record.dhl_domestic_id = xml_response_dict['data']['data']['@' + constants_dhl.DOMESTIC_ID]
                        record.dhl_error_status = xml_response_dict['data']['data']['@' + constants_dhl.ERROR_STATUS]
                        record.dhl_event_country = xml_response_dict['data']['data']['@' + constants_dhl.EVENT_COUNTRY]
                        record.dhl_event_location = xml_response_dict['data']['data']['@' + constants_dhl.EVENT_LOCATION]
                        record.dhl_ice = xml_response_dict['data']['data']['@' + constants_dhl.ICE]
                        record.dhl_identifier_type = xml_response_dict['data']['data']['@' + constants_dhl.IDENTIFIER_TYPE]
                        record.dhl_international_flag = xml_response_dict['data']['data']['@' + constants_dhl.INTERNATIONAL_FLAG]
                        record.dhl_leitcode = xml_response_dict['data']['data']['@' + constants_dhl.LEITCODE]
                        record.dhl_matchcode = xml_response_dict['data']['data']['@' + constants_dhl.MATCHCODE]
                        record.dhl_order_preferred_delivery_date = xml_response_dict['data']['data']['@' + constants_dhl.ORDER_PREFERRED_DELIVERY_DAY]
                        record.dhl_origin_country = xml_response_dict['data']['data']['@' + constants_dhl.ORIGIN_COUNTRY]
                        record.dhl_pan_recipient_address = xml_response_dict['data']['data']['@' + constants_dhl.PAN_RECIPIENT_ADDRESS]
                        record.dhl_pan_recipient_city = xml_response_dict['data']['data']['@' + constants_dhl.PAN_RECIPIENT_CITY]
                        record.dhl_pan_recipient_name = xml_response_dict['data']['data']['@' + constants_dhl.PAN_RECIPIENT_NAME]
                        record.dhl_pan_recipient_postalcode = xml_response_dict['data']['data']['@' + constants_dhl.PAN_RECIPIENT_POSTALCODE]
                        record.dhl_pan_recipient_street = xml_response_dict['data']['data']['@' + constants_dhl.PAN_RECIPIENT_STREET]
                        record.dhl_piece_code = xml_response_dict['data']['data']['@' + constants_dhl.PIECE_CODE]
                        record.dhl_piece_customer_reference = xml_response_dict['data']['data']['@' + constants_dhl.PIECE_CUSTOMER_REFERENCE]
                        record.dhl_piece_id = xml_response_dict['data']['data']['@' + constants_dhl.PIECE_ID]
                        record.dhl_piece_identifier = xml_response_dict['data']['data']['@' + constants_dhl.PIECE_IDENTIFIER]
                        record.dhl_product_code = xml_response_dict['data']['data']['@' + constants_dhl.PRODUCT_CODE]
                        record.dhl_product_key = xml_response_dict['data']['data']['@' + constants_dhl.PRODUCT_KEY]
                        record.dhl_product_name = xml_response_dict['data']['data']['@' + constants_dhl.PRODUCT_NAME]
                        record.dhl_pslz_nr = xml_response_dict['data']['data']['@' + constants_dhl.PSLZ_NR]
                        record.dhl_recipient_city = xml_response_dict['data']['data']['@' + constants_dhl.RECIPIENT_CITY]
                        record.dhl_recipient_id = xml_response_dict['data']['data']['@' + constants_dhl.RECIPIENT_ID]
                        record.dhl_recipient_id_text = xml_response_dict['data']['data']['@' + constants_dhl.RECIPIENT_ID_TEXT]
                        record.dhl_recipient_name = xml_response_dict['data']['data']['@' + constants_dhl.RECIPIENT_NAME]
                        record.dhl_recipient_street = xml_response_dict['data']['data']['@' + constants_dhl.RECIPIENT_STREET]
                        record.dhl_ric = xml_response_dict['data']['data']['@' + constants_dhl.RIC]
                        record.dhl_routing_code_ean = xml_response_dict['data']['data']['@' + constants_dhl.ROUTING_CODE_EAN]
                        record.dhl_ruecksendung = xml_response_dict['data']['data']['@' + constants_dhl.RUECKSENDUNG]
                        record.dhl_searched_piece_code = xml_response_dict['data']['data']['@' + constants_dhl.SEARCHED_PIECE_CODE]
                        record.dhl_searched_ref_no = xml_response_dict['data']['data']['@' + constants_dhl.SEARCHED_REF_NO]
                        record.dhl_shipment_code = xml_response_dict['data']['data']['@' + constants_dhl.SHIPMENT_CODE]
                        record.dhl_shipment_customer_reference = xml_response_dict['data']['data']['@' + constants_dhl.SHIPMENT_CUSTOMER_REFERENCE]
                        record.dhl_shipment_height = xml_response_dict['data']['data']['@' + constants_dhl.SHIPMENT_HEIGHT]
                        record.dhl_shipment_length = xml_response_dict['data']['data']['@' + constants_dhl.SHIPMENT_LENGTH]
                        record.dhl_shipment_weight = xml_response_dict['data']['data']['@' + constants_dhl.SHIPMENT_WEIGHT]
                        record.dhl_shipment_width = xml_response_dict['data']['data']['@' + constants_dhl.SHIPMENT_WIDTH]
                        record.dhl_shipper_address = xml_response_dict['data']['data']['@' + constants_dhl.SHIPPER_ADDRESS]
                        record.dhl_shipper_city = xml_response_dict['data']['data']['@' + constants_dhl.SHIPPER_CITY]
                        record.dhl_shipper_name = xml_response_dict['data']['data']['@' + constants_dhl.SHIPPER_NAME]
                        record.dhl_shipper_street = xml_response_dict['data']['data']['@' + constants_dhl.SHIPPER_STREET]
                        record.dhl_short_status = xml_response_dict['data']['data']['@' + constants_dhl.SHORT_STATUS]
                        record.dhl_standard_event_code = xml_response_dict['data']['data']['@' + constants_dhl.STANDARD_EVENT_CODE]
                        record.dhl_status = xml_response_dict['data']['data']['@' + constants_dhl.STATUS]
                        record.dhl_status_liste = xml_response_dict['data']['data']['@' + constants_dhl.STATUS_LISTE]
                        record.dhl_status_timestamp = xml_response_dict['data']['data']['@' + constants_dhl.STATUS_TIMESTAMP]
                        record.dhl_upu = xml_response_dict['data']['data']['@' + constants_dhl.UPU]

                        eventlist = xml_response_dict['data']['data']['data']['data']
                        if not isinstance(eventlist, list) and isinstance(eventlist, dict):
                            eventlist = [eventlist]
                        
                        for dhl_event in eventlist:
                            count = self.env['stock.dhl.event'].search_count([('stock_dhl_picking_unit_id','=',record.id),('dhl_event_timestamp','=',dhl_event['@' + constants_dhl.EVENT_TIMESTAMP])])
                            if count == 0:
                                self.env['stock.dhl.event'].create({
                                    'stock_dhl_picking_unit_id': record.id,
                                    'dhl_event_country': dhl_event['@' + constants_dhl.EVENT_COUNTRY],
                                    'dhl_event_location': dhl_event['@' + constants_dhl.EVENT_LOCATION],
                                    'dhl_event_status': dhl_event['@' + constants_dhl.EVENT_STATUS],
                                    'dhl_event_text': dhl_event['@' + constants_dhl.EVENT_TEXT],
                                    'dhl_event_timestamp': dhl_event['@' + constants_dhl.EVENT_TIMESTAMP],
                                    'dhl_ice': dhl_event['@' + constants_dhl.ICE],
                                    'dhl_ric': dhl_event['@' + constants_dhl.RIC],
                                    'dhl_ruecksendung': dhl_event['@' + constants_dhl.RUECKSENDUNG],
                                    'dhl_standard_event_code': dhl_event['@' + constants_dhl.STANDARD_EVENT_CODE],
                                })
                        
                        record.stock_dhl_ice_id = self.env['stock.dhl.ice'].search([('code','=',record.dhl_ice)], limit=1)
                        if record.stock_dhl_ice_id and record.stock_dhl_ice_id.stock_dm_state_id:
                            if not record.stock_dm_state_id:
                                record.stock_dm_state_id = record.stock_dhl_ice_id.stock_dm_state_id
                            else:
                                if record.stock_dm_state_id.sequence and (record.stock_dm_state_id.sequence == 70 or (record.stock_dhl_ice_id.stock_dm_state_id.sequence and record.stock_dm_state_id.sequence < record.stock_dhl_ice_id.stock_dm_state_id.sequence)):
                                    record.stock_dm_state_id = record.stock_dhl_ice_id.stock_dm_state_id
                        

                elif xml_response.find('<B>SIM:</B>') != -1:
                    try:
                        errorsplit1 = xml_response.split('<B>SIM:</B>')
                        errorsplit2 = errorsplit1[1].split('</FONT>')
                        errormessage = errorsplit2[0].strip()
                        record.error_occurred = True
                        record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                        record.error = "Abfrage lieferte Fehlermeldung: " + h.unescape(errormessage)
                        _logger.error("Abfragefehler Tracking(Details) für DHL-Sendung '" + str(record.name) + "'. Abfrage lieferte Fehlermeldung: " + str(errormessage))
                        record.stock_dm_state_id = self.env.ref('ama_delivery.dms70').id
                        if record.error_counter >= 5:
                            record.auto_tracking = False
                        else:
                            record.auto_tracking = True
                    except Exception as e:
                        record.error_occurred = True
                        record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                        record.error = "Server sendet unübliche Fehlermeldung: " + h.unescape(xml_response)
                        _logger.error("Abfragefehler Tracking(Details) für DHL-Sendung '" + str(record.name) + "'. Server sendet unübliche Fehlermeldung: " + str(xml_response))
                        record.stock_dm_state_id = self.env.ref('ama_delivery.dms70').id
                        if record.error_counter >= 5:
                            record.auto_tracking = False
                        else:
                            record.auto_tracking = True
                else:
                    record.error_occurred = True
                    record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                    record.error = "Server-Antwort entspricht weder einer gültigen Antwort, noch einer üblichen Fehlermeldung: " + str(xml_response)
                    _logger.error("Abfragefehler Tracking(Details) für DHL-Sendung '" + str(record.name) + "'. Server-Antwort entspricht weder einer gültigen Antwort, noch einer üblichen Fehlermeldung: " + str(xml_response))
                    record.stock_dm_state_id = self.env.ref('ama_delivery.dms70').id
                    if record.error_counter >= 5:
                        record.auto_tracking = False
                    else:
                        record.auto_tracking = True
                    
            time.sleep(sleep_time)
            
            record.new_image_received = False
            if not record.dhl_image and record.dhl_delivery_event_flag == '1' and record.dhl_dest_country == 'DE' and record.auto_tracking:
                method = 'd-get-signature'
                xml_response = ''
                xml_response_dict = ''

                request = '<?xml version="1.0" encoding="UTF-8"?><data '
                request += constants_dhl.APPNAME + '=\"' + appname + '\" '
                request += constants_dhl.PASSWORD + '=\"' + password + '\" '
                request += constants_dhl.LANGUAGE_CODE + '=\"' + language_code + '\" '
                request += constants_dhl.REQUEST + '=\"' + method + '\" '

                request += constants_dhl.PIECE_CODE + '=\"' + piece_code + '\"/>'

                headers = {'Content-Type': 'text/xml'}
                payload = {'xml': request}

                _logger.info(request)

                try:
                    r = requests.get(endpoint, params=payload, auth=HTTPBasicAuth(cig_user, cig_pass), headers=headers)

                    if r.status_code == 200:
                        r.encoding = "utf-8"
                        xml_response = r.text
                        _logger.info(xml_response)
                    else:
                        record.error_occurred = True
                        record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                        record.error = "Fehler beim Abrufen des POD der DHL Sendung '" + str(record.name) + "'. Server sendet Statuscode " + str(r.status_code) + " mit Inhalt: '" + str(r.text) + "'."
                        _logger.error("Fehler beim Abrufen des POD der DHL Sendung '" + str(record.name) + "'. Server sendet Statuscode " + str(r.status_code) + " mit Inhalt: '" + str(r.text) + "'.")
                        record.stock_dm_state_id = self.env.ref('ama_delivery.dms70').id
                        if record.error_counter >= 5:
                            record.auto_tracking = False
                        else:
                            record.auto_tracking = True

                except Exception as e:
                    record.error_occurred = True
                    record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                    record.error = "Fehler beim Abrufen des POD der DHL Sendung '" + str(record.name) + "'. HTTP-Request fehlgeschlagen: " + str(e)
                    _logger.error("Fehler beim Abrufen des POD der DHL Sendung '" + str(record.name) + "'. HTTP-Request fehlgeschlagen: " + str(e))
                    record.stock_dm_state_id = self.env.ref('ama_delivery.dms70').id
                    if record.error_counter >= 5:
                        record.auto_tracking = False
                    else:
                        record.auto_tracking = True


                if xml_response.startswith('<?xml'):
                    # XML parsen
                    record.error_occurred = False
                    record.error_counter = False
                    record.error = ''
                    xml_response_dict = xmltodict.parse(xml_response)

                    record.dhl_image_event_date = xml_response_dict['data']['data']['@' + constants_dhl.EVENT_DATE]
                    record.dhl_image_mime_type = xml_response_dict['data']['data']['@' + constants_dhl.MIME_TYPE]
                    record.dhl_image = xml_response_dict['data']['data']['@' + constants_dhl.IMAGE]

                    record.new_image_received = True

                elif xml_response.find('<B>SIM:</B>') != -1:
                    try:
                        errorsplit1 = xml_response.split('<B>SIM:</B>')
                        errorsplit2 = errorsplit1[1].split('</FONT>')
                        errormessage = errorsplit2[0].strip()
                        record.error_occurred = True
                        record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                        record.error = "Abfrage lieferte Fehlermeldung (POD): " + h.unescape(errormessage)
                        _logger.error("Abfragefehler Tracking(POD) für DHL-Sendung '" + str(record.name) + "'. Abfrage lieferte Fehlermeldung: " + str(errormessage))
                        record.stock_dm_state_id = self.env.ref('ama_delivery.dms70').id
                        if record.error_counter >= 5:
                            record.auto_tracking = False
                        else:
                            record.auto_tracking = True
                    except Exception as e:
                        record.error_occurred = True
                        record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                        record.error = "Server sendet unübliche Fehlermeldung (POD): " + h.unescape(xml_response)
                        _logger.error("Abfragefehler Tracking(POD)für DHL-Sendung '" + str(record.name) + "'. Server sendet unübliche Fehlermeldung: " + str(xml_response))
                        record.stock_dm_state_id = self.env.ref('ama_delivery.dms70').id
                        if record.error_counter >= 5:
                            record.auto_tracking = False
                        else:
                            record.auto_tracking = True
                else:
                    record.error_occurred = True
                    record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                    record.error = "Server-Antwort entspricht weder einer gültigen Antwort, noch einer üblichen Fehlermeldung (POD): " + str(xml_response)
                    _logger.error("Abfragefehler Tracking(POD) für DHL-Sendung '" + str(record.name) + "'. Server-Antwort entspricht weder einer gültigen Antwort, noch einer üblichen Fehlermeldung: " + str(xml_response))
                    record.stock_dm_state_id = self.env.ref('ama_delivery.dms70').id
                    if record.error_counter >= 5:
                        record.auto_tracking = False
                    else:
                        record.auto_tracking = True
                    
                time.sleep(sleep_time)
    
    @api.multi
    def action_delete(self):
        for record in self:
            if record.name:
                company = record.stock_dm_picking_unit_id.stock_picking_id.company_id
                
                location = (company.sandbox_dhl and company.endpoint_order_dhl_test) or company.endpoint_order_dhl
                cig_username = (company.sandbox_dhl and company.cig_user_dhl_test) or (company.api_order_dhl == '1' and company.cig_user_dhl) or (company.api_order_dhl == '2' and company.cig_user_dhl2)
                cig_password = (company.sandbox_dhl and company.cig_pass_dhl_test) or (company.api_order_dhl == '1' and company.cig_pass_dhl) or (company.api_order_dhl == '2' and company.cig_pass_dhl2)
                intraship_username = (company.sandbox_dhl and company.intraship_user_dhl_test) or (company.api_order_dhl == '1' and company.intraship_user_dhl) or (company.api_order_dhl == '2' and company.gkp_user_dhl)
                intraship_password = (company.sandbox_dhl and company.intraship_pass_dhl_test) or (company.api_order_dhl == '1' and company.intraship_pass_dhl) or (company.api_order_dhl == '2' and company.gkp_pass_dhl)
                
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
                    
                    shipmentNumbers = []
                    shipmentNumber = client.factory.create('ns1:ShipmentNumberType')
                    shipmentNumber.shipmentNumber = record.name
                    shipmentNumbers.append(shipmentNumber)
                    
                    deleteShipmentResponse = False
                    
                    try:
                        deleteShipmentResponse = client.service.deleteShipmentDD(version, shipmentNumbers)
                    except Exception as e:
                        record.error = str(e)
                        _logger.error('Fehler DHL-Versand (Server)', unicode(e))
                        raise Warning('Fehler DHL-Versand (Server)', unicode(e))
                        
                    if deleteShipmentResponse:
                        _logger.debug(str(deleteShipmentResponse))
                        if deleteShipmentResponse.Status is not None:
                            statusCode = deleteShipmentResponse.Status and deleteShipmentResponse.Status.StatusCode and str(deleteShipmentResponse.Status.StatusCode)
                            statusMessage = deleteShipmentResponse.Status and deleteShipmentResponse.Status.StatusMessage and str(deleteShipmentResponse.Status.StatusMessage)
                            record.dhl_code = statusCode
                            _logger.debug('Request (Delete) Nummer %s ergab den Statuscode %s mit der Nachricht %s' % (record.name, statusCode, statusMessage))
                            if statusCode == 0:
                                record.stock_dm_state_id = self.env['stock.dm.state'].search([('sequence','=','80')], limit=1)
                                record.error_occurred = False
                                record.error_counter = False
                                record.error = ''
                            else:
                                #record.stock_dm_state_id = self.env['stock.dm.state'].search([('sequence','=','70')], limit=1)
                                record.error_occurred = True
                                record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                                record.error = 'Request (Delete) Nummer %s ergab den Statuscode %s mit der Nachricht %s' % (record.name, statusCode, statusMessage)
                                _logger.error('Request (Delete) Nummer %s ergab den Statuscode %s mit der Nachricht %s' % (record.name, statusCode, statusMessage))
                                raise Warning('Request (Delete) Nummer %s ergab den Statuscode %s mit der Nachricht %s' % (record.name, statusCode, statusMessage))
                    else:
                        #record.stock_dm_state_id = self.env['stock.dm.state'].search([('sequence','=','70')], limit=1)
                        record.error_occurred = True
                        record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                        record.error = 'Request (Delete) Nummer %s ergab kein Ergebnis.' % (record.name)
                        _logger.error('Request (Delete) Nummer %s ergab kein Ergebnis.' % (record.name))
                        raise Warning('Request (Delete) Nummer %s ergab kein Ergebnis.' % (record.name))
                
                
                elif company.api_order_dhl == '2':
                    WSDL_URL = u'https://cig.dhl.de/cig-wsdls/com/dpdhl/wsdl/geschaeftskundenversand-api/2.1/geschaeftskundenversand-api-2.1.wsdl'
                    client = Client(WSDL_URL, prettyxml=True, faults=True, location=location, transport=HttpAuthenticated(username = cig_username, password = cig_password), nosend=False)
                    
                    authentification = client.factory.create('cis:AuthentificationType')
                    authentification.user = intraship_username
                    authentification.signature = intraship_password
                    client.set_options(soapheaders=authentification)

                    version = client.factory.create('ns1:Version')
                    version.majorRelease = u'2'
                    version.minorRelease = u'1'
                    
                    shipmentNumbers = []
                    shipmentNumbers.append(Element('cis:shipmentNumber').setText(record.name))
                    
                    deleteShipmentOrderResponse = False
                    
                    try:
                        deleteShipmentOrderResponse = client.service.deleteShipmentOrder(version, shipmentNumbers)
                    except Exception as e:
                        record.error = str(e)
                        _logger.error('Fehler DHL-Versand (Server)', unicode(e))
                        raise Warning('Fehler DHL-Versand (Server)', unicode(e))
                        
                    if deleteShipmentOrderResponse:
                        _logger.debug(str(deleteShipmentOrderResponse))
                        if deleteShipmentOrderResponse.Status is not None:
                            statusCode = deleteShipmentOrderResponse.Status and deleteShipmentOrderResponse.Status.statusCode and str(deleteShipmentOrderResponse.Status.statusCode)
                            statusMessage = deleteShipmentOrderResponse.Status and deleteShipmentOrderResponse.Status.statusMessage and deleteShipmentOrderResponse.Status.statusMessage[0]
                            record.dhl_code = statusCode
                            _logger.debug('Request (Delete) Nummer %s ergab den Statuscode %s mit der Nachricht %s' % (record.name, statusCode, statusMessage))
                            if statusCode == 0:
                                record.stock_dm_state_id = self.env['stock.dm.state'].search([('sequence','=','80')], limit=1)
                                record.error_occurred = False
                                record.error_counter = False
                                record.error = ''
                            else:
                                #record.stock_dm_state_id = self.env['stock.dm.state'].search([('sequence','=','70')], limit=1)
                                record.error_occurred = True
                                record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                                record.error = 'Request (Delete) Nummer %s ergab den Statuscode %s mit der Nachricht %s' % (record.name, statusCode, statusMessage)
                                _logger.error('Request (Delete) Nummer %s ergab den Statuscode %s mit der Nachricht %s' % (record.name, statusCode, statusMessage))
                                raise Warning('Request (Delete) Nummer %s ergab den Statuscode %s mit der Nachricht %s' % (record.name, statusCode, statusMessage))
                    else:
                        #record.stock_dm_state_id = self.env['stock.dm.state'].search([('sequence','=','70')], limit=1)
                        record.error_occurred = True
                        record.error_counter = (not record.error_counter and 1) or (record.error_counter + 1)
                        record.error = 'Request (Delete) Nummer %s ergab kein Ergebnis.' % (record.name)
                        _logger.error('Request (Delete) Nummer %s ergab kein Ergebnis.' % (record.name))
                        raise Warning('Request (Delete) Nummer %s ergab kein Ergebnis.' % (record.name))
                
        return
    
    # Override delete method, so that shipment is deleted at DHL too.
    @api.multi
    def unlink(self):
        for record in self:
            # First call java function to delete delivery slip at DHL
            record.action_delete()
            # If no error occured delete shipment
            super(stock_dhl_picking_unit, record).unlink()
        return

        
class MyPlugin(MessagePlugin):

    def marshalled(self, context):
        #_logger.debug('Marshalled')
        
        for body_element in context.envelope.childAtPath('Body'):
            #_logger.debug(body_element.name)
            if body_element.name == 'DeleteShipmentDDRequest':
                for element in body_element:
                    #_logger.debug(element.name)
                    if element.name == 'Version':
                        element.setPrefix('ns0')
                                                

class stock_dhl_ice(models.Model):
    _name = 'stock.dhl.ice'
    _order = 'code asc'

    name = fields.Char(string="Name", compute='_get_name')
    code = fields.Char(string="ICE Code", required=True)
    text = fields.Char(string="ICE Text", compute='_get_text')
    text_en = fields.Char(string="ICE Text englisch")
    text_de = fields.Char(string="ICE Text deutsch")
    stock_dm_state_id = fields.Many2one('stock.dm.state', ondelete='restrict', string="dm_state")

    _sql_constraints = [
            ('code_unique',
             'UNIQUE(code)',
             "Der verwendete Code muss einmalig sein."),
            ]
            
    @api.multi
    @api.depends('code', 'text')
    def _get_name(self):
        for record in self:
            record.name = ': '.join([record.code or '', record.text or ''])

    @api.multi
    @api.depends('text_en', 'text_de')
    def _get_text(self):
        for record in self:
            if self.env.user.lang == "de_DE":
                record.text = record.text_de
            else:
                record.text = record.text_en
 
 
class stock_dhl_ric(models.Model):
    _name = 'stock.dhl.ric'
    _order = 'code asc'

    name = fields.Char(string="Name", compute='_get_name')
    code = fields.Char(string="RIC Code", required=True)
    text = fields.Char(string="RIC Text", compute='_get_text')
    text_en = fields.Char(string="RIC Text englisch")
    text_de = fields.Char(string="RIC Text deutsch")

    _sql_constraints = [
            ('code_unique',
             'UNIQUE(code)',
             "Der verwendete Code muss einmalig sein."),
            ]

    @api.multi
    @api.depends('code', 'text')
    def _get_name(self):
        for record in self:
            record.name = ': '.join([record.code or '', record.text or ''])

    @api.multi
    @api.depends('text_en', 'text_de')
    def _get_text(self):
        for record in self:
            if self.env.user.lang == "de_DE":
                record.text = record.text_de
            else:
                record.text = record.text_en


class stock_dhl_ttpro(models.Model):
    _name = 'stock.dhl.ttpro'
    _order = 'code asc'

    name = fields.Char(string="Name", compute='_get_name')
    code = fields.Char(string="TTpro Code", required=True)
    text = fields.Char(string="TTpro Text", compute='_get_text')
    text_en = fields.Char(string="TTpro Text englisch")
    text_de = fields.Char(string="TTpro Text deutsch")

    _sql_constraints = [
            ('code_unique',
             'UNIQUE(code)',
             "Der verwendete Code muss einmalig sein."),
            ]

    @api.multi
    @api.depends('code', 'text')
    def _get_name(self):
        for record in self:
            record.name = ': '.join([record.code or '', record.text or ''])

    @api.multi
    @api.depends('text_en', 'text_de')
    def _get_text(self):
        for record in self:
            if self.env.user.lang == "de_DE":
                record.text = record.text_de
            else:
                record.text = record.text_en
                
class stock_dhl_combination(models.Model):
    _name = 'stock.dhl.combination'

    name = fields.Char(string="Name", compute='_get_name')
    stock_dhl_ice_id = fields.Many2one('stock.dhl.ice', ondelete='restrict', string="ICE", required=True)
    stock_dhl_ric_id = fields.Many2one('stock.dhl.ric', ondelete='restrict', string="RIC", required=True)
    stock_dhl_ttpro_id = fields.Many2one('stock.dhl.ttpro', ondelete='restrict', string="TTpro", required=True)
    delivery_carrier_id = fields.Many2one('delivery.carrier', ondelete='restrict', string='Auslieferungsmethode', help='Auslieferungsmethode fuer diese Sendung', required=True)
    
    @api.multi
    @api.depends('stock_dhl_ice_id', 'stock_dhl_ric_id', 'stock_dhl_ttpro_id', 'delivery_carrier_id')
    def _get_name(self):
        for record in self:
            record.name = "ICE: " + (record.stock_dhl_ice_id.name or " ") + " - " \
                + "RIC: " + (record.stock_dhl_ric_id.name or " ") + " - " \
                + "TTpro: " + (record.stock_dhl_ttpro_id.name or " ") + " - " \
                + "DM: " + (record.delivery_carrier_id.name or " ")
                
                
class stock_dhl_status(models.Model):
    _name = 'stock.dhl.status'
    
    name = fields.Char(string="Name", compute='_get_name')
    code = fields.Char(string="Status Code", required=True)
    text = fields.Char(string="Status Text", compute='_get_text')
    text_en = fields.Char(string="Status Text englisch")
    text_de = fields.Char(string="Status Text deutsch")

    _sql_constraints = [
            ('code_unique',
             'UNIQUE(code)',
             "Der verwendete Code muss einmalig sein."),
            ]

    @api.multi
    @api.depends('code', 'text')
    def _get_name(self):
        for record in self:
            record.name = ': '.join([record.code or '', record.text or ''])

    @api.multi
    @api.depends('text_en', 'text_de')
    def _get_text(self):
        for record in self:
            if self.env.user.lang == "de_DE":
                record.text = record.text_de
            else:
                record.text = record.text_en
    


class stock_dhl_event(models.Model):
    _name = 'stock.dhl.event'

    # displayed columns
    stock_dhl_picking_unit_id = fields.Many2one('stock.dhl.picking.unit', ondelete='cascade', string="Shipment number", required=True)
    name = fields.Char(string="State description", compute='_get_name', readonly=True)
    stock_dhl_ice_id = fields.Many2one('stock.dhl.ice', ondelete='restrict', string="ICE", compute='_get_ice', readonly=True, store=True)
    stock_dhl_ric_id = fields.Many2one('stock.dhl.ric', ondelete='restrict', string="RIC", compute='_get_ric', readonly=True, store=True)
    stock_dm_state_id = fields.Many2one('stock.dm.state', related='stock_dhl_ice_id.stock_dm_state_id', ondelete='restrict', readonly=True, store=True)
    stock_dhl_ttpro_id = fields.Many2one('stock.dhl.ttpro', ondelete='restrict', string="TTpro", compute='_get_ttpro', readonly=True, store=True)
    event_date = fields.Datetime(string="Date DHL Event", compute='_get_event_date')
    
    # not displayed columns
    # DHL response columns
    dhl_event_country = fields.Char(string="event-country")
    dhl_event_location = fields.Char(string="event-location")
    dhl_event_status = fields.Char(string="event-status")
    dhl_event_text = fields.Char(string="event-text")
    dhl_event_timestamp = fields.Char(string="event-timestamp")
    dhl_ice = fields.Char(string="ice")
    dhl_ric = fields.Char(string="ric")
    dhl_ruecksendung = fields.Char(string="ruecksendung")
    dhl_standard_event_code = fields.Char(string="standard-event-code")


    @api.multi
    @api.depends('dhl_ice')
    def _get_ice(self):
        for record in self:
            record.stock_dhl_ice_id = self.env['stock.dhl.ice'].search([('code','=',record.dhl_ice)], limit=1)

    @api.multi
    @api.depends('dhl_ric')
    def _get_ric(self):
        for record in self:
            record.stock_dhl_ric_id = self.env['stock.dhl.ric'].search([('code','=',record.dhl_ric)], limit=1)

    @api.multi
    @api.depends('dhl_standard_event_code')
    def _get_ttpro(self):
        for record in self:
            record.stock_dhl_ttpro_id = self.env['stock.dhl.ttpro'].search([('code','=',record.dhl_standard_event_code)], limit=1)

    @api.multi
    @api.depends('dhl_event_timestamp', 'dhl_event_status')
    def _get_name(self):
        for record in self:
            record.name = ' - '.join([record.dhl_event_timestamp or '', record.dhl_event_status or ''])

    @api.multi
    @api.depends('dhl_event_timestamp')
    def _get_event_date(self):
        for record in self:
            if record.dhl_event_timestamp:
                try:
                    tz = pytz.timezone('Europe/Berlin') 
                    record.event_date = tz.localize(datetime.strptime(record.dhl_event_timestamp, '%d.%m.%Y %H:%M')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
                    # record.event_date = datetime.strptime(record.dhl_event_timestamp, '%d.%m.%Y %H:%M').strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    record.event_date = False
