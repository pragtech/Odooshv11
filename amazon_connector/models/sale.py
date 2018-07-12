# -*- coding: utf-8 -*-
import urllib
import base64
import logging
logger = logging.getLogger('sale')

from odoo import api, fields, models, _
from datetime import timedelta, datetime, time
from odoo import netsvc
from odoo.tools.translate import _
from odoo.addons.amazon_connector.amazon_api import amazonerp_osv as amazon_api_obj

class PosSaleReport(models.Model):
    _inherit = 'report.all.channels.sales'

    state_id= fields.Many2one('res.country.state', string='Parnter State', readonly=True)
    amount_tax= fields.Float(string='Taxes', readonly=True)
    
    def _so(self):
        so_str = """
            WITH currency_rate as (%s)
                SELECT sol.id AS id,
                    so.name AS name,
                    so.partner_id AS partner_id,
                    sol.product_id AS product_id,
                    pro.product_tmpl_id AS product_tmpl_id,
                    so.date_order AS date_order,
                    so.user_id AS user_id,
                    pt.categ_id AS categ_id,
                    so.company_id AS company_id,
                    sol.price_total / COALESCE(cr.rate, 1.0) AS price_total,
                    so.amount_tax / COALESCE (cr.rate, 1.0) AS amount_tax,
                    so.pricelist_id AS pricelist_id,
                    rp.country_id AS country_id,
                    rp.state_id AS state_id,
                    sol.price_subtotal / COALESCE (cr.rate, 1.0) AS price_subtotal,
                    (sol.product_uom_qty / u.factor * u2.factor) as product_qty,
                    so.analytic_account_id AS analytic_account_id,
                    so.team_id AS team_id

            FROM sale_order_line sol
                    JOIN sale_order so ON (sol.order_id = so.id)
                    LEFT JOIN product_product pro ON (sol.product_id = pro.id)
                    JOIN res_partner rp ON (so.partner_id = rp.id)
                    LEFT JOIN product_template pt ON (pro.product_tmpl_id = pt.id)
                    LEFT JOIN product_pricelist pp ON (so.pricelist_id = pp.id)
                    LEFT JOIN currency_rate cr ON (cr.currency_id = pp.currency_id AND
                        cr.company_id = so.company_id AND
                        cr.date_start <= COALESCE(so.date_order, now()) AND
                        (cr.date_end IS NULL OR cr.date_end > COALESCE(so.date_order, now())))
                    LEFT JOIN product_uom u on (u.id=sol.product_uom)
                    LEFT JOIN product_uom u2 on (u2.id=pt.uom_id)
        """ % self.env['res.currency']._select_companies_rates()
        return so_str
    
    def get_main_request(self):
        request = """
            CREATE or REPLACE VIEW %s AS
                SELECT id AS id,
                    name,
                    partner_id,
                    product_id,
                    product_tmpl_id,
                    date_order,
                    user_id,
                    categ_id,
                    company_id,
                    price_total,
                    amount_tax,
                    pricelist_id,
                    analytic_account_id,
                    country_id,
                    state_id,
                    team_id,
                    price_subtotal,
                    product_qty
                FROM %s
                AS foo""" % (self._table, self._from())
        return request
    
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    @api.model
    def _default_journal(self):
        accountjournal_obj = self.env['account.journal']
        accountjournal_ids = accountjournal_obj.search([('name','=','Sales Journal')])
        if accountjournal_ids:
            return accountjournal_ids[0]
        return False
        
    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            amazon_tax = 0.0
            for line in order.order_line:
                print("amazon_taxamazon_tax",line.new_tax_amount)
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amazon_tax += line.new_tax_amount
            if order.amazon_order or order.magento_order:
                amount_tax = amazon_tax
            else:
                amount_tax = amount_tax
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })    
    
    amazon_order_id = fields.Char(string='Order ID', size=256)
    shipping_submission_feedid = fields.Char(string='Submission Feed ID',size=15)
    journal_id = fields.Many2one('account.journal', string='Journal',readonly=True)
    faulty_order = fields.Boolean(string='Faulty')
    confirmed = fields.Boolean(string='Confirmed')
    fullfillment_method = fields.Selection([('MFN','MFN'),('AFN','AFN')], string='Fullfillment Shop', track_visibility='always')
    ship_service = fields.Char(string='ShipServiceLevel', size=64)
    ship_category = fields.Char(string='ShipmentServiceLevelCategory')
    late_ship_date = fields.Datetime(string='LatestShipDate')
    shipped_by_amazon = fields.Boolean(string='ShippedByAmazonTFM')
    order_type = fields.Char(string='OrderType')
    amazon_order_status = fields.Char(string='OrderStatus')
    earlier_ship_date = fields.Datetime(string='EarliestShipDate')
    amazon_payment_method = fields.Char(string='PaymentMethod')
    amazon_order = fields.Boolean(string='Amazon ORder')
    updated = fields.Boolean(string='Updated Orders', default=False)
    item_shipped = fields.Char(string='Number of item shipped')
    item_unshipped = fields.Char(string='Number of item unshipped')
    is_prime = fields.Boolean(string='Is Prime')
    fullfillment_shop = fields.Char(string='Fullfillment Shop')
#     amazon_orderlisting_ids = fields.One2many('amazon.order.listing', 'sale_id','Order Listing')
    stateorigin = fields.Char(string='State Or Region')
    amazonstate_id= fields.Many2one(related='partner_id.state_id', string='State', store=True)
    recipient_name = fields.Char(string='Recipient Name')
#     new_tax_amount= fields.Float(string='New Taxes', readonly=True)
      
    @api.multi
    def oe_status(self):
        self.action_confirm()
        return True
    
    @api.multi
    def oe_status_invoice(self, cr, uid, ids):
        for order in self:
            order.invoice_ids.signal_workflow('invoice_open')
            order.invoice_ids.invoice_pay_customer_base()
        return True
    
    @api.model
    def create(self, vals):
        print ("valsvalsvalsvalsvals",vals)
        res = super(SaleOrder, self).create(vals)
        print ("resresresresresres",res)
        return res
    
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    

    order_item_id = fields.Char(string='Order Item ID', size=256)
    asin = fields.Char(string='Asin', size=256)
    notes = fields.Char(string='Notes',size=256)
    item_price = fields.Float(string='Item Price')
    shipping_price = fields.Float(string='Shipping Price')
    gift_cost = fields.Float(string='Gift Costs')
    new_tax_amount = fields.Float(string='New Tax')
    
    
    
#     @api.multi
#     def name_get(self):
#         result = []
#         for so_line in self:
#             name = '%s - %s' % (so_line.order_id.name, so_line.name.split('\n')[0] or so_line.product_id.name)
#             if so_line.order_partner_id.ref:
#                 name = '%s (%s)' % (name, so_line.order_partner_id.ref)
#             result.append((so_line.id, name))
#         return result
# 
#     @api.model
#     def name_search(self, name='', args=None, operator='ilike', limit=100):
#         if operator in ('ilike', 'like', '=', '=like', '=ilike'):
#             args = expression.AND([
#                 args or [],
#                 ['|', ('order_id.name', operator, name), ('name', operator, name)]
#             ])
#         return super(SaleOrderLine, self).name_search(name, args, operator, limit)
    
    
    
    
    
    
    
