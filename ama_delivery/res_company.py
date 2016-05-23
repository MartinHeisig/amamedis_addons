# -*- coding: utf-8 -*-

from openerp import models, fields, api

class res_company_access_data(models.Model):
    _inherit = 'res.company'
    
    # Owncloud Login and directories
    oc_user = fields.Char('Username')
    oc_password = fields.Char('Password')
    oc_local_dir = fields.Char('Local directory')
    oc_remote_dir = fields.Char('Remote directory')
    
    # DHL Login
    # * Geschäftskundenversand *
    dhl_order_endpoint = fields.Char('Endpunkt', help='Endpunkt Geschaeftskundenversand Produktionssystem', default='https://cig.dhl.de/services/production/soap/')
    dhl_order_ekp = fields.Char('EKP Nummer', size=10, help='Die ersten zehn Ziffern Ihrer DHL Abrechnungsnummer')
    dhl_order_partner_id = fields.Char('DHL Teilnahme National', size=2, help='Die letzten zwei Ziffern ihrer DHL Abrechnungsnummer')
    dhl_order_intraship_user = fields.Char('Intraship Benutzername', help='Benutzername Intraship Account')
    dhl_order_intraship_password = fields.Char('Intraship Passwort', help='Passwort Intraship Account')
    dhl_order_endpoint_test = fields.Char('Endpunkt', help='Endpunkt Geschaeftskundenversand Testsystem', default='https://cig.dhl.de/services/sandbox/soap/')
    dhl_order_ekp_test = fields.Char('EKP Nummer Test', size=10, help='EKP Nummer für Testsystem', default='5000000000')
    dhl_order_partner_id_test = fields.Char('DHL Teilnahme National Test', size=2, help='Teilnahme Nummer Testsystem', default='01')
    dhl_order_intraship_user_test = fields.Char('Benutzername Test', help='Benutzername Web-Service Testsystem', default='geschaeftskunden_api')
    dhl_order_intraship_password_test = fields.Char('Passwort Test', help='Passwort Web-Service Testsystem', default='Dhl_ep_test1')
    
    # * Sendungsverfolgung *
    dhl_track_endpoint = fields.Char('Endpunkt', help='Endpunkt Sendungsverfolgung Produktionssystem', default='https://cig.dhl.de/services/production/rest/sendungsverfolgung/')
    dhl_track_appname = fields.Char('ZT Kennung', help='Die ihrer EKP Nummer zugewiesene ZT Kennung, um die mit dieser EKP Nummer generierten Sendungen zu verfolgen')
    dhl_track_password = fields.Char('ZT Passwort', help='Passwort fuer die ZT Kennung')
    dhl_track_cig_user = fields.Char('Application ID', help='Application ID fuer die Anwendung nach Freigabe durch DHL')
    dhl_track_cig_pass = fields.Char('Token', help='Fuer diese Application ID generiertes Token')
    dhl_track_endpoint_test = fields.Char('Endpunkt', help='Endpunkt Sendungsverfolgung Testsystem', default='https://cig.dhl.de/services/sandbox/rest/sendungsverfolgung/')
    dhl_track_appname_test = fields.Char('Benutzername Test', help='Benutzername Web-Service Testsystem', default='dhl_entwicklerportal')
    dhl_track_password_test = fields.Char('Passwort Test', help='Passwort Web-Service Testsystem', default='Dhl_123!')
    dhl_track_cig_user_test = fields.Char('CIG Benutzername Test', help='Kennung der Anwendung im Testmodus. Entspricht DHL EntwicklerID', default='robberechts')
    dhl_track_cig_pass_test = fields.Char('CIG Passwort Test', help='Passwort der Anwendung im Testmodus. Entspricht Entwicklerportal Passwort', default='1Q@dhl.com')
    
    # * Switch for activating test mode
    dhl_test = fields.Boolean('DHL Test Modus', help='Alle DHL Anfragen laufen unter Testbedingungen. Es werden keine echten Labels erstellt oder Sendungen verfolgt')
