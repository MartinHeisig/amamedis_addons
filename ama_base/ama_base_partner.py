# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 artmin - IT Dienstleistungen.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning

class amamedis_partner(models.Model):

    _inherit = 'res.partner'
    _description = "Add custom fields for Amamedis partner."

    display_name = fields.Char(string='Name', compute='_compute_display_name')
    debit_ref = fields.Char('Lastschrift Mandatsreferenz', size=64)
    bga = fields.Char('BGA', size=64)
    first_name = fields.Char('Vorname / Firmenname Zusatz', size=64)
    gender = fields.Selection((('w','weiblich'),('m','männlich')), 'Geschlecht')
    contact_add = fields.Many2one('res.partner', 'Kontakt verknüpfen', domain=[('active','=',True),('parent_id','=',False)])
    contact_remove = fields.Many2one('res.partner', 'Verknüpfung auflösen')
    branch_ids = fields.Many2many('res.partner', 'res_partner_branch', 'partner_id', 'branch_id', 'Filialen')
    oc_folder = fields.Char('Owncloud-Verzeichnis')
    type = fields.Selection(selection_add=[('fax', 'Fax')])
    has_fax_contact = fields.Boolean('Faxkontakt existiert', compute='_compute_has_fax_contact', store=True)
    is_main = fields.Boolean('ist Hauptapotheke', default=False, help='Gibt an, ob es sich um eine Hauptapotheke handelt.')
    is_cooperation = fields.Boolean('ist Kooperation', default=False, help='Gibt an, ob ein Unternehmen eine Kooperation ist.')
    cooperation_id = fields.Many2one('res.partner', 'gehört zu Kooperation', domain=[('active','=',True),('is_cooperation','=',True)], help='die zugehoerige Kooperation')
    
    '''Better Way for new Api but doesnt change the name in Many2One DropDown fields'''
    @api.multi
    @api.depends('name', 'first_name', 'parent_id.name', 'city', 'zip', 'ref', 'email')
    def _compute_display_name(self):
        if self._context is None:
            self._context = {}
        for record in self:
            name = record.name
            '''if not record.is_company and record.first_name:
                name = "%s %s" % (record.first_name, name)'''
            if record.parent_id and not record.is_company:
                name = "%s, %s" % (record.parent_name, name)
            if record.city and record.zip:
                name += ' (' + record.city + ' ' + record.zip + ')'
            elif record.city:
                name += ' (' + record.city + ')'
            elif record.zip:
                name += ' (' + record.zip + ')'
            if self._context.get('show_address_only'):
                name = self._display_address(record, without_company=True)
            if self._context.get('show_address'):
                name = name + "\n" + self._display_address(record, without_company=True)
            if self._context.get('show_street') and record.street:
                name += "\n" + record.street
            if self._context.get('show_ref') and record.ref:
                name += "\n" + record.ref
            '''if self._context.get('show_email') and record.email:
                name += "\n" + record.email'''
            name = name.replace('\n\n','\n')
            name = name.replace('\n\n','\n')
            if self._context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            record.display_name = name
            
    @api.multi
    def action_compute_ref(self):
        for record in self:
            ref = ((record.section_id and record.section_id.code) or '') + (record.bga or str(record.id))
            if self.env['res.partner'].search_count([('ref', '=', ref)]):
                raise Warning('Generierung fehlgeschlagen - Kundennummer %s ist schon in Benutzung. Bitte manuell eingeben!' % ref)
            else:
                record.ref = ref
                
    @api.multi
    @api.depends('fax', 'child_ids')
    def _compute_has_fax_contact(self):
        for record in self:
            record.has_fax_contact = False
            if record.fax:
                for child in record.child_ids:
                    if child.name == "Mail2Fax" + record.fax or child.email == record.fax + "@fax.fax-mobile.de":
                        record.has_fax_contact = True
                        return
            else:
                record.has_fax_contact = True

    @api.multi
    def action_generate_fax_contact(self):
        for record in self:
            record._compute_has_fax_contact()
            if not record.has_fax_contact:
                self.env['res.partner'].create({
                    'name': "Mail2Fax" + record.fax,
                    'email': record.fax + "@fax.fax-mobile.de",
                    'type': 'fax',
                    'fax': record.fax,
                    'function': 'Fax',
                    'is_company': False,
                    'parent_id': record.id,
                    'use_parent_address': True,
                    'category_id': [(4, 27)],
                    'customer': False,
                    'supplier': False,
                    })

    ''' Adds city to all displays of partners and gives possibility to show city
    in many2one relation.'''
    @api.multi
    @api.depends('name', 'first_name', 'parent_id.name', 'city', 'zip', 'ref', 'email')
    def name_get(self):
        if self._context is None:
            self._context = {}
        res = []
        for record in self:
            name = record.name
            if record.parent_id and not record.is_company:
                name = "%s, %s" % (record.parent_name, name)
            if record.city and record.zip:
                name += ' (' + record.city + ' ' + record.zip + ')'
            elif record.city:
                name += ' (' + record.city + ')'
            elif record.zip:
                name += ' (' + record.zip + ')'
            if self._context.get('show_address_only'):
                name = self._display_address(record, without_company=True)
            if self._context.get('show_address'):
                name = name + "\n" + self._display_address(record, without_company=True)
            if self._context.get('show_street') and record.street:
                name += "\n" + record.street
            if self._context.get('show_ref') and record.ref:
                name += "\n" + record.ref
            if self._context.get('show_email_add') and record.email:
                if not record.is_company and record.first_name:
                    name += "\n" + "%s %s <%s>" % (record.first_name, record.name, record.email)
                else:
                    name += "\n" + "%s <%s>" % (record.name, record.email)
            name = name.replace('\n\n','\n')
            name = name.replace('\n\n','\n')
            if self._context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            res.append((record.id, name))
        return res
        
    @api.multi
    def add_contact(self, context={}):
        for record in self:
            # raise except_orm('ADD', str(context))
            if context.get('contact_add'):
                self.env['res.partner'].browse(context.get('contact_add')).parent_id = record
            record.contact_add = False
        return
    
    @api.multi
    def remove_contact(self, context={}):
        for record in self:
            if context.get('contact_remove'):
                self.env['res.partner'].browse(context.get('contact_remove')).parent_id = False
                self.env['res.partner'].browse(context.get('contact_remove')).use_parent_address = False
            record.contact_remove = False
        return
    
    @api.multi
    def write(self, vals):
        if vals.get('contact_add'):
            vals['contact_add'] = False
        if vals.get('contact_remove'):
            vals['contact_remove'] = False
        result = super(amamedis_partner, self).write(vals)
        return result
        
    @api.model
    def create(self, vals):
        if vals.get('contact_add'):
            vals['contact_add'] = False
        if vals.get('contact_remove'):
            vals['contact_remove'] = False
        partner = super(amamedis_partner, self).create(vals)
        return partner
