# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import except_orm, Warning, RedirectWarning

#import datetime

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
                
    
    auto_sale = fields.Boolean(string='Automatischer E-Mail-Versand der Auftragsbestaetigung', help='Automatischer Versand E-Mail Auftragsbestaetigung', default=False)
    auto_purchase = fields.Boolean(string='Automatisches Annehmen der Lieferantenbestellung', help='Automatische Bestaetigung des ERSTEN vorkalkulierten Lieferantenangebots', default=False)
    auto_stock = fields.Boolean(string='Automatisches Bestätigen der Lieferung', help='Automatische Initiierung der Lieferung durch Versand E-Mail Lieferschein an Lager/Lieferant', default=False)
    auto_stock_carrier = fields.Boolean(string='Automatische Bestellung beim Logistiker', help='Automatische Bestellung der Paketlabels beim verknüpften Logistiker')
    auto_invoice = fields.Boolean(string='Automatischer E-Mail-Versand der Rechnung', help='Automatische Rechnungserstellung und Versendung nach Lieferung', default=False)
    
    dhl_check = fields.Boolean(string='Lieferant ist DHL', compute='_compute_dhl_check', default=False, store=True)
    del_is_company = fields.Boolean(related='partner_shipping_id.is_company', readonly=True)
    del_name1 = fields.Char(related='partner_shipping_id.del_name1', store=True)
    del_name2 = fields.Char(related='partner_shipping_id.del_name2', store=True)
    del_name1_parent = fields.Char(related='partner_shipping_id.parent_id.del_name1', store=True)
    del_name2_parent = fields.Char(related='partner_shipping_id.parent_id.del_name2', store=True)
    
    @api.model
    def synchronize_cron(self):
        _logger.info('Ich bins der Rechnungs-CronJob')
        
        #get all sale orders with manual invoice that are shipped
        so_ids = self.search([('state','=','manual'),('shipped','=',True),('auto_invoice','=',True)])
        _logger.debug(str(so_ids))
        
        #self.env['stock.picking'].search([])._get_origin() #besser ins first_install
        
        done_so_ids = []
        
        for so in so_ids:
            if so not in done_so_ids:
                sp_ids = self.env['stock.picking'].search([('orig_order','=',so.id)])
                all_done = True
                
                done_sp_ids = []
                not_done_sp_ids = []
                
                for sp in sp_ids:
                    if not sp.del_date:
                        sp._compute_date_done() #besser ins first_install
                all_done = all(sp.delivery_done or sp.del_date <= fields.Date.today() for sp in sp_ids)
                any_done = any(sp.delivery_done or sp.del_date <= fields.Date.today() for sp in sp_ids)
                
                if not any_done:
                    # kein einziger Lieferschein geliefert
                    # überspringe diesen Auftrag
                    _logger.debug('Skip %s - kein Lieferschein ausgeliefert' % (so.name))
                    continue
                if all_done:
                    # alle Lieferscheine geliefert
                    # Auftrag abrechnen (vor splitting check)
                    _logger.debug('Abrechnen %s - Alle Lieferscheine ausgeliefert' % (so.name))
                else:
                    all_done_no_backorder = all((sp.delivery_done or sp.del_date <= fields.Date.today()) and not sp.backorder_id for sp in sp_ids)
                    if all_done_no_backorder:
                        # alle Lieferscheine geliefert, die offenen sind Einlagerungen
                        # Auftrag abrechnen (vor splitting check)
                        _logger.debug('Abrechnen %s - alle offenen Lieferscheine sind Einlagerungen' % (so.name))
                    else:
                        # es gibt min einen parallelen Lieferschein (einer anderen Route) der noch nicht ausgeliefert wurde
                        # nimm alle fertigen ohne backorder und warte 7 tage vom kleinesten datum und rechne diese ab
                        _logger.debug('Wait %s - warte 7 Tage auf einen anderen Lieferschein' % (so.name))
                        
                # splitting check
                if not so.split_from and not so.splitting_counter:
                    # kein gesplitteter Auftrag
                    # Auftrag abrechnen
                    _logger.debug('NoSplit %s' % (so.name))
                elif so.split_from:
                    # suche Hauptauftrag
                    _logger.debug('SplitChild %s' % (so.name))
                else:
                    # du bist Hauptauftrag
                    _logger.debug('SplitParent %s' % (so.name))
    
    @api.multi
    def action_handle_order(self, context=None):
        for record in self:
        
            if record.dhl_check:
                if record.del_is_company and not record.del_name1:
                    raise Warning('Fehlender Versandname','Zum Nutzen des Versands muss mindestens das Feld Versandname 1 (Firmenname) gesetzt sein.')
                if not record.del_is_company and not record.del_name1:
                    raise Warning('Fehlender Versandname','Zum Nutzen des Versands muss mindestens das Feld Versandname 3 (Personenname) gesetzt sein.')
                if not record.del_is_company and not record.del_name1_parent:
                    raise Warning('Fehlender Versandname','Zum Nutzen des Versands muss mindestens das Feld Versandname 1 (Firmenname) gesetzt sein.')
                if not record.partner_shipping_id.zip:
                    raise Warning('Fehlende Postleitzahl', 'Im verwendeten Lieferkontakt ist keine Postleitzahl eingetragen')
                if record.partner_shipping_id.country_id.code == 'DE' and len(record.partner_shipping_id.zip) != 5:
                    raise Warning('Falsche Postleitzahl', 'Für den Versand in Deutschland wird eine 5stellige Postleitzahl benötigt')
                if not record.partner_shipping_id.city:
                    raise Warning('Fehlende Stadt', 'Im verwendeten Lieferkontakt ist keine Stadt eingetragen')
                if not record.partner_shipping_id.street_name:
                    raise Warning('Fehlende Strasse', 'Im verwendeten Lieferkontakt ist keine Strasse eingetragen')
                if not record.partner_shipping_id.street_number:
                    raise Warning('Fehlende Hausnummer', 'Im verwendeten Lieferkontakt ist keine Hausnummer eingetragen')
            
            tmp_state = record.state
            
            record.action_button_confirm()
            
            if record.auto_sale and tmp_state != 'sent':
                record.force_quotation_send()
                
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
                    sp.auto_stock = record.auto_stock and sp.move_lines and sp.move_lines[0] and sp.move_lines[0].product_id.categ_id.route_ids and sp.move_lines[0].product_id.categ_id.route_ids[0].auto_stock
                    sp.auto_stock_carrier = record.auto_stock_carrier and sp.move_lines and sp.move_lines[0] and sp.move_lines[0].product_id.categ_id.route_ids and sp.move_lines[0].product_id.categ_id.route_ids[0].auto_stock_carrier
                    sp.auto_invoice = record.auto_invoice and sp.move_lines and sp.move_lines[0] and sp.move_lines[0].product_id.categ_id.route_ids and sp.move_lines[0].product_id.categ_id.route_ids[0].auto_invoice
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
    
    @api.multi
    @api.onchange('release_quantity_check')
    def _onchange_release_quantity_check(self):
        for record in self:
            if not record.release_quantity_check:
                record.release_quantity_value = record.product_uom_qty
    
    @api.multi
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
                    record.release_quantity_value = record.release_quantity_input
                
    @api.multi
    @api.constrains('release_quantity_input')
    def _check_release_quantity(self):
        for record in self:
            if record.release_quantity_input < 0:
                raise Warning('Fehlerhafte Abrufmenge','Abrufmenge muss größer gleich 0 sein.')
            if record.release_quantity_input > record.product_uom_qty:
                raise Warning('Fehlerhafte Abrufmenge','Abrufmenge muss kleiner gleich der Bestellmenge sein.')
                

    release_quantity_value = fields.Float('Abrufmenge', compute='_compute_release_quantity', help="Anzahl der Produkte für einzelnen Lagerabrufe in der gleichen Einheit, wie die Standardmengeneinheit.")
    release_quantity_check = fields.Boolean('Abrufmenge aktivieren', help="Nur wenn dieser Schalter gesetzt ist, wird die Abrufmenge geliefert, sonst die komplette Bestellmenge.")
    release_quantity_input = fields.Float('Abrufmenge', help="Eingabefeld für die Abrufmenge")
    
                
class ama_rq_procurement_order(models.Model):
    _inherit = 'procurement.order'

    @api.v7
    def _run_move_create(self, cr, uid, procurement, context=None):
        vals = super(ama_rq_procurement_order, self)._run_move_create(cr, uid, procurement, context)
        vals.update({
            'release_quantity_value': procurement.sale_line_id and procurement.sale_line_id.release_quantity_value,
            'release_quantity_check': procurement.sale_line_id and procurement.sale_line_id.release_quantity_check,
            'release_quantity_input': procurement.sale_line_id and procurement.sale_line_id.release_quantity_input,
            })
        return vals
                    