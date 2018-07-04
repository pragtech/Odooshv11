# -*- encoding: utf-8 -*-
##############################################################################
#
#    Globalteckz
#    Copyright (C) 2012 (http://www.globalteckz.com)
#
##############################################################################
import time
from odoo import api, fields, models, _

class WoocommerceConnectorWizard(models.TransientModel):
    _name = "woocommerce.connector.wizard"
    
    @api.model
    def default_get(self, fields):
        result= super(WoocommerceConnectorWizard, self).default_get(fields)
        if self._context.get('active_model') == 'sale.shop':
            obj = self.env['sale.shop'].browse(self._context.get('active_id'))
            result.update({'shop_ids': self._context.get('active_ids'),
                           'last_order_import_date': obj.last_woocommerce_order_import_date,
                           'last_refund_order_import_date': obj.last_woocommerce_refund_order_import_date,
                           })
        return result
    
    shop_ids = fields.Many2many('sale.shop', string="Select Shops")
    #import fields
    import_order = fields.Boolean('Import Orders')
    last_order_import_date = fields.Date('Last woocom order Import Date')
    last_refund_order_import_date = fields.Date('Last woocom refund order Import Date')

    import_woocom_product = fields.Boolean('Import Products')
    import_category = fields.Boolean('Import Categories')
    import_customer = fields.Boolean('Import Customers')
    import_attribute = fields.Boolean('Import Products Attributes',help="Includes Product Attributes and Categories")
    import_inventory = fields.Boolean('Import Inventory')
    import_carrier = fields.Boolean('Import Carriers')
    import_payment = fields.Boolean('Import Payment Method')

    import_refung_order = fields.Boolean('Import Refunded Orders')
    import_product_tags = fields.Boolean('Import Product Tags')
    import_coupons = fields.Boolean('Import Coupons')

    # update fields
    update_categories=fields.Boolean("Update Categories")
    update_product_data = fields.Boolean('Update Product Data')
    update_woocom_product_inventory = fields.Boolean(string="Update Product Inventory")
    update_order_status = fields.Boolean('Update Order Status')

    update_product_tag=fields.Boolean("Update Product Tags")
    update_coupons=fields.Boolean("Update Coupons")

    export_woocom_customers = fields.Boolean(string="Export Customers")
    export_woocom_orders = fields.Boolean(string="Export Orders")
    export_woocom_products = fields.Boolean(string="Export Products")
    export_woocom_categories = fields.Boolean(string="Export Categories")

    export_woocom_product_tags = fields.Boolean(string="Export Product Tags")
    export_woocom_coupons = fields.Boolean(string="Export Coupons")

    

    @api.one
    def import_woocommerce(self):
        shop_ids=self.shop_ids

        if self.import_attribute:
            for shop_id in shop_ids:
                shop_id.importWoocomAttribute()

        if self.import_category:
            self.shop_ids.importWooCategory()

        if self.import_customer:
            self.shop_ids.importWoocomCustomer()

        if self.import_woocom_product:
            for shop_id in shop_ids:
                shop_id.importWoocomProduct()
       
        if self.import_inventory:
            for shop_id in shop_ids:
                shop_id.importWoocomInventory()

        if self.import_carrier:
            for shop_id in shop_ids:
                shop_id.importWoocomCarrier()
        
        if self.import_payment:
            for shop_id in shop_ids:
                shop_id.importWooPaymentMethod()
                
        if self.import_order:
            for shop_id in shop_ids:
                shop_id.with_context({'last_woocommerce_order_import_date': self.last_order_import_date}).importWoocomOrder()

        if self.import_refung_order:
            for shop_id in shop_ids:
                shop_id.with_context({'last_woocommerce_refund_order_import_date': self.last_refund_order_import_date}).importRefundOrder()
                # shop_id.importRefundOrder()
                


        if self.import_product_tags:
            for shop_id in shop_ids:
                shop_id.importTags()


        if self.import_coupons:
            for shop_id in shop_ids:
                shop_id.importCoupons()
        
       
        if self.update_categories:
            self.shop_ids.updateWoocomCategory()
# #           
        if self.update_product_data:
            self.shop_ids.updateWoocomProduct()
 
        if self.update_woocom_product_inventory:
            self.shop_ids.updateWoocomInventory()
            
        if self.update_order_status:
            self.shop_ids.updateWoocomOrderStatus()


        if self.update_product_tag:
            self.shop_ids.updateWoocomProductTag()

 
        if self.update_coupons:
            self.shop_ids.updateWoocomCoupons()

# 
        if self.export_woocom_customers:
            self.shop_ids.exportWoocomCustomers()
# 
        if self.export_woocom_categories:
            self.shop_ids.exportWoocomCategories()
 


        if self.export_woocom_product_tags:
            self.shop_ids.exportWoocomProductTags()


        if self.export_woocom_coupons:
            self.shop_ids.exportWoocomCoupons()
 


        if self.export_woocom_products:
            self.shop_ids.exportWoocomProduct()
 
        if self.export_woocom_orders:
            self.shop_ids.expotWoocomOrder()
#             print"=====self.shop_ids.export_presta_orders()>>>>>>>>>>",self.shop_ids.export_woocom_orders()

        return True
