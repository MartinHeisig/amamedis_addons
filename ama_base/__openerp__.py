# -*- coding: utf-8 -*-
{
    'name': "Amamedis Base",

    'summary': "Adds custom fields for Amamedis",

    'description': """
Amamedis Basis Modul
====================

Fügt extra Felder für Amamedis hinzu

Partner
-------
    * Lastschrift Mandatsreferenz
    * BGA
    * Vorname / Firmenname Zusatz
    * Geschlecht
    * Filialen
    * Owncloud-Verzeichnis
    * Funktion Kontakte hinzufügen/entfernen ohne anlegen/löschen
    * Funktion Anzeigename mit Strasse/Ort/PLZ/Kundennr
    * Smart-Buttons in Kontakt-Popup
    
Produkte
--------
    * Beschreibung für Bestellscheine
    * Mindestbestellmenge
    
Verkaufsteams
-------------
    * Logo
    * Absenderemail
    * Signatur
    * Absenderzeile
    * Fußzeile
    * Ansprechpartner
    * Briefabschluss
    
Angebot und Auftrag
-------------------
    * Lieferdatum
    * Bestelldatum
    
Auftragszeilen
--------------
    * Funktion automatische VE-Auswahl bei Produktwechsel
    * Infofeld Mindestbestellmenge
    """,

    'author': "Martin Heisig",
    'website': "https://github.com/MartinHeisig/amamedis_addons.git",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Tools',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'product', 'sale_stock', 'purchase'],

    # always loaded
    'data': [
        'ama_base_partner_view.xml',
        'ama_base_product_view.xml',
        'ama_base_sale_view.xml',
        'ama_base_purchase_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo.xml',
    ],
}
