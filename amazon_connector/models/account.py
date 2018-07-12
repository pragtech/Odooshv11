# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger('amazon')

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError
class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    is_amazon = fields.Boolean(string='Is Amazon')
    fullfilment_shop = fields.Selection([('MFN','MFN'),('AFN','AFN')],'Fullfillment Shop',track_visibility='always')

    @api.multi
    def invoice_pay_customer_base(self):
        order_obj = self.env['sale.order']
        for rec in self:
            ctx = self._context.copy()
            if rec.type == 'out_invoice' and (rec.fullfilment_shop=='MFN' or rec.fullfilment_shop=='AFN'):
             
                self.env.cr.execute("SELECT invoice_id, order_id FROM sale_order_invoice_rel WHERE invoice_id =%d" % (rec.id,))
                saleorder_res = dict(self.env.cr.fetchone())
                saleorder_id = saleorder_res[saleorder_res[1]]
                order = order_obj.browse(saleorder_id)
                 
                ctx['type'] = 'out_invoice'
                journal_id = self.with_context(ctx)._get_journal()
                currency_id = self.with_context(ctx)._get_currency()
                ctx['currency_id'] = currency_id
                if rec.state == 'draft':
                    rec.signal_workflow('invoice_open')
                rec.with_conetxt(ctx).pay_and_reconcile(journal_id, rec.amount_total)
                order.write({'state':'done'})
        return True
    
    @api.model
    def create(self, vals):
        if vals.get('type') =='out_refund':
            origin_id = self.search([('number','=',vals.get('origin'))])
            if origin_id:
                vals.update({'is_amazon':True})
        if self._context.get('from_amazon',False):
            vals.update({'is_amazon':True})
        return super(AccountInvoice, self).create(vals)
    
    @api.multi
    def invoice_pay_customer(self):
        order_obj = self.env['sale.order']
        purchase_obj = self.env['purchase.order']
        for invoice in self:
            if invoice.type == 'out_invoice':
                self.env.cr.execute("SELECT invoice_id, order_id FROM sale_order_invoice_rel WHERE invoice_id =%d" % (invoice.id,))
                saleorder_res = dict(self.env.cr.fetchone())
                saleorder_id = saleorder_res[1]
                order = order_obj.browse(saleorder_id)
                journal = order.journal_id.id
                acc_id = journal.default_credit_account_id and journal.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('Your journal must have a default credit and debit account.'))
                invoice.signal_workflow('invoice_open')
                invoice.pay_and_reconcile(journal, invoice.amount_total)
                order.write({'state': 'done'})
    
            elif invoice.type == 'in_invoice':
                self.env.cr.execute("SELECT invoice_id, purchase_id FROM purchase_invoice_rel WHERE invoice_id =%d" % (invoice.id,))
                purchase_res = dict(self.env.cr.fetchone())
                purchase_id = purchase_res[1]
                purchase = purchase_obj.browse(purchase_id)
                journal = purchase.journal_id
                acc_id = journal.default_credit_account_id and journal.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('Your journal must have a default credit and debit account.'))
                paid = True
                picking_ids = purchase.picking_ids
                if picking_ids:
                    for picking in picking_ids:
                        picking.write({'invoice_state':'invoiced'})
                        if picking.state == 'done':
                            purchase.write({'state':'done'})
                        else:
                            purchase.write({'state':'invoiced'})
                else:
                    purchase.write({'state':'invoiced'})
                invoice.pay_and_reconcile(journal, invoice.amount_total)
        return True
    
    @api.multi
    def confirm_paid(self):
        order_obj = self.env['sale.order']
        res = super(AccountInvoice, self).confirm_paid()
        for rec in self:
            if res.type == 'out_invoice':
                self.env.cr.execute("SELECT invoice_id, order_id FROM sale_order_invoice_rel WHERE invoice_id =%d" % (rec.id,))
                saleorder_res = dict(self.env.cr.fetchone())
                saleorder_id = saleorder_res[saleorder_res[1]]
                order = order_obj.browse(saleorder_id).order_policy
                if order.order_policy == 'prepaid':
                    order.write({'state':'progress'})
                else:
                    order.write({'state':'done'})
                    order.picking_ids.write({'invoice_state':'invoiced'})
        return res
    
class AccountInvoiceLine(models.Model):
    _inherit='account.invoice.line'
        
    shipping_price=fields.Float('Shipping Price')
    ship_discount=fields.Float('Shipping Discount')
    gift_cost=fields.Float('Gift Cost')
    
    
    
class AccountTax(models.Model):
    _inherit='account.tax'
    
    amazon_country_id = fields.Many2one('res.country',string='Amazon Country')
    amazon_state_id = fields.Many2one('res.country.state',string='Amazon State',domain="[('country_id', '=', amazon_country_id)]")

              
