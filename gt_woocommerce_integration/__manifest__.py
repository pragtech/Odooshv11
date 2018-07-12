# -*- encoding: utf-8 -*-
##############################################################################
#
#    Globalteckz
#    Copyright (C) 2012 (http://www.globalteckz.com)
#
##############################################################################

{
    "name" : "Woocommerce Connector",
    "author" : "Globalteckz",
    "category" : "Sales",
    "depends" : ['base','sale_shop','account', 'product_images_olbs','delivery','stock','sale'],
    "description": """
    This Module implements a basic Woocommerce Integration Functionality
    """,
    "data": [
      'security/woocommerce_security.xml',
      'security/ir.model.access.csv',
      'data/scheduler.xml',
#      'data/product_data.xml',
      'data/woocom_sequence_data.xml',
      'data/product_data.xml',
      'views/wocommerce_integration_view.xml',
      'views/sale_shop_view.xml',
      'views/woocom_account_view.xml',
      'wizard/woocom_connector_wizard_view.xml',
      'wizard/woocom_export_categ_view.xml',
      'wizard/woocom_export_product_view.xml',
      'wizard/woocom_export_order_view.xml',
      'wizard/woocom_export_customer_view.xml',
      'views/woocommerce_dashboard_view.xml',
      'views/order_workflow_view.xml',
      'views/product_attribute_view.xml',
      'views/product_tag_view.xml',
      'views/coupon_view.xml',
      'views/woocom_product_view.xml',
      'views/res_partner_view.xml',
      'views/carrier_woocom_view.xml',
      'views/payment_gatway_view.xml',
      'views/woocom_order_view.xml',
      'views/stock_view.xml',
      'views/woocommerce_log_view.xml',
      'views/sale_analysis_view.xml',
      'views/wocommerce_menus.xml',
#      
    ],
    "installable": True,
    "active": True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
