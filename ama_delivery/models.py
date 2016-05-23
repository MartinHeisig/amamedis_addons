# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning
from requests.auth import HTTPBasicAuth

import logging
import binascii
import requests
import time
import xmltodict

import constants

_logger = logging.getLogger(__name__)


class stock_picking_pu(models.Model):
    _inherit = 'stock.picking'
    '''Erweiterung des Lieferscheins'''

    stock_dm_picking_unit_ids = fields.One2many(comodel_name='stock.dm.picking.unit', inverse_name='stock_picking_id', string="Sendescheine")


class stock_dm_picking_unit(models.Model):
    _name = 'stock.dm.picking.unit'
    '''ungebrandete Sendung'''

    name = fields.Char(string='Name', compute='_compute_name', help='Logistiker-Sendungsnummer')
    code = fields.Char(string='Sendungsnummer', help='Sendungsnummer', required=True)
    stock_picking_id = fields.Many2one('stock.picking', ondelete='restrict', string='Lieferschein', help='Lieferschein, zu dem diese Sendung gehört', required=True)
    delivery_carrier_id = fields.Many2one('delivery.carrier', ondelete='restrict', string='Logistiker', help='Auslieferungsmethode für diese Sendung', required=True)
    delivery_carrier_res_model = fields.Char(string='Datenmodell des Lieferanten', related='delivery_carrier_id.res_model', help='Der Auslieferungsmethode (dem Logistiker) zugewiesenes Datenmodell', store=True)
    delivery_carrier_res_id = fields.Integer(string='ID im Datenmodell des Lieferanten', help='DatensatzID im jeweiligen Modell des Logistikers')
    stock_dm_state_id = fields.Many2one('stock.dm.state', string='Status der Lieferung', compute='_compute_carriers_state', ondelete='restrict', store=True, help='Interner Status der Sendung')
    
    @api.multi
    @api.depends('code','delivery_carrier_id.name')
    def _compute_name(self):
        for record in self:
            if record.code and record.delivery_carrier_id and record.delivery_carrier_id.name:
                record.name = ' - '.join(record.delivery_carrier_id.name, record.code)
    
    @api.multi
    @api.depends('delivery_carrier_res_model','delivery_carrier_res_id')
    def _compute_carrier_state(self):
        for record in self:
            if record.delivery_carrier_res_model and record.delivery_carrier_res_id:
                carrier_picking_unit = self.env[record.delivery_carrier_res_model].browse(record.delivery_carrier_res_id)
                if carrier_picking_unit.stock_dm_state_id:
                    record.stock_dm_state_id = carrier_picking_unit.stock_dm_state_id #eventuell erst hier von dhl-status auf internen status umrechnen? -> verworfen weil gehört in DHL Teil
    

