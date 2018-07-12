# -*- encoding: utf-8 -*-
##############################################################################
#
#    Globalteckz
#    Copyright (C) 2012 (http://www.globalteckz.com)
#
##############################################################################
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
from odoo import api, fields, models, _
from odoo.addons.gt_woocommerce_integration.api import API
from odoo.addons.gt_woocommerce_integration.api import woocom_api

class account_tax(models.Model):
    _inherit = "account.tax"

    wocomm_country_id = fields.Many2one('res.country',string="Country")
    wocomm_state_id = fields.Many2one('res.country.state',string='State',domain="[('country_id', '=', wocomm_country_id)]")



class account_invoice(models.Model):
    _inherit = "account.invoice"
                
    is_woocom =fields.Boolean('Woocommerce')
    total_discount_tax_excl=fields.Float('Discount(tax excl.)')
    total_discount_tax_incl=fields.Float('Discount(tax incl)')
    total_paid_tax_excl= fields.Float('Paid (tax excl.)')
    total_paid_tax_incl=fields.Float('Paid (tax incl.)')
    total_products_wt=fields.Float('Weight')
    total_shipping_tax_excl=fields.Float('Shipping(tax excl.)')
    total_shipping_tax_incl=fields.Float('Shipping(tax incl.)')
    total_wrapping_tax_excl=fields.Float('Wrapping(tax excl.)')
    total_wrapping_tax_incl=fields.Float('Wrapping(tax incl.)')
    shop_ids = fields.Many2many('sale.shop', 'invoice_shop_rel', 'invoice_id', 'shop_id', string="Shop")
    active_bool = fields.Boolean('button active')
# 

    def invoice_pay_customer_base(self):
        accountinvoice_link = self
        journal_id = self._default_journal()

        if self.type == 'out_invoice':
            self.with_context(type='out_invoice')
        elif self.type == 'out_refund':    
            self.with_context(type='out_refund')
        self.pay_and_reconcile(journal_id,accountinvoice_link.amount_total, False, False)
        return True    



    @api.multi
    def expotWoocomRefundOrder(self):
        # print ("expotWoocomREFUNDDDDDDOrder",self)

        invoice_obj = self.env['account.invoice']
        invoice_refund_obj = self.env['account.invoice.refund']
        sale_order_obj = self.env['sale.order']

        for invoice in self:
            refund_ids = invoice_obj.search([('origin', '=', invoice.number)])
            # print ("refund_idsssssssssss111111111",refund_ids)

            if refund_ids:
                refund_ids = invoice_obj.search([('id', '=', refund_ids.refund_invoice_id.id)])
                # print ("IFFFFFFFrefund_idss",refund_ids)

            if not refund_ids:
                refund_ids = invoice_obj.search([('id', '=', invoice.refund_invoice_id.id)])
                # print ("NOTTTTTrefund_idsss",refund_ids)

                sale_order_id = sale_order_obj.search([('name','=',refund_ids.origin)])
                # print ("SALEIDDDDDDDDDDD",sale_order_id)

            wcapi = API(url=sale_order_id.shop_id.woocommerce_instance_id.location, consumer_key=sale_order_id.shop_id.woocommerce_instance_id.consumer_key, consumer_secret=sale_order_id.shop_id.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            # print ("WCPIIIIIIIIIIIII",wcapi)

            invoice_vals = {
                 'amount' : str(self.amount_untaxed),
                 'reason' : str(self.name),
            }
            # print ("invoicevalsssssss",invoice_vals,sale_order_id.woocom_id)


            # data = {
            #             "amount": "400.00",
            #             'reason' : 'HELLO',
            #             "api_refund" : True,
            #         }
            # print ("dataaaaaaaaaaaa",data)
            # res = wcapi.post("orders/" + str(sale_order_id.woocom_id) + "/refunds", data)


            res = wcapi.post("orders/" + str(sale_order_id.woocom_id) + "/refunds", invoice_vals)
            # print ("RESSSSSSS",res)
            res = res.json()
            # print ("RESSS22222222",res)

            if res.get('data') == 200 :    
                invoice.write({'active_bool': 'True'})



    
account_invoice()

