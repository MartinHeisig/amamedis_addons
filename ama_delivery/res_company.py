# -*- coding: utf-8 -*-

from openerp import models, fields, api

class res_company_access_data(models.Model):
    _inherit = 'res.company'
    
    # Owncloud Login and directories
    del_oc_user = fields.Char('Username')
    del_oc_password = fields.Char('Password')
    del_oc_local_dir = fields.Char('Local directory')
    del_oc_remote_dir = fields.Char('Remote directory')
    
    # DHL Login
    api_order_dhl = fields.Selection([('1', 'Intraship'),('2', 'Versenden')], string='API-Version', help='Auswahl, welche API verwendet werden soll', default='1')
    sandbox_dhl = fields.Boolean('DHL Test Modus', help='Alle DHL Anfragen laufen unter Testbedingungen. Es werden keine echten Labels erstellt oder Sendungen verfolgt')
    
    ekp_dhl = fields.Char('EKP Nummer', size=10, help='Die ersten zehn Ziffern Ihrer DHL Abrechnungsnummer')
    partner_id_dhl = fields.Char('DHL Teilnahme National', size=2, help='Die letzten zwei Ziffern ihrer DHL Abrechnungsnummer')
    cig_user_dhl = fields.Char('CIG Benutzername Intraship', help='Application ID fuer die Anwendung nach Freigabe durch DHL')
    cig_pass_dhl = fields.Char('CIG Passwort Intraship', help='Fuer diese Application ID generiertes Token')
    intraship_user_dhl = fields.Char('Intraship Benutzername', help='Benutzername Intraship Account')
    intraship_pass_dhl = fields.Char('Intraship Passwort', help='Passwort Intraship Account')
    cig_user_dhl2 = fields.Char('CIG Benutzername Versenden', help='Application ID fuer die Anwendung nach Freigabe durch DHL')
    cig_pass_dhl2 = fields.Char('CIG Passwort Versenden', help='Fuer diese Application ID generiertes Token')
    gkp_user_dhl = fields.Char('Versenden Benutzername', help='Benutzername Account Geschaeftskundenportal')
    gkp_pass_dhl = fields.Char('Versenden Passwort', help='Passwort Account Geschaeftskundenportal')
    zt_user_dhl = fields.Char('ZT Kennung', help='Die ihrer EKP Nummer zugewiesene ZT Kennung, um die mit dieser EKP Nummer generierten Sendungen zu verfolgen')
    zt_pass_dhl = fields.Char('ZT Passwort', help='Passwort fuer die ZT Kennung')
    endpoint_order_dhl = fields.Char('Endpunkt Geschäftskundenversand', help='Endpunkt Geschaeftskundenversand Produktionssystem', default='https://cig.dhl.de/services/production/soap/')
    endpoint_track_dhl = fields.Char('Endpunkt Sendungsverfolgung', help='Endpunkt Sendungsverfolgung Produktionssystem', default='https://cig.dhl.de/services/production/rest/sendungsverfolgung/')
    
    ekp_dhl_test = fields.Char('EKP Nummer Sandbox', size=10, help='EKP Nummer Sandbox', default='2222222222')
    partner_id_dhl_test = fields.Char('DHL Teilnahme National Sandbox', size=2, help='Teilnahme Nummer Sandbox', default='01')
    cig_user_dhl_test = fields.Char('CIG Benutzername Sandbox', help='Kennung der Anwendung im Testmodus. Entspricht DHL EntwicklerID', default='robberechts')
    cig_pass_dhl_test = fields.Char('CIG Passwort Sandbox', help='Passwort der Anwendung im Testmodus. Entspricht Entwicklerportal Passwort', default='1Q@dhl.com')
    intraship_user_dhl_test = fields.Char('Intraship Benutzername Sandbox', help='Benutzername Intraship Account Sandbox', default='2222222222_01')
    intraship_pass_dhl_test = fields.Char('Intraship Passwort Sandbox', help='Passwort Intraship Account Sandbox', default='pass')
    zt_user_dhl_test = fields.Char('ZT Kennung Sandbox', help='ZT-Kennung Sandbox', default='dhl_entwicklerportal')
    zt_pass_dhl_test = fields.Char('ZT Passwort Sandbox', help='ZT-Passwort Sandbox', default='Dhl_123!')
    endpoint_order_dhl_test = fields.Char('Endpunkt Geschäftskundenversand Sandbox', help='Endpunkt Geschaeftskundenversand Sandbox', default='https://cig.dhl.de/services/sandbox/soap/')
    endpoint_track_dhl_test = fields.Char('Endpunkt Sendungsverfolgung Sandbox', help='Endpunkt Sendungsverfolgung Sandbox', default='https://cig.dhl.de/services/sandbox/rest/sendungsverfolgung/')
    
    '''# * Geschäftskundenversand *
    dhl_order_endpoint = fields.Char('Endpunkt', help='Endpunkt Geschaeftskundenversand Produktionssystem', default='https://cig.dhl.de/services/production/soap/')
    dhl_order_api = fields.Selection([('1', 'Intraship'),('2', 'Versenden')], string='API-Version', help='Auswahl, welche API verwendet werden soll', default='1')
    #dhl_order_accountNumber = fields.Char('DHL Abrechnungsnummer', size=14, help='14stellige DHL Abrechnungsnummer')
    dhl_order_ekp = fields.Char('EKP Nummer', size=10, help='Die ersten zehn Ziffern Ihrer DHL Abrechnungsnummer')
    dhl_order_partner_id = fields.Char('DHL Teilnahme National', size=2, help='Die letzten zwei Ziffern ihrer DHL Abrechnungsnummer')
    dhl_order_intraship_user = fields.Char('Intraship Benutzername', help='Benutzername Intraship Account')
    dhl_order_intraship_password = fields.Char('Intraship Passwort', help='Passwort Intraship Account')
    dhl_order_endpoint_test = fields.Char('Endpunkt', help='Endpunkt Geschaeftskundenversand Sandbox', default='https://cig.dhl.de/services/sandbox/soap/')
    #dhl_order_accountNumber_test = fields.Char('DHL Abrechnungsnummer', size=14, help='DHL Abrechnungsnummer fuer Sandbox', default='22222222220101')
    #dhl_order_ekp_test = fields.Char('EKP Nummer Test', size=10, help='EKP Nummer für Sandbox', default='5000000000')
    dhl_order_ekp_test = fields.Char('EKP Nummer Test', size=10, help='EKP Nummer für Sandbox', default='2222222222')
    dhl_order_partner_id_test = fields.Char('DHL Teilnahme National Test', size=2, help='Teilnahme Nummer Sandbox', default='01')
    #dhl_order_intraship_user_test = fields.Char('Benutzername Test API 1.0', help='Benutzername Web-Service Sandbox', default='geschaeftskunden_api')
    #dhl_order_intraship_password_test = fields.Char('Passwort Test API 1.0', help='Passwort Web-Service Sandbox', default='Dhl_ep_test1')
    dhl_order_intraship_user_test = fields.Char('Benutzername Test', help='Benutzername Web-Service Sandbox', default='2222222222_01')
    dhl_order_intraship_password_test = fields.Char('Passwort Test', help='Passwort Web-Service Sandbox', default='pass')
    
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
    dhl_track_cig_pass_test = fields.Char('CIG Passwort Test', help='Passwort der Anwendung im Testmodus. Entspricht Entwicklerportal Passwort', default='1Q@dhl.com')'''
    
    # * Switch for activating test mode
    dhl_sandbox = fields.Boolean('DHL Test Modus', help='Alle DHL Anfragen laufen unter Testbedingungen. Es werden keine echten Labels erstellt oder Sendungen verfolgt')