class stock_dhl_picking_unit(models.Model):
    _name = 'stock.dhl.picking.unit'
    '''DHL-gebrandete Sendung'''
    
    name = fields.Char(string='Name', help='Sendungsnummer', readonly=True, required=True)
    stock_dhl_ice_id = fields.Many2one('stock.dhl.ice', ondelete='restrict', string="ICE", compute='_compute_ice', readonly=True, store=True)
    stock_dhl_ric_id = fields.Many2one('stock.dhl.ric', ondelete='restrict', string="RIC", compute='_compute_ric', readonly=True, store=True)
    stock_dhl_ttpro_id = fields.Many2one('stock.dhl.ttpro', ondelete='restrict', string="TTpro", compute='_compute_ttpro', readonly=True, store=True)
    stock_dm_picking_unit_id = fields.Many2one('stock.dm.picking.unit', string='Sendung', ondelete='restrict', help='Zugehörige interne Sendung', store=True, required=True)
    stock_dm_state_id = fields.Many2one('stock.dm.state', string='Status der Lieferung', related='stock_dhl_ice_id.stock_dm_state_id', ondelete='restrict', readonly=True, store=True)
    image = fields.Binary(string="Signature", compute='_compute_image', readonly=True, store=True)
    
    stock_dhl_ice_code = fields.Char(related='stock_dhl_ice_id.code', string="ICE-Code", readonly=True)
    stock_dhl_ice_text = fields.Char(related='stock_dhl_ice_id.text', string="ICE-Text", readonly=True)
    stock_dhl_ric_code = fields.Char(related='stock_dhl_ric_id.code', string="RIC-Code", readonly=True)
    stock_dhl_ric_text = fields.Char(related='stock_dhl_ric_id.text', string="RIC-Text", readonly=True)
    stock_dhl_ttpro_code = fields.Char(related='stock_dhl_ttpro_id.code', string="TTpro-Code", readonly=True)
    stock_dhl_ttpro_text = fields.Char(related='stock_dhl_ttpro_id.text', string="TTpro-Text", readonly=True)
    new_image_received = fields.Boolean(default=False)
    
    # not displayed fields
    # DHL response fields
    dhl_airway_bill_number = fields.Char(string="airway-bill-number")
    dhl_delivery_event_flag = fields.Char(string="delivery-event-flag")
    dhl_dest_country = fields.Char(string="dest-country")
    dhl_division = fields.Char(string="division")
    dhl_domestic_id = fields.Char(string="domestic-id")
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
             "Sendungen sind einmalig und können nicht dupliziert werden.\nFalls es sich um eine reguläre Sendung handelt, prüfen Sie ob Ihr Ihnen zugewiesener Nummernpool zu klein ist."),
            ]
    
    @api.multi
    @api.depends('dhl_ice')
    def _compute_ice(self):
        for record in self:
            record.stock_dhl_ice_id = self.env['stock.dhl.ice'].search([('code','=',record.dhl_ice)], limit=1)

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
    def tracking(self):
        for record in self:
            method = "d-get-piece-detail"
            language_code = "de"
            try:
                piece_code = record.name
            except Exception as e:
                raise e
            test = True
            # auslagern in company
            appname = "dhl_entwicklerportal"
            password = "Dhl_123!"
            cig_user = "robberechts"
            cig_pass = "1Q@dhl.com"
            endpoint = "https://cig.dhl.de/services/sandbox/rest/sendungsverfolgung/"

            xml_response = ''
            xml_response_dict = ''

            request = '<?xml version="1.0" encoding="UTF-8"?><data '
            request += constants.APPNAME + '=\"' + appname + '\" '
            request += constants.PASSWORD + '=\"' + password + '\" '
            request += constants.LANGUAGE_CODE + '=\"' + language_code + '\" '
            request += constants.REQUEST + '=\"' + method + '\" '

            request += constants.PIECE_CODE + '=\"' + piece_code + '\"'
            
            request += '></data>'

            headers = {'Content-Type': 'text/xml'}
            payload = {'xml': request}


            try:
                r = requests.get(endpoint, params=payload, auth=HTTPBasicAuth(cig_user, cig_pass), headers=headers)

                if r.status_code == 200:
                    r.encoding = "utf-8"
                    xml_response = r.text
                else:
                    raise except_orm('Request error', 'HTTP request failed')

            except Exception as e:
                raise except_orm('Request error', 'HTTP request failed')


            if xml_response.startswith('<?xml'):
                # XML parsen
                xml_response_dict = xmltodict.parse(xml_response)

                record.dhl_airway_bill_number = xml_response_dict['data']['data']['@' + constants.AIRWAY_BILL_NUMBER]
                record.dhl_delivery_event_flag = xml_response_dict['data']['data']['@' + constants.DELIVERY_EVENT_FLAG]
                record.dhl_dest_country = xml_response_dict['data']['data']['@' + constants.DEST_COUNTRY]
                record.dhl_division = xml_response_dict['data']['data']['@' + constants.DIVISION]
                record.dhl_domestic_id = xml_response_dict['data']['data']['@' + constants.DOMESTIC_ID]
                record.dhl_error_status = xml_response_dict['data']['data']['@' + constants.ERROR_STATUS]
                record.dhl_event_country = xml_response_dict['data']['data']['@' + constants.EVENT_COUNTRY]
                record.dhl_event_location = xml_response_dict['data']['data']['@' + constants.EVENT_LOCATION]
                record.dhl_ice = xml_response_dict['data']['data']['@' + constants.ICE]
                record.dhl_identifier_type = xml_response_dict['data']['data']['@' + constants.IDENTIFIER_TYPE]
                record.dhl_international_flag = xml_response_dict['data']['data']['@' + constants.INTERNATIONAL_FLAG]
                record.dhl_leitcode = xml_response_dict['data']['data']['@' + constants.LEITCODE]
                record.dhl_matchcode = xml_response_dict['data']['data']['@' + constants.MATCHCODE]
                record.dhl_order_preferred_delivery_date = xml_response_dict['data']['data']['@' + constants.ORDER_PREFERRED_DELIVERY_DAY]
                record.dhl_origin_country = xml_response_dict['data']['data']['@' + constants.ORIGIN_COUNTRY]
                record.dhl_pan_recipient_address = xml_response_dict['data']['data']['@' + constants.PAN_RECIPIENT_ADDRESS]
                record.dhl_pan_recipient_city = xml_response_dict['data']['data']['@' + constants.PAN_RECIPIENT_CITY]
                record.dhl_pan_recipient_name = xml_response_dict['data']['data']['@' + constants.PAN_RECIPIENT_NAME]
                record.dhl_pan_recipient_postalcode = xml_response_dict['data']['data']['@' + constants.PAN_RECIPIENT_POSTALCODE]
                record.dhl_pan_recipient_street = xml_response_dict['data']['data']['@' + constants.PAN_RECIPIENT_STREET]
                record.dhl_piece_code = xml_response_dict['data']['data']['@' + constants.PIECE_CODE]
                record.dhl_piece_customer_reference = xml_response_dict['data']['data']['@' + constants.PIECE_CUSTOMER_REFERENCE]
                record.dhl_piece_id = xml_response_dict['data']['data']['@' + constants.PIECE_ID]
                record.dhl_piece_identifier = xml_response_dict['data']['data']['@' + constants.PIECE_IDENTIFIER]
                record.dhl_product_code = xml_response_dict['data']['data']['@' + constants.PRODUCT_CODE]
                record.dhl_product_key = xml_response_dict['data']['data']['@' + constants.PRODUCT_KEY]
                record.dhl_product_name = xml_response_dict['data']['data']['@' + constants.PRODUCT_NAME]
                record.dhl_pslz_nr = xml_response_dict['data']['data']['@' + constants.PSLZ_NR]
                record.dhl_recipient_city = xml_response_dict['data']['data']['@' + constants.RECIPIENT_CITY]
                record.dhl_recipient_id = xml_response_dict['data']['data']['@' + constants.RECIPIENT_ID]
                record.dhl_recipient_id_text = xml_response_dict['data']['data']['@' + constants.RECIPIENT_ID_TEXT]
                record.dhl_recipient_name = xml_response_dict['data']['data']['@' + constants.RECIPIENT_NAME]
                record.dhl_recipient_street = xml_response_dict['data']['data']['@' + constants.RECIPIENT_STREET]
                record.dhl_ric = xml_response_dict['data']['data']['@' + constants.RIC]
                record.dhl_routing_code_ean = xml_response_dict['data']['data']['@' + constants.ROUTING_CODE_EAN]
                record.dhl_ruecksendung = xml_response_dict['data']['data']['@' + constants.RUECKSENDUNG]
                record.dhl_searched_piece_code = xml_response_dict['data']['data']['@' + constants.SEARCHED_PIECE_CODE]
                record.dhl_searched_ref_no = xml_response_dict['data']['data']['@' + constants.SEARCHED_REF_NO]
                record.dhl_shipment_code = xml_response_dict['data']['data']['@' + constants.SHIPMENT_CODE]
                record.dhl_shipment_customer_reference = xml_response_dict['data']['data']['@' + constants.SHIPMENT_CUSTOMER_REFERENCE]
                record.dhl_shipment_height = xml_response_dict['data']['data']['@' + constants.SHIPMENT_HEIGHT]
                record.dhl_shipment_length = xml_response_dict['data']['data']['@' + constants.SHIPMENT_LENGTH]
                record.dhl_shipment_weight = xml_response_dict['data']['data']['@' + constants.SHIPMENT_WEIGHT]
                record.dhl_shipment_width = xml_response_dict['data']['data']['@' + constants.SHIPMENT_WIDTH]
                record.dhl_shipper_address = xml_response_dict['data']['data']['@' + constants.SHIPPER_ADDRESS]
                record.dhl_shipper_city = xml_response_dict['data']['data']['@' + constants.SHIPPER_CITY]
                record.dhl_shipper_name = xml_response_dict['data']['data']['@' + constants.SHIPPER_NAME]
                record.dhl_shipper_street = xml_response_dict['data']['data']['@' + constants.SHIPPER_STREET]
                record.dhl_short_status = xml_response_dict['data']['data']['@' + constants.SHORT_STATUS]
                record.dhl_standard_event_code = xml_response_dict['data']['data']['@' + constants.STANDARD_EVENT_CODE]
                record.dhl_status = xml_response_dict['data']['data']['@' + constants.STATUS]
                record.dhl_status_liste = xml_response_dict['data']['data']['@' + constants.STATUS_LISTE]
                record.dhl_status_timestamp = xml_response_dict['data']['data']['@' + constants.STATUS_TIMESTAMP]
                record.dhl_upu = xml_response_dict['data']['data']['@' + constants.UPU]

                for dhl_event in xml_response_dict['data']['data']['data']['data']:
                    count = self.env['stock.picking.unit.state'].search_count([('stock_picking_unit_id','=',record.id),('dhl_event_timestamp','=',dhl_event['@' + constants.EVENT_TIMESTAMP])])
                    if count == 0:
                        self.env['stock.picking.unit.state'].create({
                            'stock_picking_unit_id': record.id,
                            'dhl_event_country': dhl_event['@' + constants.EVENT_COUNTRY],
                            'dhl_event_location': dhl_event['@' + constants.EVENT_LOCATION],
                            'dhl_event_status': dhl_event['@' + constants.EVENT_STATUS],
                            'dhl_event_text': dhl_event['@' + constants.EVENT_TEXT],
                            'dhl_event_timestamp': dhl_event['@' + constants.EVENT_TIMESTAMP],
                            'dhl_ice': dhl_event['@' + constants.ICE],
                            'dhl_ric': dhl_event['@' + constants.RIC],
                            'dhl_ruecksendung': dhl_event['@' + constants.RUECKSENDUNG],
                            'dhl_standard_event_code': dhl_event['@' + constants.STANDARD_EVENT_CODE],
                        })


                record.new_image_received = False
                if not record.dhl_image and record.dhl_ice == "DLVRD":
                    time.sleep(10)

                    method = 'd-get-signature'
                    xml_response = ''
                    xml_response_dict = ''

                    request = '<?xml version="1.0" encoding="UTF-8"?><data '
                    request += constants.APPNAME + '=\"' + appname + '\" '
                    request += constants.PASSWORD + '=\"' + password + '\" '
                    request += constants.LANGUAGE_CODE + '=\"' + language_code + '\" '
                    request += constants.REQUEST + '=\"' + method + '\" '

                    request += constants.PIECE_CODE + '=\"' + piece_code + '\"'

                    request += '></data>'

                    headers = {'Content-Type': 'text/xml'}
                    payload = {'xml': request}


                    try:
                        r = requests.get(endpoint, params=payload, auth=HTTPBasicAuth(cig_user, cig_pass), headers=headers)

                        if r.status_code == 200:
                            r.encoding = "utf-8"
                            xml_response = r.text
                        else:
                            raise except_orm('Request error', 'HTTP request failed while getting signature')

                    except Exception as e:
                        raise except_orm('Request error', 'HTTP request failed while getting signature')


                    if xml_response.startswith('<?xml'):
                        # XML parsen
                        xml_response_dict = xmltodict.parse(xml_response)

                        record.dhl_image_event_date = xml_response_dict['data']['data']['@' + constants.EVENT_DATE]
                        record.dhl_image_mime_type = xml_response_dict['data']['data']['@' + constants.MIME_TYPE]
                        record.dhl_image = xml_response_dict['data']['data']['@' + constants.IMAGE]

                        record.new_image_received = True

                    elif xml_response.find('<B>SIM:</B>') != -1:
                        try:
                            errorsplit1 = xml_response.split('<B>SIM:</B>')
                            errorsplit2 = errorsplit1[1].split('</FONT>')
                            errormessage = errorsplit2[0].strip()
                            raise except_orm('Request error', 'Server sent error message: ' + errormessage)
                        except Exception as e:
                            raise except_orm('Request error', 'Server sent a HTML-Response that do not fit the usual errormessage-style:\n' + xml_response)
                    else:
                        raise except_orm('Request error', 'Server sent a response that was not XML-style for valid response or valid HTML-sytle for errormessage:\n' + xml_response)


            elif xml_response.find('<B>SIM:</B>') != -1:
                try:
                    errorsplit1 = xml_response.split('<B>SIM:</B>')
                    errorsplit2 = errorsplit1[1].split('</FONT>')
                    errormessage = errorsplit2[0].strip()
                    raise except_orm('Request error', 'Server sent error message: ' + errormessage)
                except Exception as e:
                    raise except_orm('Request error', 'Server sent a HTML-Response that do not fit the usual errormessage-style:\n' + xml_response)
            else:
                raise except_orm('Request error', 'Server sent a response that was not XML-style for valid response or valid HTML-sytle for errormessage:\n' + xml_response)

                
class stock_dm_state(models.Model):
    _name = 'stock.dm.state'
    _order = 'sequence asc'
    '''allgemeiner Lieferstatus'''
    
    name = fields.Char(string="State", compute='_get_name')
    name_en = fields.Char(string="State_en")
    name_de = fields.Char(string="State_de")
    sequence = fields.Integer(string="Sequence")

    @api.multi
    @api.depends('name_en', 'name_de')
    def _get_name(self):
        for record in self:
            if self.env.user.lang == "de_DE":
                record.name = record.name_de
            else:
                record.name = record.name_en

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
            record.name = record.code + ": " + record.text

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
    code = fields.Char(string="RIC Code")
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
            record.name = record.code + ": " + record.text

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
    code = fields.Char(string="TTpro Code")
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
            record.name = record.code + ": " + record.text

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
    delivery_carrier_id = fields.Many2one('delivery.carrier', ondelete='restrict', string='Auslieferungsmethode', help='Auslieferungsmethode für diese Sendung', required=True)
    
    @api.multi
    @api.depends('stock_dhl_ice_id', 'stock_dhl_ric_id', 'stock_dhl_ttpro_id', 'delivery_carrier_id')
    def _get_name(self):
        for record in self:
            record.name = "ICE: " + record.stock_dhl_ice_id.name + " - " \
                + "RIC: " + record.stock_dhl_ric_id.name + " - " \
                + "TTpro: " + record.stock_dhl_ttpro_id.name + " - " \
                + "DM: " + record.delivery_carrier_id.name