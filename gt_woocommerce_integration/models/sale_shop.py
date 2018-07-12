# -*- coding: utf-8 -*-
#############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import urllib.request
from odoo import api, fields, models, _
from odoo.addons.gt_woocommerce_integration.api import API
from odoo.addons.gt_woocommerce_integration.api import woocom_api
import logging
from datetime import timedelta, datetime, date, time
import time
logger = logging.getLogger('__name__')
# import urllib
# import requests
# from urllib import urlopen
import base64
import sys, json
from odoo.exceptions import UserError
import datetime
from datetime import datetime, timedelta, date


class SaleShop(models.Model):
    _inherit = "sale.shop"


    @api.model
    def _get_shipment_fee_product(self):
        product = self.env.ref('gt_woocommerce_integration.product_product_shipping')
        return product and product.id or False
    
    @api.model
    def _get_shipment_gift_product(self):
        product = self.env.ref('gt_woocommerce_integration.product_product_gift_wrapp')
        return product and product.id or False
    
    code = fields.Char(srting='Code')
    name = fields.Char('Name')

    woocommerce_shop = fields.Boolean(srting='Woocommerce Shop')
    woocommerce_instance_id = fields.Many2one('woocommerce.instance', srting='Woocommerce Instance', readonly=True)
#     woocommerce_id = fields.Char(string='shop Id')

    # ## Product Configuration
    product_import_condition = fields.Boolean(string="Create New Product if Product not in System while import order", default=True)
#     route_ids = fields.Many2many('stock.location.route', 'shop_route_rel', 'shop_id', 'route_id', string='Routes')

    # Order Information
    company_id = fields.Many2one('res.company', srting='Company', required=False,
                                 default=lambda s: s.env['res.company']._company_default_get('stock.warehouse'))
    prefix = fields.Char(string='Prefix')
    suffix = fields.Char(string='Suffix')
    shipment_fee_product_id = fields.Many2one('product.product', string="Shipment Fee", domain="[('type', '=', 'service')]", default=_get_shipment_fee_product)
    gift_wrapper_fee_product_id = fields.Many2one('product.product', string="Gift Wrapper Fee", domain="[('type', '=', 'service')]", default=_get_shipment_gift_product)
    sale_journal = fields.Many2one('account.journal')
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist')
    partner_id = fields.Many2one('res.partner', string='Customer')
    workflow_id = fields.Many2one('import.order.workflow', string="Order Workflow")
    on_fly_update_order_status = fields.Boolean(string="Update on Shop at time of Odoo Order Status Change", default=True)
    # stock Configuration
    on_fly_update_stock = fields.Boolean(string="Update on Shop at time of Odoo Inventory Change", default=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    # Schedular Configuration
    auto_import_order = fields.Boolean(string="Auto Import Order", default=True)
    auto_import_products = fields.Boolean(string="Auto Import Products", default=True)
    auto_update_inventory = fields.Boolean(string="Auto Update Inventory", default=True)
    auto_update_order_status = fields.Boolean(string="Auto Update Order Status", default=True)
    auto_update_product_data = fields.Boolean(string="Auto Update Product data", default=True)
    auto_update_price = fields.Boolean(string="Auto Update Price", default=True)
    auto_update_customer_data  = fields.Boolean(string="Auto Update Customer", default=True)

    # Import last date
    last_woocommerce_inventory_import_date = fields.Datetime(srting='Last Inventory Import Time')
    last_woocommerce_product_import_date = fields.Datetime(srting='Last Product Import Time')
    last_woocommerce_product_attrs_import_date = fields.Datetime(srting='Last Product Attributes Import Time')
    last_woocommerce_order_import_date = fields.Date(srting='Last Order Import Time')

    last_woocommerce_refund_order_import_date = fields.Date(srting='Last Refund Order Import Time')

    last_woocommerce_msg_import_date = fields.Datetime(srting='Last Message Import Time')


    # Update last date
    woocommerce_last_update_category_date = fields.Datetime(srting='Woocom last update category date')
    woocommerce_last_update_customer_date = fields.Datetime(srting='Woocom last update customer date')

    woocommerce_last_update_inventory_date = fields.Datetime(srting='Woocom last update inventory date')
    woocommerce_last_update_catalog_rule_date = fields.Datetime(srting='Woocom last update catalog rule date')
    woocommerce_last_update_product_data_date = fields.Datetime(srting='Woocom last update product data rule date')
    woocommerce_last_update_order_status_date = fields.Datetime(srting='Woocom last update order status date')

    woocommerce_last_update_product_tag_date = fields.Datetime(srting='Woocom last update product tag date')
    woocommerce_last_update_coupon_date = fields.Datetime(srting='Woocom last update coupon date')

    # Export last date
    prestashop_last_export_product_data_date = fields.Datetime(string='Last Product Export Time')
    
    @api.one
    def create_woo_attr(self, attr_val, wcapi):

        prod_att_obj = self.env['product.attribute']
        prod_attr_vals_obj = self.env['product.attribute.value']
        attribute_list = []
        attribute_val = {
                'name':attr_val.get('name'),
                'woocom_id' : attr_val.get('id'),
        }
        attrs_ids = prod_att_obj.search([('woocom_id', '=', attr_val.get('id'))])

        if not attrs_ids:
            att_id = prod_att_obj.create(attribute_val)
        else:
            attrs_ids[0].write(attribute_val)
            att_id = attrs_ids[0]

        logger.info('Value ===> %s', att_id.name)
        attribute_value_rul = "products/attributes/" + str(attr_val.get('id')) + "/terms"
        attr_value_list = wcapi.get(attribute_value_rul)
        attr_value_list = attr_value_list.json()

        if attr_value_list.get('product_attribute_terms'):
            for attr_val in attr_value_list.get('product_attribute_terms'):

                attrs_op_val = {
                    'attribute_id': att_id.id,
                    'woocom_id': attr_val.get('id'),
                    'name': attr_val.get('slug'),
                }
                attrs_ids = prod_attr_vals_obj.search([('woocom_id', '=', attr_val.get('id')), ('attribute_id', '=', att_id.id)])
                if attrs_ids:
                    attrs_ids[0].write(attrs_op_val)
                    # attribute_list.append(attrs_ids[0].id)
                else:
                    v_id = prod_attr_vals_obj.create(attrs_op_val)
                    # attribute_list.append(v_id.id)
            return attribute_list

    @api.multi
    def importWoocomAttribute(self):
        # print ("IMPORT_ATRRRRRRRRRRRRRRr")
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=False, version='v3')
#             try:
            r = wcapi.get("products/attributes")
            logger.error('rrrrrrrrrr ===> %s', r.text)
            if not r.status_code:
                raise UserError(_("Enter Valid url"))
            attribute_list = r.json()
            if attribute_list.get('product_attributes'):
#                     try:
                for attribute in attribute_list.get('product_attributes'):
                    shop.create_woo_attr(attribute, wcapi)
#                     except Exception as e:
#                         if self.env.context.get('log_id'):
#                             log_id = self.env.context.get('log_id')
#                             self.env['log.error'].create({'log_description': str(e) + " While Getting Atribute info of %s" % (attribute_list.get('product_attributes')), 'log_id': log_id})
#                         else:
#                             log_id = self.env['woocommerce.log'].create({'all_operations':'import_attribute', 'error_lines': [(0, 0, {'log_description': str(e) + " While Getting Atribute info of %s" % (attribute_list.get('product_attributes'))})]})
#                             self = self.with_context(log_id=log_id.id)
#             except Exception as e:
#                 if self.env.context.get('log_id'):
#                     log_id = self.env.context.get('log_id')
#                     self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
#                 else:
#                     log_id = self.env['woocommerce.log'].create({'all_operations':'import_attributes', 'error_lines': [(0, 0, {'log_description': str(e)})]})
#                     self = self.with_context(log_id=log_id.id)
        return True

    
    # @api.multi
    # def importWoocomAttribute(self):
    #     for shop in self:
    #             wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=False, version='v3')
    #         # try:
    #             count = 1
    #             r = wcapi.get("products/attributes")
    #             logger.error('rrrrrrrrrr ===> %s', r.text)
    #             if not r.status_code:
    #                 raise UserError(_("Enter Valid url"))
    #             attribute_list = r.json()
    #             while len(attribute_list) > 0:
    #                 if attribute_list.get('product_attributes'):
    #                     for attribute in attribute_list.get('product_attributes'):
    #                         shop.create_woo_attr(attribute, wcapi)
    #                         count+=1
    #                         attribute_list = wcapi.get("products/attributes?page="+ str(count))
    #                         attribute_list = attribute_list.json()
    #         # except Exception as e:
    #         #     print ("Error.............%s",e)
    #         #     pass
    #     return True

    
    @api.one
    def get_categ_parent(self, category, wcapi):
        prod_category_obj = self.env['woocom.category']
        vals = {
            'woocom_id': str(category.get('id')),
            'name': category.get('name'),
        }
        category_check = prod_category_obj.search([('woocom_id', '=', category.get('parent'))])
        if not category_check:
            if int(category.get('parent')) == 0:
                vals.update({'parent_id': False})
            else:
                cat_url = 'products/categories/' + str(category.get('parent'))
                valsss = wcapi.get(cat_url)
                valsss = valsss.json()
                parent_id = self.get_categ_parent(valsss, wcapi)[0]
                vals.update({'parent_id': parent_id[0].id})
            parent_id = prod_category_obj.create(vals)
            logger.info('Created Category ===> %s' % (parent_id.id))
            if parent_id:
                self.env.cr.execute("select categ_id from woocom_category_shop_rel where categ_id = %s and shop_id = %s" % (
                    parent_id.id, self.id))
                categ_data = self.env.cr.fetchone()
                if categ_data == None:
                    self.env.cr.execute("insert into woocom_category_shop_rel values(%s,%s)" % (parent_id.id, self.id))
            return parent_id
        else:
            parent_id = prod_category_obj.create(vals)
            if parent_id:
                self.env.cr.execute("select categ_id from woocom_category_shop_rel where categ_id = %s and shop_id = %s" % (
                    parent_id.id, self.id))
                categ_data = self.env.cr.fetchone()
                if categ_data == None:
                    self.env.cr.execute("insert into woocom_category_shop_rel values(%s,%s)" % (parent_id.id, self.id))
            return parent_id
    
    @api.one
    def create_woo_category(self, category, wcapi):
        
        prod_category_obj = self.env['woocom.category']
        category_check = prod_category_obj.search([('woocom_id', '=', category.get('id'))])
        if not category_check:
            vals = {
                'woocom_id': str(category.get('id')),
                'name': category.get('name'),
                }
            parent_category_check = prod_category_obj.search([('woocom_id', '=', category.get('parent'))])
            if not parent_category_check:
                if int(category.get('parent')) != 0:
                    cat_url = 'products/categories/' + str(category.get('parent'))
                    # print ("cat_url=========>",cat_url)
                    valsss = wcapi.get(cat_url)
                    valsss = valsss.json()
               
                    parent_id = self.get_categ_parent(valsss.get("product_category"), wcapi)[0].id
                else:
                    parent_id = False
                vals.update({'parent_id': parent_id})
            else:
                vals.update({'parent_id': parent_category_check[0].id})
            logger.info('Created vals ===> %s' % vals)
            cat_id = prod_category_obj.create(vals)
            logger.info('Created Category ===> %s' % (cat_id.id))
            return cat_id
        else:
            vals = {
                'woocom_id': str(category.get('id')),
                'name': category.get('name'),
            }
            parent_category_check = prod_category_obj.search([('woocom_id', '=', category.get('parent'))])
            if not parent_category_check:
                if int(category.get('parent')) != int('0'):
                    cat_url = 'products/categories/' + str(category.get('parent'))
                    valsss = wcapi.get(cat_url)
                    valsss = valsss.json()
                    parent_id = self.get_categ_parent(valsss, wcapi)[0].id
                else:
                    parent_id = False
                vals.update({'parent_id': parent_id})
            else:
                vals.update({'parent_id': parent_category_check[0].id})
            category_check[0].write(vals)
            return category_check[0]
    
    @api.multi
    def importWooCategory(self):
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            try:
                count = 1
                categ = wcapi.get("products/categories?page="+ str(count))
                if not categ.status_code:
                    raise UserError(_("Enter Valid url"))
                category_list = categ.json()
#                 try:
                for category in category_list:
                    shop.create_woo_category(category, wcapi)
                while len(category_list) > 0:
                    count += 1
                    categ = wcapi.get("products/categories?page="+ str(count))
                    category_list = categ.json()
                    for category in category_list:
                        shop.create_woo_category(category, wcapi)
#                 except Exception as e:
#                     if self.env.context.get('log_id'):
#                         log_id = self.env.context.get('log_id')
#                         self.env['log.error'].create({'log_description': str(e) + " While Getting product categories info of %s" % (category_list.get('product_categories')), 'log_id': log_id})
#                     else:
#                         log_id = self.env['woocommerce.log'].create({'all_operations':'import_categories', 'error_lines': [(0, 0, {'log_description': str(e) + " While Getting product categories info of %s" % (category_list.get('product_categories'))})]})
#                         self = self.with_context(log_id=log_id.id)
            except Exception as e:
                if self.env.context.get('log_id'):
                    log_id = self.env.context.get('log_id')
                    self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
                else:
                    log_id = self.env['woocommerce.log'].create({'all_operations':'import_categories', 'error_lines': [(0, 0, {'log_description': str(e)})]})
                    self = self.with_context(log_id=log_id.id)
        return True
    
    
    @api.one
    def create_woocom_product(self, product, wcapi):
        # print ("CEATE PRODUCTTTTTTTTTTTT",product)

        prod_temp_obj = self.env['product.template']
        product_obj = self.env['product.product']
        att_val_obj = self.env['product.attribute.value']
        att_obj = self.env['product.attribute']
        category_obj = self.env['woocom.category']
        tag_obj = self.env['product.tags']
        product_att_line_obj = self.env['product.attribute.line']
        # print ("product.get('nameeeeeeeeeeeeeeeeeeeee')",product.get('name'))
        prd_tmp_vals = {
            'name': product.get('name'),
            'type': 'product',
            'list_price': product.get('sale_price') and float(product.get('sale_price')) or 0.00,
            'default_code': product.get('sku'),
            'description': product.get('short_description'),
            'woocom_regular_price': product.get('regular_price') and float(product.get('regular_price')) or 0.00,
            'woocom_id': product.get('id'),
            'woocom_price' : product.get('price') and float(product.get('price')) or 0.00,
            'product_lngth': product.get('dimensions').get('length'),
            'product_width': product.get('dimensions').get('width'),
            'product_hght': product.get('dimensions').get('height'),
            'product_wght': product.get('dimensions').get('weight'),
        }

        tags = []
        if product.get('tags'):
            for tag in product.get('tags'):
                tag_ids = tag_obj.search([('tag_id', '=', tag.get('id'))])
                if tag_ids:
                    tags.append(tag_ids[0].id)
                else:
                    tag_vals={
                                'name' :tag.get('name') ,
                                'slud_code' : tag.get('slug') ,
                                'description':tag.get('description') ,
                                'tag_id' : tag.get('id') ,
                            }
                    tag_record = tag_obj.create(tag_vals)

                    if tag_record:
                        tags.append(tag_record.id)

            if tags:
                prd_tmp_vals.update({'tag_ids': [(6,0,tags)]})


        if product.get('categories'):
            categ = product.get('categories')
            if isinstance(product.get('categories'), dict):
                categ = [categ]
            cat = product.get('categories')[len(product.get('categories'))- 1]
            cat_ids = category_obj.search([('woocom_id', '=', cat.get('id'))])
            if cat_ids:
                categ_id = cat_ids[0]
                logger.info('product categ id ===> %s', categ_id.name)
                prd_tmp_vals.update({'woo_categ': categ_id.id})
            else:
                self.importWooCategory()
                cat_ids = category_obj.search([('woocom_id', '=', cat.get('id'))])
                if cat_ids:
                    prd_tmp_vals.update({'woo_categ': cat_ids[0].id})
        img_ids = []
        images_list = product.get('images')
        count = 1


        if images_list:

            for imgs in images_list:
                loc = imgs.get('src').split('/')
                image_name = loc[len(loc) - 1]
                img_vals = {
                     'name': image_name,
                     'link': True ,
                     'url':imgs.get('src'),
                     'woocom_img_id' : imgs.get('id')
                } 
                if count == 1:
                    (filename, header) = urllib.request.urlretrieve(imgs.get('src'))
                    f = open(filename, 'rb')
                    img = base64.encodestring(f.read())
                    prd_tmp_vals.update({'image':img})
                    f.close()
                img_ids.append((0, 0, img_vals))
            prd_tmp_vals.update({'woocom_product_img_ids':img_ids})
              



#    attributes line
        at_lines = []  
        
        for attrdict in product.get('attributes'):
            attrs_ids = att_obj.search([('name','=',attrdict.get('name'))])
            att_id = False
            if attrs_ids:
                att_id = attrs_ids[0]
                logger.info('product attribute id ===> %s', att_id.name)
            else:
                self.importWoocomAttribute()   
                attrs_ids = att_obj.search([('name','=',attrdict.get('name'))])
                if attrs_ids:
                    att_id = attrs_ids[0]
            if att_id:
                value_ids=[]
                option = []
                if attrdict.get('options'):
                    option = attrdict.get('options')
                elif attrdict.get('option'):
                    option = attrdict.get('option')
                if isinstance(option, dict):
                    option = [option]
                for value in option:
                    v_ids = att_val_obj.search([('attribute_id','=', att_id.id),('name','=',value.lower())])
                    if v_ids:
                        value_ids.append(v_ids[0].id)
                if value_ids:
                    at_lines.append((0, 0, {
                        'attribute_id': att_id.id,
                        'value_ids': [(6, 0, value_ids)],
                    }))
        if at_lines:
            prd_tmp_vals.update({'attribute_line_ids':at_lines})
        temp_ids = prod_temp_obj.search([('woocom_id', '=', product.get('id'))])
        if temp_ids:
            temp_id = temp_ids[0]
            logger.info('product template id ===> %s', temp_id.name)
            new_lines = []
            if at_lines:
                for variant_data in at_lines:
                    p_at_ids = product_att_line_obj.search([('attribute_id', '=', variant_data[2].get('attribute_id')), ('product_tmpl_id','=', temp_id.id)])
                    if p_at_ids:
                        v_data = [v.id for v in p_at_ids[0].value_ids]
                        new_vals = []
                        for vd in variant_data[2].get('value_ids')[0][2]:
                            if vd not in v_data:
                                new_vals.append(vd)
                        if new_vals:
                            new_lines.append((1, p_at_ids[0].id, {'attribute_id': variant_data[2].get('attribute_id'), 'value_ids': [(4,new_vals)]}))
                    else:
                        variant_data[2].update({'product_tmpl_id': temp_id.id})
                        product_att_line_obj.create(variant_data[2])
                        new_lines.append((0, 0, {'attribute_id': variant_data[2].get('attribute_id'), 'value_ids': variant_data[2].get('value_ids')[0][2]}))
#                 prd_tmp_vals.pop('attribute_line_ids')
            F = prd_tmp_vals.copy()
#             F.pop('image_medium')
            prd_tmp_vals.update({'attribute_line_ids': new_lines})
            # print ("VALSSSSSSSSPRODDD4444444444444444444DDDd",prd_tmp_vals)
            
            temp_id = temp_id.write(prd_tmp_vals)
        else:
            # print ("VALSSSSSSSSPRODDDDDDd",prd_tmp_vals)
           
            temp_ids = prod_temp_obj.create(prd_tmp_vals)
        if product.get('variations'):
            for variation in product.get('variations'):
                try:
                    url = "products/" + str(product.get('id')) +"/variations/" + str(variation)
                    vari = wcapi.get(url)
                    if not vari.status_code:
                        raise UserError(_("Enter Valid url"))
                    vari_data = vari.json()
                    op_ids = []
                    for var in vari_data.get('attributes'):
                        v_ids = att_val_obj.search([('name','=',var.get('option').lower())])
                        if v_ids:
                            op_ids.append(v_ids[0].id)
                    if op_ids:
                        product_ids = product_obj.search( 
                            [('product_tmpl_id.woocom_id', '=', product.get('id'))]) 
                        prod_id_var = False 
                        if product_ids: 
                            for product_data in product_ids: 
                                prod_val_ids = product_data.attribute_value_ids.ids 
                                prod_val_ids.sort() 
                                get_val_ids = op_ids 
                                get_val_ids.sort() 
                                if get_val_ids == prod_val_ids: 
                                    prod_id_var = product_data 
                                    break
                        if prod_id_var:
                            vari_vals={
                                'default_code' : vari_data.get('sku'),
                                'product_lngth': vari_data.get('dimensions').get('length'),
                                'product_width': vari_data.get('dimensions').get('width'),
                                'product_hght': vari_data.get('dimensions').get('height'),
                                'product_wght': vari_data.get('dimensions').get('weight'),
                                'woocom_variant_id' : vari_data.get('id'),
                                'list_price': vari_data.get('sale_price') and float(vari_data.get('sale_price')) or 0.00,
                                'woocom_regular_price': vari_data.get('regular_price') and float(vari_data.get('regular_price')) or 0.00,
                                'woocom_price' : vari_data.get('price'),
                                'description': vari_data.get('short_description'),
                            }
                            prod_id_var.write(vari_vals)
                            # print ("vari_valssssssss",vari_vals)
                except:
                    pass
#                 return temp_id
#     
    @api.multi
    def importWoocomProduct(self):
        # print ("IMPORTTTTPRODUCTTTTTTTT",self)

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            count = 1
            prod = wcapi.get("products?page="+ str(count))
            if not prod.status_code:
                raise UserError(_("Enter Valid url"))
            product_list = prod.json()
            for product in product_list:
                shop.create_woocom_product(product, wcapi)
            while len(product_list) > 0:
                count += 1
                prod = wcapi.get("products?page="+ str(count))
                product_list = prod.json()
                for product in product_list:
                    shop.create_woocom_product(product, wcapi)
        return True
    
         
    @api.one
    def create_woo_inventory(self, loc_id , qty , product):
        # print ("create_woo_inventoryyyyyy",qty, product)
        
        inv_wiz = self.env['stock.change.product.qty']
        if qty > 0:
            inv_wizard = inv_wiz.create({
                'location_id' : loc_id,
                'new_quantity' : qty,
                'product_id' : product.id,
                })
            # print ("inv_wizardddddd",inv_wizard)
            inv_wizard.change_product_qty()
        return True


    @api.multi
    def CreateWoocomInventory(self, product_list, wcapi):
        # print ("CreateWoocomInventoryyyyyyyyyyyy")

        inventory_list = []
    
        for prod_dict in product_list:
            if isinstance(prod_dict, dict):
                # print ("prod_dictttttttttttttttttttt")
                product_vrt = prod_dict.get('variations', [])
                if product_vrt:
                    # print ("iiiiiffffffffproduct_vrt")

                    for variant in product_vrt:
                        prod_url = 'products/' + str(prod_dict.get('id')) + "/variations/" + str(variant)
                        products_data = wcapi.get(prod_url)
                        product_dict = products_data.json()
                        if products_data.status_code != 200:
                            raise UserError(_("Enter Valid url"))
                        
                        prod_ids = self.env['product.product'].search([('woocom_variant_id', '=', variant)])
                        # print ("prodidssssss1111111111",prod_ids,prod_ids.name)

                        if prod_ids:
                            p_id = prod_ids[0]
                            # print ("iiiiffffffprodidsssss",p_id)
                            logger.info('product invent id ===> %s', p_id.name)
                        else:
                            self.create_woocom_product(product_dict, wcapi)
                            prod_ids = self.env['product.product'].search([('woocom_variant_id', '=', variant.get('id'))])
                            # print ("elseeeeprod_idsssssss222222222",prod_ids,prod_ids.name) 
                            if prod_ids:
                                p_id = prod_ids[0]
                                # print ("iiiiffffffprodidsssss22222222",p_id)
                        if p_id:
                            # print ("PIDDDDDDDDDDDD",p_id)
                            # print ("product_dict.get('stock_quantity11111')",product_dict.get('stock_quantity'))

                            if product_dict.get('stock_quantity'):
                                self.create_woo_inventory(self.warehouse_id.lot_stock_id.id, product_dict.get('stock_quantity'), p_id)
                            else:
                                # print ("elseeeeeeeeeee*******")
                                continue
                else:
                    # print ("======ELSEEEEEEEE=========")
                    pro_ids = self.env['product.product'].search([('product_tmpl_id.woocom_id', '=', prod_dict.get('id'))])
                    # print ("pro_idsELSEEEEEEEEEE1111111111111",pro_ids,pro_ids.name)

                    if pro_ids:
                        p_id = pro_ids[0]
                        # print ("ELSEEEEEEEEpidddddddddddd",p_id)
                    else:
                        product_url = 'products/' + str(prod_dict.get('id'))
                        products_data = wcapi.get(product_url)
                        if products_data.status_code != 200:
                            raise UserError(_("Enter Valid url"))

                        product_dict = products_data.json()
                        self.create_woocom_product(product_dict.get('product'), wcapi)
                        pro_ids = self.env['product.product'].search([('product_tmpl_id.woocom_id', '=', prod_dict.get('id'))])
                        # print ("pro_idsEELSEEEEEEEEE222222222222",pro_ids,pro_ids.name)

                        if pro_ids:
                            p_id = pro_ids[0]
                            # print ("pro_idsiiiiidddddddddELSEEEEEEEEEiffffff",pro_ids)

                    if p_id:
                        # print ("=======pro_idddd",p_id)
                        # print ("=======stock_quantity",prod_dict.get('stock_quantity'))

                        if prod_dict.get('stock_quantity'):
                            self.create_woo_inventory(self.warehouse_id.lot_stock_id.id, prod_dict.get('stock_quantity'), p_id)
                        else:
                            continue
        
    @api.multi
    def importWoocomInventory(self):
        # print ("importWoocomInventoryyyyyyyyyy")

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            # print ("WCPIIIIIII22222",wcapi)
            count = 1
            products = wcapi.get("products")
            # print ("productsssssssssssssss",products) 

            if products.status_code != 200:
                raise UserError(_("Enter Valid url"))
            
            product_list = products.json()
            while len(product_list) > 0:
                # print ("LENNNNNNNNNNNNN------",len(product_list))

                shop.CreateWoocomInventory(product_list,wcapi)
                # print ("count1111111111------",count)

                count += 1
                # print ("count2222222222------",count)

                url = "products?page="+ str(count)
                # print ("urlllllllllllllll----",url)

                products = wcapi.get("products?page="+ str(count))
                # print ("PRODUCTSSSSSSSSS-----",products)

                product_list = products.json()
                # print ("product_listtttt-----",product_list)
        return True



    @api.one
    def create_woo_customer(self, customer_detail, wcapi):
        # print ("create_woo_customereeeeeeee=======>>>")

        res_partner_obj = self.env['res.partner']
        country_obj = self.env['res.country']
        state_obj = self.env['res.country.state']
        
        if customer_detail == None:
            cust_id = res_partner_obj.search([('name','=','Guest Customer')])

        if customer_detail != None:

            country_ids  = False
            bcountry = customer_detail.get('billing').get('country')
            if bcountry != 'False':
                country_ids = country_obj.search([('code', '=', bcountry)])
                if not country_ids:
                    country_id = country_obj.create({'name':bcountry, 'code':bcountry}).id
                else:
                    country_id = country_ids.id
                    logger.info('country id ===> %s', country_id)
            else:
                country_id = False
                

            bstate = customer_detail.get('billing').get('state')
            if bstate != 'False':
                state_ids = state_obj.search([('country_id', '=', country_id),('code', '=', bstate)])
                if not state_ids:
                    state_id = state_obj.create({'name':bstate, 'code':bstate, 'country_id': country_id}).id
                else:
                    state_id = state_ids.id
                    logger.info('state id ===> %s', state_id)
            else:
                state_id = False

    #         if customer_detail.get('first_name') or customer_detail.get('last_name'):
            vals = {
                'woocom_id': customer_detail.get('id'),
                'name': (customer_detail.get('first_name') or '' + customer_detail.get('last_name') or '') or customer_detail.get('username'),
                'customer' : True,
                'supplier' : False,
                'street': customer_detail.get('billing') and customer_detail.get('billing').get('address_1') or '',
                'street2' : customer_detail.get('billing').get('address_2'),
                'city': customer_detail.get('billing').get('city'),
                'zip': customer_detail.get('billing').get('postcode'),
                'phone': customer_detail.get('billing').get('phone'),
                'state_id' :state_id,
                'country_id': country_id,
                'email': customer_detail.get('email'),
                'website': customer_detail.get('website'),
                }
            
            ####
            add_lines = []  
            
            scountry = customer_detail.get('shipping').get('country')
            if scountry != 'False':
                scountry_ids = country_obj.search([('code', '=', scountry)])
                if not scountry_ids:
                    scountry_id = country_obj.create({'name':scountry, 'code':scountry}).id
                else:
                    scountry_id = scountry_ids[0].id
                    logger.info('scountry id ===> %s', scountry_id)
            else:
                scountry_id = False
                
            sstate = customer_detail.get('shipping').get('state')
            if sstate != 'False':
                sstate_ids = state_obj.search([('code', '=', sstate)])
                if not sstate_ids:
                    sstate_id = state_obj.create({'name':sstate, 'code':sstate, 'country_id': scountry_id}).id
                else:
                    sstate_id = sstate_ids[0].id
                    logger.info('sstate id ===> %s', sstate_id)
            else:
                sstate_id = False
            
            if customer_detail.get('shipping').get('city'):
                add_lines.append((0, 0, {
                    'woocom_id': customer_detail.get('id'),
                    'name': customer_detail.get('shipping').get('first_name') or ' ' + customer_detail.get('shipping').get('last_name') or ' ',
                    'street': customer_detail.get('shipping').get('address_1'),
                    'street2' : customer_detail.get('shipping').get('address_2'),
                    'city': customer_detail.get('shipping').get('city'),
                    'zip': customer_detail.get('shipping').get('postcode'),
                    'phone': customer_detail.get('shipping').get('phone'),
                    'country_id' : scountry_id,
                    'state_id' : sstate_id,
                    'type': 'delivery',
                    }))

            vals.update({'child_ids' : add_lines})
            customer_ids = res_partner_obj.search([('woocom_id', '=', customer_detail.get('id')),('email','=',customer_detail.get('email'))])
            # print ("customer_ids1111111111",customer_ids) 
            if not customer_ids:
                cust_id = res_partner_obj.create(vals)
                # print ("customer_ids222222",cust_id) 
            else:
                cust_id = customer_ids[0]
                # print ("customer_ids3333333",cust_id) 
                logger.info('customer id ===> %s', cust_id.name)
                vals.pop('child_ids')
                cust_id.write(vals)
            if cust_id:
                # print ("customer_ids444444444",cust_id) 
                self.env.cr.execute("select cust_id from customer_shop_rel where cust_id = %s and shop_id = %s" % (cust_id.id, self.id))
                cust_data = self.env.cr.fetchone()
        return cust_id

    
    @api.multi
    def importWoocomCustomer(self):
        # print ("importWoocomCustomerrrrrrrrrr=======>>>")
        
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            count = 1
            customers = wcapi.get("customers?page="+ str(count))
            if customers.status_code != 200:
                raise UserError(_("Enter Valid url"))
            customer_list = customers.json()
            for custm in customer_list:
                shop.create_woo_customer(custm, wcapi)
            while len(customer_list) > 0:
                count += 1
                custm = wcapi.get("customers?page="+ str(count))
                customer_list = custm.json()
                for custm in customer_list:
                    shop.create_woo_customer(custm, wcapi)
        return True
    
    @api.one
    def create_woo_carrier(self, carrier, wcapi):
        # print ("create_woo_carrierrrrrrrrrr")

        carrier_obj = self.env['delivery.carrier']
        partner_obj = self.env['res.partner']
        product_obj = self.env['product.product']
        carrier_list_ids = []

        partner_ids = partner_obj.search([('name', '=', carrier.get('title'))])
        if partner_ids:
            partner_id = partner_ids[0]
        else:
            partner_id = partner_obj.create({'name': carrier.get('title')})
        prod_ids = product_obj.search([('name', '=', carrier.get('title'))])
        if prod_ids:
            prod_ids = prod_ids[0]
        else:
            prod_ids = product_obj.create({'name': carrier.get('title')})
        carr_vals = {
            'name': carrier.get('title'),
            'partner_id': partner_id.id,
            'woocom_id': carrier.get('id'),
            'product_id': prod_ids.id
        }
        car_ids = carrier_obj.search([('woocom_id', '=',carrier.get('id'))])
        if not car_ids:
            carrier_id = carrier_obj.create(carr_vals)
        else:
            carrier_id = car_ids[0]
            logger.info('carrier id ===> %s', carrier_id.name)
            carrier_id.write(carr_vals)
        return carrier_id

    @api.multi
    def importWoocomCarrier(self):
        # print ("IMPORTCARRRRRRRR")
        for shop in self:
            # print ("Shoppppppppppppppp",shop)

            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            # print ("wcapiiiiiiiiiiiiii",wcapi)

            carriers = wcapi.get("shipping_methods")
            # print ("Shoppppppppppppppp",shop)

            if carriers.status_code != 200:
                raise UserError(_("Enter Valid url"))

            carriers_list = carriers.json()
            # print ("carriers_listttttttttttt",carriers_list)

            for carrier in carriers_list:
                # print ("carrierrrrrrrrrrrr",carrier)

                shop.create_woo_carrier(carrier, wcapi)
        return True



    @api.one
    def create_woo_payment_method(self, payment, wcapi):
        payment_obj = self.env['payment.gatway']
        pay_ids = payment_obj.search([('woocom_id', '=',payment.get('id'))])
        pay_vals = {
            'title': payment.get('title'),
            'woocom_id': payment.get('id'),
            'descrp': payment.get('description'),
            }
        pay_ids.write(pay_vals)
        if not pay_ids:
            payment_id = payment_obj.create(pay_vals)
            payment_id.write(pay_vals)


    @api.multi
    def importWooPaymentMethod(self):
        
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            payment_methods = wcapi.get("payment_gateways")
            if payment_methods.status_code != 200:
                raise UserError(_("Enter Valid url"))
            payments_list = payment_methods.json()
            for payment in payments_list:
                shop.create_woo_payment_method(payment, wcapi)
        return True
    
    
    def woocomManageOrderWorkflow(self, saleorderid, order_detail, status):
        # print("WORKFLOWWWWWWWWWWW",saleorderid,status)

        invoice_obj = self.env['account.invoice']
        invoice_refund_obj = self.env['account.invoice.refund']
        return_obj = self.env['stock.return.picking']
        return_line_obj = self.env['stock.return.picking.line']
        
        if order_detail.get('status') == 'cancelled':
            if saleorderid.state in ['draft']:
                saleorderid.action_cancel()

            if saleorderid.state in ['progress', 'done', 'manual']:
                invoice_ids = saleorderid.invoice_ids
                for invoice in invoice_ids:
                    refund_ids = invoice_obj.search([('origin', '=', invoice.number)])
                    # print  "==refund_ids==>",refund_ids
                    if not refund_ids:
                        if invoice.state == 'paid':
                            refund_invoice_id = invoice_refund_obj.create(dict(
                                description='Refund To %s' % (invoice.partner_id.name),
                                date=datetime.date.today(),
                                filter_refund='refund'
                            ))
                            refund_invoice_id.invoice_refund()
                            saleorderid.write({'is_refund': True})
                        else:
                            invoice.action_cancel()

                for picking in saleorderid.picking_ids:
                    if picking.state not in ('done'):
                        picking.action_cancel()
                    else:
                        ctx = self._context.copy()
                        ctx.update({'active_id': picking.id})
                        res = return_obj.with_context(ctx).default_get(['product_return_moves', 'move_dest_exists'])
                        res.update({'invoice_state': '2binvoiced'})
                        return_id = return_obj.with_context(ctx).create({'invoice_state': 'none'})
                        for record in res['product_return_moves']:
                            record.update({'wizard_id': return_id.id})
                            return_line_obj.with_context(ctx).create(record)

                        pick_id_return, type = return_id.with_context(ctx)._create_returns()
                        pick_id_return.force_assign()
                        pick_id_return.action_done()
            saleorderid.action_cancel()
            return True


       # ==== My code from here to make "Refund" sale orders to confirm and its invocie  and delivery created====#

        if not self.workflow_id:
            if order_detail.get('status') == 'refunded':
                if saleorderid.state == 'draft':
                    saleorderid.action_confirm()

                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid.action_invoice_create()
                    invoice_ids = invoice_obj.browse(invoice_ids)
                    # invoice_ids.write({'is_woocom': True})

                for invoice_id in saleorderid.invoice_ids:
                    if invoice_id.state == 'draft':
                        # print "invoice state is draft"
                        invoice_id.action_invoice_open()

                    if invoice_id.state not in ['paid'] and invoice_id.invoice_line_ids:
                        invoice_id.pay_and_reconcile(self.sale_journal or self.env['account.journal'].search(
                                [('type', '=', 'bank')], limit=1), invoice_id.amount_total)

       #  =========My code till here    ===========  #  


        if self.workflow_id:

            if self.workflow_id.validate_order:
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()

        # if complete shipment is activated in workflow
            if self.workflow_id.complete_shipment:

                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()

                for picking_id in saleorderid.picking_ids:
                    # If still in draft => confirm and assign
                    if picking_id.state == 'draft':
                        picking_id.action_confirm()
                        picking_id.action_assign()
    
                    if picking_id.state == 'confirmed':
                        picking_id.force_assign()
                        picking_id.action_assign()
                        # picking_id.button_validate()
                    picking_id.do_transfer()

                    
    
            # if create_invoice is activated in workflow
            if self.workflow_id.create_invoice:
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()
                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid.action_invoice_create()
                    invoice_ids = invoice_obj.browse(invoice_ids)
                    invoice_ids.write({'is_woocom': True})
    
    
            # if validate_invoice is activated in workflow
            if self.workflow_id.validate_invoice:
                if saleorderid.state == 'draft':
                    saleorderid.action_confirm()
    
                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid.action_invoice_create()
                    invoice_ids = invoice_obj.browse(invoice_ids)
                    invoice_ids.write({'is_woocom': True})
    
                for invoice_id in saleorderid.invoice_ids:
                    if invoice_id.state == 'draft':
                        invoice_id.action_invoice_open()
    
            # if register_payment is activated in workflow
            if self.workflow_id.register_payment:
                if saleorderid.state == 'draft':
                    saleorderid.action_confirm()
                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid.action_invoice_create()
                    invoice_ids = invoice_obj.browse(invoice_ids)
                    invoice_ids.write({'is_woocom': True})
    
                for invoice_id in saleorderid.invoice_ids:
                    if invoice_id.state == 'draft':
                        # print "invoice state is draft"
                        invoice_id.action_invoice_open()
                    if invoice_id.state not in ['paid'] and invoice_id.invoice_line_ids:
                        invoice_id.pay_and_reconcile(
                            self.workflow_id and self.sale_journal or self.env['account.journal'].search(
                                [('type', '=', 'bank')], limit=1), invoice_id.amount_total)
            return True
                
        else:
            if order_detail.get('status') == 'on-hold':
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()

                for picking_id in saleorderid.picking_ids:
# If still in draft => confirm and assign
                    if picking_id.state == 'draft':
                        picking_id.action_confirm()
                        picking_id.action_assign()
    
                    if picking_id.state == 'confirmed':
                        picking_id.force_assign()
                    picking_id.do_transfer()
                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid.action_invoice_create()
                    
                        
            elif order_detail.get('status') == 'failed':
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()

                for picking_id in saleorderid.picking_ids:
# If still in draft => confirm and assign
                    if picking_id.state == 'draft':
                        picking_id.action_confirm()
                        picking_id.action_assign()
    
                    if picking_id.state == 'confirmed':
                        picking_id.force_assign()
                    picking_id.do_transfer()
                                            
            elif order_detail.get('status') == 'processing': 
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()
               
                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid.action_invoice_create()
    
                for invoice_id in saleorderid.invoice_ids:
                    if invoice_id.state == 'draft':
                        invoice_id.action_invoice_open()
                    if invoice_id.state not in ['paid'] and invoice_id.invoice_line_ids:
                            invoice_id.pay_and_reconcile(
                                self.sale_journal or self.env['account.journal'].search(
                                    [('type', '=', 'bank')], limit=1), invoice_id.amount_total)
        
            elif order_detail.get('status') == 'pending':
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()
               
                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid.action_invoice_create()
                
                        
            elif order_detail.get('status') == 'completed':
                if saleorderid.state in ['draft']:
                    saleorderid.action_confirm()

                for picking_id in saleorderid.picking_ids:
                    if picking_id.state == 'draft':
                        picking_id.action_confirm()
                        picking_id.action_assign()
    
                    if picking_id.state == 'confirmed':
                        picking_id.force_assign()
                    picking_id.do_transfer()
                    
                if not saleorderid.invoice_ids:
                    invoice_ids = saleorderid.action_invoice_create()
    
                for invoice_id in saleorderid.invoice_ids:
                    if invoice_id.state == 'draft':
                        invoice_id.action_invoice_open()
                    if invoice_id.state not in ['paid'] and invoice_id.invoice_line_ids:
                            invoice_id.pay_and_reconcile(
                                self.sale_journal or self.env['account.journal'].search(
                                    [('type', '=', 'bank')], limit=1), invoice_id.amount_total)
                
                saleorderid.action_done()


    @api.one
    def woocomManageCoupon(self, orderid, coupon_detail, wcapi):
        # print ("woocomManageCouponnnnnnnnn",coupon_detail)

        sale_order_line_obj = self.env['sale.order.line']
        coupon_obj = self.env['woocom.coupons']
        product_obj = self.env['product.product']

        for coupon_value in coupon_detail:
            # print ("FORRRRcoupon_valueeeeee",coupon_value)
            c_id = False
            # c_ids = coupon_obj.search([('coupon_id','=', coupon_value.get('id'))])

            c_ids = coupon_obj.search(['|',('coupon_id','=', coupon_value.get('id')),('coupon_code','=', coupon_value.get('code'))])
            # print("c_idsssssssss1111111111",c_ids)

            if c_ids:
                c_id = c_ids[0]
                # print("IIIIIIFFFFFFFc_idsssssss",c_ids)

            else:
                url = 'coupons/' + str(coupon_value.get('id'))
                # print("URLLLLLLLLLL",url)

                coupons_data = wcapi.get(url)
                # print("coupons_data11111111111",coupons_data)

                coupons_data = coupons_data.json()
                # print("coupons_data222222222222",coupons_data)

                c_id = coupon_obj.create({
                          'coupon_id': coupon_value.get('id'), 
                          'coupon_code': coupon_value.get('code'),
                          # 'description': coupon_value.get('description'),
                          })
                # print ("C_IDVALSSSSSSSSSSSS",c_id,coupon_value.get('id'),coupon_value.get('code'),coupon_value.get('description')) 

                self._cr.commit()

            p_id = False
            p_ids = product_obj.search([('name','=','Coupon'),('type','=','service')])
            # print ("P_IDSSSSSSSSSSSS",p_id) 

            if p_ids:
                p_id = p_ids[0]
                # print ("iiiffffffffP_IDSSSSSSSSSSS",p_id) 
            else:
                p_id = product_obj.create({
                    'name': 'Coupon',
                    'type': 'service'
                    })
                # print ("elseeeeeeeeP_IDSSSSSSSSSS",p_id) 
                self._cr.commit()

            line = {
                'product_id' : p_id and p_id.id,
                'price_unit': -float(coupon_value.get('discount')),

                # 'name': c_id.description,
                
                'name': p_id.name,
                'product_uom_qty': 1,
                'order_id': orderid.id,
                'tax_id': False,
                'woocom_id': coupon_value.get('id'),
                'product_uom': p_id and p_id.uom_id.id 
            }
            # print ("LINEEEEEEEEE",line) 

            line_ids = sale_order_line_obj.search([('order_id', '=', orderid.id), ('woocom_id', '=', coupon_value.get('id'))])
            if line_ids:
                line_id = line_ids[0]
                # print ("line_idsssssssssss",line_ids) 
                # logger.info('order line id ===> %s', line_id.name)
                # line_id.write(line)
            else:
                # print "====elseeeeeeline===>",line
                line_id = sale_order_line_obj.create(line)
        return True


           
    @api.one
    def woocomManageOrderLines(self, orderid, order_detail, wcapi):

        sale_order_line_obj = self.env['sale.order.line']
        prod_attr_val_obj = self.env['product.attribute.value']
        prod_templ_obj = self.env['product.template']
        product_obj = self.env['product.product']
        lines = []
        for child in order_detail:
            p_id = False
            p_ids = product_obj.search([('default_code', '=', child.get('sku'))])
            if p_ids:
                p_id = p_ids[0]
                logger.info('order line product id ===> %s', p_id.name)
            else:
                self.importWoocomProduct()
                p_ids = product_obj.search([('default_code', '=', child.get('sku'))])
                if p_ids:
                    p_id = p_ids[0]
            if not p_id:
                p_id = product_obj.create({'default_code': child.get('sku'), 'name': child.get('name') or child.get('sku')})
#                 'name': child.get('sku'),
#             if child.get('name') or child.get('sku')
            
            line = {
                'product_id' : p_id and p_id.id,
                'price_unit': float(child.get('price')),
                'name': child.get('name') or child.get('sku'),
                'product_uom_qty': float(child.get('quantity')),
                'order_id': orderid.id,
                'tax_id': False,
                'woocom_id': child.get('id'),
                'product_uom': p_id and p_id.uom_id.id 
            }
            
            tax_id = []
            # print ("child.get('subtotal_tax')))))))))",child.get('subtotal_tax')) 
            if child.get('subtotal_tax') != None:
                tax_id = self.getTaxesAccountID(child,orderid,line.get('price_unit'))
                # print("tax_idddddddddddddddddddddd",tax_id)

                if tax_id[0]:
                    line['tax_id'] = [(6, 0, tax_id)]
                    # print ("iiiiifffffffline['tax_id']ddddddddddd",line['tax_id'])
                else:
                    line['tax_id'] =[]
                    # print ("elseeeeeeeeeline['tax_id']ddddddddddd",line['tax_id'])

            line_ids = sale_order_line_obj.search([('order_id', '=', orderid.id), ('woocom_id', '=', child.get('id'))])
            # print ("Lineidddddddsssssss",line_ids)

            if line_ids:
                line_id = line_ids[0]
                # print ("iiiddddddLineiddddddd",line_id)
                logger.info('order line id ===> %s', line_id.name)
                line_id.write(line)
                # print ("LINEEEEEEE",line_id)
            else:
                line_id = sale_order_line_obj.create(line)
                # print ("elseeeeeLineiddddddd",line_id)

        return True

    @api.one
    def getTaxesAccountID(self,each_result,order_id,unit_price):
        # print ("getTaxesAccountIDDDDDDDD")

        accounttax_obj = self.env['account.tax']
        accounttax_id = False
        shop_data = self.browse(self._ids)
#         if hasattr(each_result ,'tax_percent') and float(each_result['tax_percent']) > 0.0:
        # amount = float(each_result['ItemTax'])/int(each_result.get('QuantityOrdered'))
        # print("amountamount",amount)

        acctax_ids = accounttax_obj.search([('wocomm_country_id','=',order_id.partner_id.country_id.id),('type_tax_use', '=', 'sale'),('wocomm_state_id', '=', order_id.partner_id.state_id.id)])
        # print("acctax_idsssssssssssssssssss",acctax_ids)

        if acctax_ids:
            accounttax_id = acctax_ids[0].id
            # print ("iiffffaccounttax_id111111111111",accounttax_id)
#             accounttax_id = accounttax_obj.create({'name':name,'amount':amount,'type_tax_use':'sale','amount_type':'fixed'})
#             accounttax_id = accounttax_id.id
        else:
            accounttax_id = False
            # print ("elseeeeeaccounttax_id111111111111",accounttax_id)
        return accounttax_id


          
    @api.one
    def create_woo_order(self, order_detail, wcapi):
        # print ("create_woo_orderrrrwwwwwwwwwwwww",order_detail)

        sale_order_obj = self.env['sale.order']
        res_partner_obj = self.env['res.partner']
        carrier_obj = self.env['delivery.carrier']
        status_obj = self.env['woocom.order.status']
        payment_obj = self.env['payment.gatway']
        woocom_conector = self.env['woocommerce.connector.wizard']
        
        if not order_detail.get('line_items'):
            return False
        custm_id = order_detail.get('customer_id')
        # print("===custm_idcustm_idcustm_id======>",custm_id)
        if not custm_id:
            # print("===custm_idcustm_idcustm_id======>",custm_id)
            partner_id = self[0].partner_id.id
        else:
            # print ("==ELSEEEEORDERRRRRRRRRR==")
            part_ids = res_partner_obj.search([('woocom_id', '=', custm_id)])
            # print ("part_idssssssssss111111111111111",part_ids)

            if part_ids:
                # print ("iffffff_part_ids111111111111111",part_ids)
                partner_id = part_ids[0].id
                logger.info('partner id ===> %s', partner_id)
                # print ("part_idsss0000000000000",part_ids)

                # ship_partner_id=False
                # bill_partner_id=False
                # for res1 in part_ids[0].child_ids:
                #     print ("resssssssssssss",res1,res1.type)
                #     if res1.type == 'delivery':
                #         ship_partner_id=res1.id
                #     elif res1.type == 'invoice':
                #         bill_partner_id=res1.id
                # print ("BILLLLLLLL//////Shipppppppppp",bill_partner_id,ship_partner_id)
            else:
                # print ("==esleeeeeeee==")
                url = 'customers/' + str(custm_id)
                # print ("CUSTOMER_urlllllllll",url)
                customer_data = wcapi.get(url)
                customer_data = customer_data.json()
                # partner_id,ship_partner_id, bill_partner_id = self.create_woo_customer(customer_data, wcapi)
                partner_id = self.create_woo_customer(customer_data, wcapi)[0].id
                # partner_id = partner_id.id
                # print ("PARTNERRRRRRRRRRRR",partner_id)

        paym_ids = payment_obj.search([('woocom_id','=',order_detail.get('payment_method'))])
        if paym_ids:
            pay_id = paym_ids[0].id
            logger.info('payment id ===> %s', pay_id)
        else:
            pay_id = payment_obj.search([('woocom_id','=',order_detail.get('payment_method'))])
            pay_id = pay_id.id
        car_id = False
        for avalue in order_detail.get('shipping_lines'):
            if avalue.get('method_id') == 'False':
                car_id = False
            else:
                car_ids = carrier_obj.search([('woocom_id','=',avalue.get('method_id'))])
                if car_ids:
                    car_id = car_ids[0].id
                    logger.info('carrier id ===> %s', car_id)
                else:
                    self.importWoocomCarrier()
#                     car_url = 'shipping_methods'+str(avalue.get('method_id'))

                    car_ids = carrier_obj.search([('woocom_id','=', avalue.get('method_id').replace(':2',""))])
                    if car_ids:
                        car_id = car_ids[0].id
                    else:
                        car_id = False
                    # print ("caridddddddddddddd",car_id)
                    # carr_data = wcapi.get(car_id)
                    # print ("cardataaaaaaaaaaa",carr_data)
                    # carrier_data = carr_data.json()
                    # print ("CARDATA2222222222",carrier_data)
                    # carrier_id = self.create_woo_carrier(carrier_data.get('customer'), wcapi)[0].id
#                     car_ids = carrier_obj.search([('woocom_id','=',avalue.get('method_id'))])
#                     if car_ids:
#                         car_id = car_ids[0].id
#                         logger.info('carrier id ===> %s', car_id)
#                     else:
#                         car_id = False
        # llllllllllllllll
        if order_detail.get('status') == 'draft':
            # print ("order_detail.get('status1111111111')",order_detail.get('status'))

            order_detail.update({'status': 'pending'})
            # print ("order_detail.get('status22222222222')",order_detail.get('status'))

        order_vals = {'partner_id': partner_id,
                      'woocom_id' : order_detail.get('id'),
                      'warehouse_id': self.warehouse_id.id,
                      'name': (self.prefix and self.prefix or '') + str(order_detail.get('id')) + (self.suffix and self.suffix or ''),
                      'pricelist_id': self.pricelist_id.id,
                      'order_status' : order_detail.get('status'),
                      'shop_id': self.id,
                      'carrier_woocommerce': car_id or False,
                      'woocom_payment_mode':pay_id,
                      # 'partner_billing_id': bill_partner_id, 
                      # 'partner_shipping_id': ship_partner_id, 

        }
        # print ("ORDRVALSSSSSSSSSSSSSSSSS",order_vals)


        sale_order_ids = sale_order_obj.search([('woocom_id', '=', order_detail.get('id'))])
        # print ("SALEORDERIDDDDDDDD",sale_order_ids)

        if not sale_order_ids:
            s_id = sale_order_obj.create(order_vals)
            self._cr.commit()
            # print ("sidd11111111111111d",s_id,s_id.name)
            self.woocomManageOrderLines(s_id, order_detail.get('line_items'), wcapi)
            if order_detail.get('coupon_lines', False):
                    # print ("IIIIIIIIINNNNNNNNN111111111111")
                    self.woocomManageCoupon(s_id, order_detail.get('coupon_lines'), wcapi)
            self.woocomManageOrderWorkflow(s_id, order_detail, order_detail.get('status'))
        else:
            if sale_order_ids.state != 'done':
                s_id = sale_order_ids[0]
                # print ("SID22222222222",s_id,s_id.name)

                # logger.info('create order ===> %s', s_id.name)
                s_id.write(order_vals)
                self.woocomManageOrderLines(s_id, order_detail.get('line_items'), wcapi)
                if order_detail.get('coupon_lines', False):
                    # print ("IIIIIIIIINNNNNNNNN111111111111")
                    self.woocomManageCoupon(s_id, order_detail.get('coupon_lines'), wcapi)
                # s_id.delivery_tax_address()
                self.woocomManageOrderWorkflow(s_id, order_detail, order_detail.get('status'))

        
    @api.multi
    def importWoocomOrder(self):
        # print ("importOrderrrrrrrrrrrrrr===========>")
        sale_order_obj = self.env['sale.order']

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            # print ("WCPIIIIIIIIIIIIII",wcapi)
            count = 1
            if self.env.context.get('last_woocommerce_order_import_date'):
                method = "orders?filter[created_at_min]="+ self.env.context.get('last_woocommerce_order_import_date')
                # print ("METHODDDDDDDD1111111111",method)
            elif shop.last_woocommerce_order_import_date:
                today = date.today()- timedelta(days=2)
                method = "orders?filter[created_at_min]="+ str(today)
                # print ("METHODDDDDDDD222222222",method)
            else:
                method = 'orders?page='+ str(count)
                # print ("METHODDDDDDDD3333333333",method)

            orders = wcapi.get(method)
            # print ("WCPIORDERSSSSSSSSSS",orders)

            if orders.status_code != 200:
                raise UserError(_("Enter Valid url"))
            orders_list = orders.json()
            # print("ORDERLISTTTTTTTTTTT",orders_list) 

            for order in orders_list:
                # print("FFFFOOOORRRRRORDERLISTTTTTT",order) 
                if order.get('status') != 'refunded':
                    shop.create_woo_order(order, wcapi)
        
            while len(orders_list) > 0:
                # print("WHILEEEEEEEEEEEEEE",len(orders_list))
                # print("====count111111",count)
                url = "orders?page="+ str(count)
                # print("=====url====>",url)

                order = wcapi.get("orders?page="+ str(count))
                count += 1
                # print ("====count22222222",count)
                orders_list = order.json()
                for order in orders_list:
                    # print ("order--------++++++++",order,order.get('status'),wcapi)
                    if order.get('status') != 'refunded':
                        shop.create_woo_order(order, wcapi)
        return True



    @api.multi
    def importRefundOrder(self):
        # print ("importRefundOrderrrrrrrrrrrrrrrrr===========>",self)
        sale_order_obj = self.env['sale.order']

        for shop in self:
            # print ("SHOPPPPPPPPPPPPPPPPP",shop)

            wcapi = woocom_api.API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            # print ("WCPIIIIIII111111111111111111",wcapi)
            count = 1
            if self.env.context.get('last_woocommerce_refund_order_import_date'):
                method = "orders?filter[created_at_min]="+ self.env.context.get('last_woocommerce_refund_order_import_date')
            elif shop.last_woocommerce_refund_order_import_date:
                today = date.today()- timedelta(days=2)
                method = "orders?filter[created_at_min]="+ str(today)
            else:
                method = 'orders?page='+ str(count)
                # method = 'orders/446'
                # print ("METHODDDDDDDD",method) 
            orders_list = wcapi.get(method)
            # print ("ORDERSSSSSSSSSSSS",orders_list)

            if orders_list.status_code != 200:
                raise UserError(_("Enter Valid url"))
            orders_list = orders_list.json()

            if isinstance(orders_list, dict):
                orders_list = [orders_list]
            while len(orders_list) > 0:
                # print ("WHILEEEEEEEEEEEEEEEEEEE1111111111",len(orders_list))
                # print ("COUNTTTTTTTTTTRRRRRRR11111",count)
                for order in orders_list:
                    # print ("FOOOOORRRRRINNNNNNNRREEEEEFFFFFF222222222",order)

                    if order.get('status') == 'refunded':
                        sale_order_ids = sale_order_obj.search([('woocom_id', '=', order.get('id'))])
                        # print ("FOOOOORRRRRsale_order_idssssssss22222222",sale_order_ids)
                        if not sale_order_ids:
                            # print ("NOTTTTTTTTTTTT",sale_order_ids,shop)
                            sale_order_ids = shop.create_woo_order(order, wcapi)
                            # print ("sale_order_idssssss111111111222222222",sale_order_ids)
                            sale_order_ids = sale_order_obj.search([('woocom_id', '=', order.get('id'))])
                            # print ("sale_order_ids22222222222222.2.2.2.2.2",sale_order_ids)
                            self._cr.commit()
                        if sale_order_ids:
                            # print ("IIIINNNN======sale",sale_order_ids)
                            shop.importWoocomOrderRefund(order,sale_order_ids)
                            self._cr.commit()
                # self._cr.commit()
                count += 1
                orders_list = wcapi.get("orders?page="+ str(count))
                url = "orders?page="+ str(count)
                # print ("URLLLLLLLLLLLLL",url)

                # count += 1
                # print ("COUNTTTTTTTTTTRRRRRRR22222",count)
                orders_list = orders_list.json()
                # print ("----------------------------------------------------",len(orders_list))
        return True



    

    @api.multi
    def importWoocomOrderRefund(self, order_detail, saleorderid):
        # print ("importWoocomOrderRefundddddddddd===========>",order_detail)

        invoice_obj = self.env['account.invoice']
        invoice_refund_obj = self.env['account.invoice.refund']
        return_obj = self.env['stock.return.picking']
        return_line_obj = self.env['stock.return.picking.line']
        sale_order_obj = self.env['sale.order']
        stock_pick_obj = self.env['stock.picking']

        ctx = self.env.context.copy()
        for shop in self:
            wcapi = woocom_api.API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            # print ("WCPIIIIIII22222222222222222",wcapi)
            count = 1

            method = 'orders/' + str(order_detail.get('id')) + '/refunds'
            refund_orders = wcapi.get(method)
            if refund_orders.status_code != 200:
                raise UserError(_("Enter Valid url"))
            refund_list = refund_orders.json()
            for refund_detail in refund_list:
                # print ("refund_detailssssssssssssssssssss",refund_detail)

                if saleorderid.state == 'draft':
                    saleorderid.action_confirm()

                if not saleorderid.invoice_ids:
                    saleorderid.action_confirm()
                    invoice_id = saleorderid.action_invoice_create()

                if saleorderid.state in ['sale', 'done', 'sent']:

                    for invoice in saleorderid.invoice_ids:
                        refund_ids = invoice_obj.search([('origin', '=', invoice.number)])
                        # print ("refund_idsssss11111111111",refund_ids)
                        if refund_ids:
                            refund_ids = invoice_obj.search([('id', '=', refund_ids.refund_invoice_id.id)])
                            # print ("refund_idsssss2222222222",refund_ids)
                        if not refund_ids:
                            refund_ids = invoice_obj.search([('id', '=', invoice.refund_invoice_id.id)])
                            # print ("refund_idsssss333333333333331",refund_ids)

                            date1 = refund_detail.get('date_created')
                            date2 = date1.replace('T'," ")
                            date3 = datetime.strptime(date2,'%Y-%m-%d %H:%M:%S')
                            date4 = date3.strftime('%m/%d/%Y')
                            if not refund_ids:
                                # print  ("==NOT refund_ids==>")
                                if invoice.state == 'paid':
                                # if invoice.state in ['paid', 'draft']:
                                    # print ("PAIDDDDDDDDDDDD",invoice.state)
                                    ctx.update({'active_ids':invoice.id})
                                    refund_vals = {
                                        'description':refund_detail.get('reason'),
                                        'date' : date4,
                                        # 'date_invoice' : datetime.today(),
                                        'filter_refund':'refund',
                                    }
                                    # print ("RefundValssssssssss",refund_vals)
                                    refund_invoice_id = invoice_refund_obj.with_context(ctx).create(refund_vals)
                                    self._cr.commit()

                                    # print ("refund_invoice_iddddddddddddd",refund_invoice_id)

                                    invc = refund_invoice_id.with_context(ctx).invoice_refund()
                                    # print ("invvvvvvvvvvvvv",invc)

                                    a = invc.get('domain')[1][2][0]
                                    # print "1111111111111",a
                                    # b = a[1]
                                    # print "2222222222222",b
                                    # c = b[2]
                                    # print "333333333333",c[0]

                                    refunded_invoice_id = invoice_obj.browse(a)
                                    # print "invoice_refundCCCCCCCCCCC",refunded_invoice_id


                                    if refunded_invoice_id.state == 'draft':
                                        # print "invoice state is draft"
                                        refunded_invoice_id.action_invoice_open()

                                    if refunded_invoice_id.state not in ['paid'] and refunded_invoice_id.invoice_line_ids:

                                        refunded_invoice_id.pay_and_reconcile(
                                            self.workflow_id and self.sale_journal or self.env['account.journal'].search(
                                                [('type', '=', 'bank')], limit=1), refunded_invoice_id.amount_total)
                                    
                                    saleorderid.write({'is_refund': True})
                                # else:
                                     #     invoice.action_cancel()

                    for picking in saleorderid.picking_ids:
                        if picking.picking_type_id.code == "incoming":
                            continue
                        if picking.return_created:
                            continue

                        # global counter
                        # print ("counter***************",counter)

                        # print ("PICINGGGGGGG=====>>>",picking.name,picking.origin)

                        # if not picking.is_original:
                        # print ("IIIIIIIFFFFFFFFFFFFF111111",picking)
                        picking.action_confirm()
                        StockPackObj = self.env['stock.move.line']
                        for move in picking.move_lines:
                            mvals={
                                    'product_id': move.product_id.id,
                                    'qty_done': move.product_uom_qty,
                                    'product_uom_id': move.product_id.uom_id.id,
                                    'location_id': move.location_id.id,
                                    'location_dest_id': move.location_dest_id.id,
                                    'move_id': move.id}
                            # print("=====mvals111111=>",mvals)
                            StockPackObj.create(mvals)
                        picking.action_done()
                        # picking.write({'is_original': 'True'})
                        self._cr.commit()
                        # print("====done validate out")


                        ctx = self._context.copy()
                        ctx.update({'active_ids': [picking.id], 'active_id': picking.id})
                        res = return_obj.with_context(ctx).default_get(['product_return_moves', 'move_dest_exists'])
                        res.update({'invoice_state': '2binvoiced'})
                        return_id = return_obj.with_context(ctx).create({'invoice_state': 'none'})
                        self._cr.commit()

                        pick_id_return, type = return_id.with_context(ctx)._create_returns()
                        new_picking_id = self.env['stock.picking'].browse([pick_id_return])
                        # print ("new_picking_idddddddddddddddddd",new_picking_id)

                        picking.return_created = True

                        # print ("IIIIIIIFFFFFFFFFFFFF",new_picking_id)
                        new_picking_id.action_confirm()
                        for move in new_picking_id.move_lines:
                            mmvals =  {
                                    'product_id': move.product_id.id,
                                    'qty_done': move.product_uom_qty,
                                    'product_uom_id': move.product_id.uom_id.id,
                                    'location_id': move.location_id.id,
                                    'location_dest_id': move.location_dest_id.id,
                                    'move_id': move.id
                                    }
                            # print("=====mvals222222222=>",mmvals)

                            StockPackObj.create(mmvals)
                        
                        new_picking_id.action_done()
                        # new_picking_id.write({'is_return': 'True'})
                        self._cr.commit()
                            
        return True


    @api.one
    def createTags(self, tag_detail, wcapi):
        # print ("CREATEEEEEE_TAGSSSSSSSSSSSSSSS")

        prod_tag_obj = self.env['product.tags']
        tag_ids_list = []
        for tag_data in tag_detail:
            prod_tag_ids = prod_tag_obj.search([('tag_id','=', tag_data.get('id'))])
            tag_vals={
                    'name' :tag_data.get('name') ,
                    'slud_code' : tag_data.get('slug') ,
                    'description':tag_data.get('description') ,
                    'tag_id' : tag_data.get('id') ,
                }
            if prod_tag_ids:
                tag_ids_list.append(prod_tag_ids[0].id)
                tag_id = prod_tag_ids[0].id
                prod_tag_ids[0].write(tag_vals)
            else:
                tag_id = prod_tag_obj.create(tag_vals)
                tag_ids_list.append(tag_id.id)
        return tag_ids_list



    @api.multi
    def importTags(self):
        # print ("IMPORT_TAGSSSSSSSSSSSSSSS")
        prod_tag_obj = self.env['product.tags']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            try:
                count = 1

                tag_list = wcapi.get("products/tags?page="+ str(count))
                if not tag_list.status_code:
                    raise UserError(_("Enter Valid url"))
                tag_list = tag_list.json()

                while len(tag_list):
                    self.createTags(tag_list,wcapi)
                    count+=1
                    tag_list = wcapi.get("products/tags?page="+ str(count))
                    tag_list = tag_list.json()
            except Exception as e:
                # print ("Error.............%s",e)
                pass
        return True

    @api.one
    def createCoupons(self, coupon_detail, wcapi):
        coupon_obj = self.env['woocom.coupons']
        coupon_ids_list = []
        for coupon_data in coupon_detail:
            if coupon_data.get('discount_type') == 'percent':
                new_coupon =  'percent' 
            elif coupon_data.get('discount_type') == 'fixed_cart':
                new_coupon =  'fixed_cart' 
            else :
                new_coupon =  'fixed_product' 

            coupon_ids = coupon_obj.search(['|',('coupon_id','=', coupon_data.get('id')),('coupon_code','=', coupon_data.get('code'))])

            # coupon_ids = coupon_obj.search([('coupon_id','=', coupon_data.get('id'))])

            # print ("coupon_idsssssssssssssssssssssss",coupon_ids)
            coupon_vals={
                    'coupon_code' : coupon_data.get('code') ,
                    'description':coupon_data.get('description') ,
                    'coupon_id' : coupon_data.get('id') ,
                    'coupon_type' : new_coupon,
                }
            if coupon_ids:
                coupon_ids_list.append(coupon_ids[0].id)
                coupon_ids[0].write(coupon_vals)
            else:
                coupon_id = coupon_obj.create(coupon_vals)
                coupon_ids_list.append(coupon_id.id)
        return coupon_ids_list


    @api.multi
    def importCoupons(self):
        # print ("IMPORT_COUPONSSSSSSSS")
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            # print ("wcapiiiiiiiiiiiiiiiiiiiii",wcapi)
            try:
                count = 1
                coupon_list = wcapi.get("coupons?page="+ str(count))
                if not coupon_list.status_code:
                    raise UserError(_("Enter Valid url"))
                coupon_list = coupon_list.json()
                while len(coupon_list):
                    self.createCoupons(coupon_list,wcapi)
                    count+=1
                    coupon_list = wcapi.get("coupons?page="+ str(count))
                    coupon_list = coupon_list.json()
            except Exception as e:
                # print ("Error.............%s",e)
                pass
        return True



    @api.multi
    def updateWoocomCoupons(self):
        # print ("updateCouponssssssssss",self)

        coupon_obj = self.env['woocom.coupons']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if shop.woocommerce_last_update_coupon_date:
                coupon_ids = coupon_obj.search([('write_date','>', shop.woocommerce_last_update_coupon_date),('coupon_id','!=',False)])
            else:
                coupon_ids = coupon_obj.search([('coupon_id','!=',False)])
            for each in coupon_ids:

                if each.coupon_type == 'percent':
                     new_coupon =  'percent' 
                elif each.coupon_type == 'fixed_product':
                    new_coupon =  'fixed_product' 
                else: 
                    new_coupon =  'fixed_cart' 

                coupon_vals={
                        'code' :each.coupon_code,
                        'description' : each.description,
                        'id':each.coupon_id,
                        'discount_type' : new_coupon,
                    }

                coupon_url = 'coupons/' + str(each.coupon_id)
                coupon_val = wcapi.post(coupon_url, coupon_vals)


    @api.multi
    def exportWoocomCoupons(self):
        # print ("ExportCuponsssssssssssssss")
        coupon_obj = self.env['woocom.coupons']
        
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
                coupon_ids = coupon_obj.browse(self.env.context.get('export_product_ids'))
            else:
                coupon_ids = coupon_obj.search([('to_be_exported','=',True)])

            for coupon in coupon_ids:
                data = {
                        "code": coupon.coupon_code,
                        'description': coupon.description,
                        'id': coupon.coupon_id,
                        'discount_type':coupon.coupon_type and coupon.coupon_type or 'fixed_cart',
                    }

                res = wcapi.post("coupons", data)
                res = res.json()
                if res:
                    coupon.write({'coupon_id': res.get('id'), 'to_be_exported': False})


# @api.multi
#     def importWooCategory(self):
#         for shop in self:
#             wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
#             try:
#                 count = 1
#                 categ = wcapi.get("products/categories?page="+ str(count))
#                 if not categ.status_code:
#                     raise UserError(_("Enter Valid url"))
#                 category_list = categ.json()
# #                 try:
#                 for category in category_list:
#                     shop.create_woo_category(category, wcapi)
#                 while len(category_list) > 0:
#                     count += 1
#                     categ = wcapi.get("products/categories?page="+ str(count))
#                     category_list = categ.json()
#                     for category in category_list:
#                         shop.create_woo_category(category, wcapi)
# #                 except Exception as e:
# #                     if self.env.context.get('log_id'):
# #                         log_id = self.env.context.get('log_id')
# #                         self.env['log.error'].create({'log_description': str(e) + " While Getting product categories info of %s" % (category_list.get('product_categories')), 'log_id': log_id})
# #                     else:
# #                         log_id = self.env['woocommerce.log'].create({'all_operations':'import_categories', 'error_lines': [(0, 0, {'log_description': str(e) + " While Getting product categories info of %s" % (category_list.get('product_categories'))})]})
# #                         self = self.with_context(log_id=log_id.id)
#             except Exception as e:
#                 if self.env.context.get('log_id'):
#                     log_id = self.env.context.get('log_id')
#                     self.env['log.error'].create({'log_description': str(e), 'log_id': log_id})
#                 else:
#                     log_id = self.env['woocommerce.log'].create({'all_operations':'import_categories', 'error_lines': [(0, 0, {'log_description': str(e)})]})
#                     self = self.with_context(log_id=log_id.id)
#         return True


    
    @api.multi
    def updateWoocomCategory(self):
        categ_obj = self.env['woocom.category']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if shop.woocommerce_last_update_category_date:
                categ_ids = categ_obj.search([('write_date','>', shop.woocommerce_last_update_category_date),('woocom_id','!=',False)])
            else:
                categ_ids = categ_obj.search([('woocom_id','!=',False)])
            for each in categ_ids:
                cat_vals= ({
                            'id': each.woocom_id,
                            'name': each.name,
                            'parent': each.parent_id and str(each.parent_id.woocom_id) or '0',
                })
                categ_url = 'products/categories/' + str(each.woocom_id)
                cat_vals = wcapi.post(categ_url, cat_vals)



    @api.multi
    def updateWoocomCustomer(self):
        # print ("updatecustttttttttttttt")

        cust_obj = self.env['res.partner']
        for shop in self:
            # print ("shoppppppppppppppp",shop) 

            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if shop.woocommerce_last_update_customer_date:
                customer_ids = cust_obj.search([('write_date','>', shop.woocommerce_last_update_customer_date),('woocom_id','!=',False)])
                # print ("custidssssss11111111",customer_ids)
            else:
                customer_ids = cust_obj.search([('woocom_id','!=',False)])
                # print ("custidssssss22222222",customer_ids)
            
            for each in customer_ids:
                customer_name = each.name
                name_list = customer_name.split(' ')
                first_name = name_list[0]
                if len(name_list) > 1:
                    last_name = name_list[1]
                else:
                    last_name = name_list[0]

                cust_vals= ({
                            'id': each.woocom_id,
                            'name': each.name,
                            'parent': each.parent_id and str(each.parent_id.woocom_id) or '0',
                            "email":str(each.email),
                            "first_name": first_name,
                            "last_name": last_name,
                            "password" : str(each.email) ,
                            "billing": {
                                "first_name": first_name,
                                "last_name": last_name,
                                "company": str(each.parent_id.name),
                                "address_1": each.street  or '',
                                "address_2": each.street2  or '',
                                "city": each.city or '',
                                "state": str(each.state_id.code),
                                "postcode": str(each.zip) or '',
                                "country": str(each.country_id.code),
                                "email": str(each.email),
                                "phone": str(each.phone),
                            },
                            "shipping": {
                                "first_name":first_name,
                                "last_name": last_name,
                                "company": str(each.parent_id.name),
                                "address_1": each.street  or '',
                                "address_2": each.street2  or '',
                                "city": each.city or '',
                                "state": str(each.state_id.code),
                                "postcode": str(each.zip) or '',
                                "country": str(each.country_id.code)
                            }
                })
                # print ("custvalsssssssssssss",cust_vals)

                cust_url = 'customers/' + str(each.woocom_id)
                cust_vals = wcapi.post(cust_url, cust_vals)

                


    @api.multi
    def updateWoocomProductTag(self):
        # print ("updateWoocomProducsTagggggggggggg",self)

        tag_obj = self.env['product.tags']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if shop.woocommerce_last_update_product_tag_date:
                tag_ids = tag_obj.search([('write_date','>', shop.woocommerce_last_update_product_tag_date),('tag_id','!=',False)])
            else:
                tag_ids = tag_obj.search([('tag_id','!=',False)])
            for each in tag_ids:
                tag_vals={
                        'name' :each.name,
                        'slug' : each.slud_code,
                        'description':each.description,
                        'id' : each.tag_id,
                    }
                tag_url = 'products/tags/' + str(each.tag_id)
                tag_val = wcapi.post(tag_url, tag_vals)
 

                    
    @api.multi
    def updateWoocomProduct(self):
        #update product details,image and variants
        prod_templ_obj = self.env['product.template']
        prdct_obj = self.env['product.product']
        stock_quant_obj = self.env['stock.quant']
        inventry_line_obj = self.env['stock.inventory.line']
        prod_att_obj = self.env['product.attribute']
        prod_attr_vals_obj = self.env['product.attribute.value']
        inventry_line_obj = self.env['stock.inventory.line']
        inventry_obj = self.env['stock.inventory']
        stock_quanty = self.env['stock.quant']

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if shop.woocommerce_last_update_product_data_date:
                product_data_ids = prod_templ_obj.search([('write_date', '>',shop.woocommerce_last_update_product_data_date),('woocom_id', '!=', False)])
            else:
                product_data_ids = prod_templ_obj.search([('woocom_id', '!=', False)])
#             product_data_ids = prod_templ_obj.browse([55])
            for each in product_data_ids:
                categs = [{
                    "id": each.woo_categ.woocom_id,
                }]
                parent_id = each.woo_categ.parent_id
                while parent_id:
                    categs.append({
                         "id": parent_id.woocom_id,
                    })
                    parent_id = parent_id.parent_id
                image_list = []
                count = 1
                for image_data in each.woocom_product_img_ids:
                    if image_data.woocom_img_id:
                        image_list.append({
                            'id':image_data.woocom_img_id,
                            'src':image_data.url,
                            'position': count  
                            })
                    else:
                        image_list.append({
                            'src':image_data.url,
                            'position': count  
                        })
                    count +=1
                prod_vals = {
                'name' : each.name,
                'sku': str(each.default_code),
                "regular_price": each.woocom_regular_price and str(each.woocom_regular_price) or '0.00',
                'sale_price': each.woocom_price and str(each.woocom_price) or '0.00',#str(each.with_context(pricelist=shop.pricelist_id.id).price),
                'dimensions':{
                                'width': str(each.product_width),
                                'height': str(each.product_hght),
                                'length': str(each.product_lngth),
                                'weight': str(each.product_wght),
                                },
                'description' : each.description_sale and str(each.description_sale) or '',
                'short_description': each.description_sale and str(each.description_sale) or '',
#                 'images':image_list,
                'categories':categs,
                'id': int(each.woocom_id),
                }
                
                if each.attribute_line_ids:
                    p_ids = prdct_obj.search([('product_tmpl_id', '=' ,each.id)])
                    qaunt = 0
                    if p_ids:
                        stck_quant_id = stock_quanty.search([('product_id','in',p_ids.ids),('location_id','=',shop.warehouse_id.lot_stock_id.id)])
                        for stock in stck_quant_id:
                            qaunt += stock.quantity
                    prod_vals.update({
                        'type': 'variable',
                        'stock_quantity': int(qaunt),
                    }) 
                else:
                    p_ids = prdct_obj.search([('product_tmpl_id', '=' ,each.id)])
                    qaunt = 0
                    if p_ids:
                        stck_quant_id = stock_quanty.search([('product_id','=',p_ids[0].id),('location_id','=',shop.warehouse_id.lot_stock_id.id)])
                        for stock in stck_quant_id:
                            qaunt += stock.quantity
                    prod_vals.update({
                        'type': 'simple',
                        'stock_quantity': int(qaunt),
                    }) 
                if prod_vals.get('type') == 'simple':
                    prod_url = 'products/' + str(each.woocom_id)
                    prd_response = wcapi.post(prod_url, prod_vals)
                attributes = []
                if each.attribute_line_ids:
                    attributes = []
                    for attr in each.attribute_line_ids:
                        values = []
                        for attr_value in attr.value_ids:
                            values.append(attr_value.name)
                        attributes.append({
                            'id': int(attr.attribute_id.woocom_id),
                            'name': attr.attribute_id.name,
                            'options': values,
                            'variation': 'true',
                            'visible': 'false'
                        })
                    if attributes:
                        prod_vals.update({'attributes': attributes})
                        prod_url = 'products/' + str(each.woocom_id)
                        prod_export_res = wcapi.post(prod_url, prod_vals)
                
                prod_var_id = prdct_obj.search([('product_tmpl_id', '=', each.id)])

                for var in prod_var_id:
                    if not var.attribute_value_ids:
                        continue
                    values = []
                    for att in var.attribute_value_ids:
                        values.append({
                            'id': att.attribute_id.woocom_id,
                            'option': att.name,
                        })
                    var_vals = {
                        'name' : var.name,
    #                     'sale_price': str(var.with_context(pricelist=shop.pricelist_id.id).price),
                        'regular_price': var.woocom_regular_price and str(var.woocom_regular_price) or '0.00',
                        'sale_price': var.woocom_price and str(var.woocom_price) or '0.00',
                        'dimensions':{
                                    'width': str(var.product_width),
                                    'height': str(var.product_hght),
                                    'length': str(var.product_lngth),
                                    'weight': str(var.product_wght),
                                    },
                        'attributes': values,
                        }
                    if var.woocom_variant_id:
                        var_url = 'products/' + str(each.woocom_id) + '/variations/' + str(var.woocom_variant_id)
                    else:
                        var_url = 'products/' + str(each.woocom_id) + '/variations'
                    prd_response = wcapi.post(var_url, var_vals).json()
                    var.write({'woocom_variant_id': prd_response.get('id')  })
        return True           
            
            
    @api.multi
    def updateWoocomInventory(self):
        prod_templ_obj = self.env['product.template']
        prdct_obj = self.env['product.product']
        inv_wiz = self.env['stock.change.product.qty']
        stck_quant = self.env['stock.quant']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if self.env.context.get('product_ids'):
                p_ids = prod_templ_obj.browse(self.env.context.get('product_ids'))
            elif shop.woocommerce_last_update_inventory_date:
                p_ids = prod_templ_obj.search([('write_date','>', shop.woocommerce_last_update_inventory_date)])
            else:
                p_ids = prod_templ_obj.search([('woocom_id','!=',False)])
            for temp in p_ids:
                if temp.attribute_line_ids:
                    prod_var_id = prdct_obj.search([('product_tmpl_id', '=', temp.id)])
                    for var_id in prod_var_id:
                        stck_id = stck_quant.search([('product_id','=',var_id.id),('location_id','=',shop.warehouse_id.lot_stock_id.id)])
                        qty = 0
                        for stck in stck_id:
                            qty += stck.quantity
                        pro_vals = {
                            'stock_quantity' : int(qty),
                            'manage_stock' : 'true'
                        }
                        if qty > 0:
                            pro_vals.update({'in_stock': True})
                        else:
                            pro_vals.update({'in_stock': False})
                        url = "products/" + str(temp.woocom_id) +"/variations/" + str(var_id.woocom_variant_id)
                        pro_res = wcapi.post(url, pro_vals).json()
                else:
                    product_ids = prdct_obj.search([('product_tmpl_id', '=', temp.id)])
                    if product_ids:
                        stck_id = stck_quant.search([('product_id','=',product_ids[0].id),('location_id','=',shop.warehouse_id.lot_stock_id.id)])
                        qty = 0
                        for stck in stck_id:
                            qty += stck.quantity
                        pro_vals = {
                            'stock_quantity' : int(qty),
                            'manage_stock' : 'true'
                        }
                        if qty > 0:
                            pro_vals.update({'in_stock': True})
                        else:
                            pro_vals.update({'in_stock': False})
                        pro_url = 'products/' + str(temp.woocom_id)
                        pro_res = wcapi.post(pro_url, pro_vals).json()
            shop.write({'woocommerce_last_update_inventory_date': datetime.now()})
                
    @api.multi
    def updateWoocomOrderStatus(self):
        # print ("updateWoocomOrderStatusssssssssswwwwwwwwwww",self)

        sale_order_obj = self.env['sale.order']
        status_obj = self.env['woocom.order.status']

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')

            sale_order_ids = sale_order_obj.search([('woocom_id', '!=', False), ('order_status','in',['pending','processing','on-hold','completed','refunded'])])

            # track_list = []

            for sale_order in sale_order_ids:
                # print ("SALEorderrrrrrrrrr",sale_order)

                ordr_url = 'orders/' + str(sale_order.woocom_id)
                order_vals = {
                     'status' : 'completed',

                }

                ord_res = wcapi.post(ordr_url, order_vals).json()
                if ord_res:
                    sale_order.write({'order_status': 'completed'})
                    
                
    @api.multi
    def expotWoocomOrder(self):
        # print ("expotWoocomOrderrrrrrrrwwwwwwwwwwwww",self)

        sale_order_obj = self.env['sale.order']
        res_partner_obj = self.env['res.partner']
        carrier_obj = self.env['delivery.carrier']
#         status_obj = self.env['presta.order.status']
        sale_order_line_obj = self.env['sale.order.line']
        prod_attr_val_obj = self.env['product.attribute.value']
        prod_templ_obj = self.env['product.template']
        product_obj = self.env['product.product']
        invoice_obj = self.env['account.invoice']
        invoice_refund_obj = self.env['account.invoice.refund']
        return_obj = self.env['stock.return.picking']
        return_line_obj = self.env['stock.return.picking.line']

        prod_templ_obj = self.env['product.template']
        prdct_obj = self.env['product.product']
        categ_obj = self.env['product.category']
         
        for shop in self:

            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
                order_ids = sale_order_obj.browse(self.env.context.get('export_product_ids'))
            else:
                order_ids = sale_order_obj.search([('to_be_exported', '=', True)])
            for order in order_ids:
                order_name = order.partner_id.name
                name_list = order_name.split(' ')
                first_name = name_list[0]
                if len(name_list) > 1:
                    last_name = name_list[1]
                else:
                    last_name = name_list[0]
                data = {
                    'customer_id' : int(order.partner_id.woocom_id),
                    'payment_method' :str(order.woocom_payment_mode),
                    'status' : str(order.order_status),
                    "billing": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "address_1": order.partner_id.street,
                        "address_2":order.partner_id.street2,
                        "city": order.partner_id.city,
                        "state": str(order.partner_id.state_id.code),
                        "postcode": str(order.partner_id.zip),
                        "country":  str(order.partner_id.country_id.code),
                        "email": str(order.partner_id.email),
                        "phone": str(order.partner_id.phone)
                    },
                    
                    "shipping": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "address_1": order.partner_id.street,
                        "address_2":order.partner_id.street2,
                        "city": order.partner_id.city,
                        "state": str(order.partner_id.state_id.code),
                        "postcode":str(order.partner_id.zip),
                        "country":  str(order.partner_id.country_id.code)
                    },
                    "total" : str(order.amount_total),
                    "line_items": [
                    ],
                    "shipping_lines": [
                        {
                            'method_id': str(order.carrier_id.woocom_id),
                            'method_title': str(order.carrier_id.name),
                            }
                    ]
                }
                if order.order_line:
                    line_items = []
                    for line in order.order_line:
                        product = False
                        if line.product_id and line.product_id.attribute_value_ids:
                            product = line.product_id.woocom_variant_id
                        else:
                            product = line.product_id.product_tmpl_id.woocom_id
                        line_items.append({
                            "product_id":  product,
                            "name" : line.name,
                            "quantity": str(line.product_uom_qty),
                            "price" : str(line.price_unit),
                            "shipping_total": str(line.price_unit),
                            
                        })
                    data.update({
                        'line_items': line_items
                    })
                ordr_export_res = wcapi.post("orders",data).json()
                if ordr_export_res:
                    order.write({'woocom_id': ordr_export_res.get('id'), 'to_be_exported': False})
                
                            
    @api.multi
    def exportWoocomCategories(self):
        # print ("EXPOCATTTTTTTTTTt")
        categ_obj = self.env['woocom.category']
        
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
               
                category_ids = categ_obj.browse(self.env.context.get('export_product_ids'))
            else:
                category_ids = categ_obj.search([('to_be_exported','=',True)])
            for categ in category_ids:
                data = {
                        "name":categ.name,
                        'slug':categ.name.replace(' ','_'),
                        "parent": categ.parent_id.woocom_id and int(categ.parent_id.woocom_id) or 0,
                    }
                res = wcapi.post("products/categories", data)
                res = res.json()
                if res:
                    categ.write({'woocom_id': res.get('id'), 'to_be_exported': False})



    @api.multi
    def exportWoocomProductTags(self):
        # print ("ExportTagsssssssssssssssssssssssss")
        tag_obj = self.env['product.tags']
        
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
                tag_ids = tag_obj.browse(self.env.context.get('export_product_ids'))
            else:
                tag_ids = tag_obj.search([('to_be_exported','=',True)])

            for tag in tag_ids:
                data = {
                        "name": tag.name,
                        'slug': tag.slud_code,
                        'id': tag.tag_id,
                        'description':tag.description,
                    }
                res = wcapi.post("products/tags", data)
                res = res.json()
                if res:
                    tag.write({'tag_id': res.get('id'), 'to_be_exported': False})

            
    @api.multi
    def exportWoocomCustomers(self):
        res_partner_obj = self.env['res.partner']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
                customer_ids = res_partner_obj.browse(self.env.context.get('export_product_ids'))
            else:
                customer_ids = res_partner_obj.search([('to_be_exported', '=', True)])
            for customer in customer_ids:
                customer_name = customer.name
                name_list = customer_name.split(' ')
                first_name = name_list[0]
                if len(name_list) > 1:
                    last_name = name_list[1]
                else:
                    last_name = name_list[0]
                custom_data = {
                        "email": str(customer.email),
                        "first_name": first_name,
                        "last_name": last_name,
                        "password" : str(customer.email) ,
                        "billing": {
                            "first_name": first_name,
                            "last_name": last_name,
                            "company": str(customer.parent_id.name),
                            "address_1": customer.street  or '',
                            "address_2": customer.street2  or '',
                            "city": customer.city or '',
                            "state": str(customer.state_id.code),
                            "postcode": str(customer.zip) or '',
                            "country": str(customer.country_id.code),
                            "email": str(customer.email),
                            "phone": str(customer.phone),
                        },
                        "shipping": {
                            "first_name":first_name,
                            "last_name": last_name,
                            "company": str(customer.parent_id.name),
                            "address_1": customer.street  or '',
                            "address_2": customer.street2  or '',
                            "city": customer.city or '',
                            "state": str(customer.state_id.code),
                            "postcode": str(customer.zip) or '',
                            "country": str(customer.country_id.code)
                        }
                    }
                cust_export_res = wcapi.post("customers", custom_data).json()
                if cust_export_res:
                    customer.write({'woocom_id': cust_export_res.get('id'), 'to_be_exported': False})
                
    @api.multi
    def exportWoocomProduct(self):
        # print ("EXPOPRODDDDDDDD")
        prod_templ_obj = self.env['product.template']
        prdct_obj = self.env['product.product']
        stock_quanty = self.env['stock.quant']
        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            if self.env.context.get('export_product_ids'):
                product_ids = prod_templ_obj.browse(self.env.context.get('export_product_ids'))
            else:
                product_ids = prod_templ_obj.search([('product_to_be_exported', '=', True)])
            for product in product_ids:
                categs = [{
                    "id": product.woo_categ.woocom_id,
                }]
                parent_id = product.woo_categ.parent_id
                while parent_id:
                    categs.append({
                         "id": parent_id.woocom_id,
                    })
                    parent_id = parent_id.parent_id
                images = []
                count = 0
                for image_data in product.woocom_product_img_ids:
                    images.append({
                        'src':image_data.url,
                        'position': count  
                        })
                    count +=1
                prod_vals = {
                    "name" :product.name,
                    "slug": product.name.replace(' ','_'),
                    "sku": str(product.default_code),
                    "manage_stock": 'true',
                    "in_stock": 'true',
#                     "stock_quantity": product.qty_available ,
                    "dimensions": {
                                        "length": str(product.product_lngth),
                                        "width": str(product.product_width),
                                        "height": str(product.product_hght),
                                        "weight": str(product.product_wght),
                                      },
                    "regular_price": product.woocom_regular_price and str(product.woocom_regular_price) or '0.00',
                    "sale_price": product.woocom_price and str(product.woocom_price) or '0.00',
                    "images":images,
                    "categories": categs,
                    'description' : str(product.description_sale),
                    'in_stock': 'true',
                    'manage_stock': 'true'
                }
                if product.attribute_line_ids:
                    p_ids = prdct_obj.search([('product_tmpl_id', '=' ,product[0].id)])
                    qaunt = 0
                    if p_ids:
                        stck_quant_id = stock_quanty.search([('product_id','in',p_ids.ids),('location_id','=',shop.warehouse_id.lot_stock_id.id)])
                        for stock in stck_quant_id:
                            qaunt += stock.quantity
                    prod_vals.update({
                        'type': 'variable',
                        'stock_quantity': int(qaunt),
                    }) 
                else:
                    p_ids = prdct_obj.search([('product_tmpl_id', '=' ,product[0].id)])
                    qaunt = 0
                    if p_ids:
                        stck_quant_id = stock_quanty.search([('product_id','=',p_ids[0].id),('location_id','=',shop.warehouse_id.lot_stock_id.id)])
                        for stock in stck_quant_id:
                            qaunt += stock.quantity
                    prod_vals.update({
                        'type': 'simple',
                        'stock_quantity': int(qaunt),
                    }) 
                if prod_vals.get('type') == 'simple':
                    prod_export_res = wcapi.post("products", prod_vals).json()
                    if prod_export_res:    
                        product.write({'woocom_id': prod_export_res.get('id'),'product_to_be_exported': False})
                attributes = []
                if product.attribute_line_ids:
                    attributes = []
                    for attr in product.attribute_line_ids:
                        values = []
                        for attr_value in attr.value_ids:
                            values.append(attr_value.name)
                        attributes.append({
                            'name': attr.attribute_id.name,
                            'options': values,
                            'variation': True,
                            'visible': False
                        })
                    if attributes:
                        prod_vals.update({'attributes': attributes})
                        prod_export_res = wcapi.post("products", prod_vals).json()
                        if prod_export_res:    
                            product.write({'woocom_id': prod_export_res.get('id'),'product_to_be_exported': False})
                     
                        prod_var_id = prdct_obj.search([('product_tmpl_id', '=', product.id)])
                        for variant in prod_var_id:
                            stck_id = stock_quanty.search([('product_id','=',variant.id),('location_id','=',shop.warehouse_id.lot_stock_id.id)])
                            qty = 0
                            for stck in stck_id:
                                qty += stck.quantity
                            variation_vals = {
                                'sku': str(variant.default_code),
                                'stock_quantity': int(qty),
                                'in_stock': 'true',
                                'manage_stock': 'true',
                                "sale_price": variant.woocom_price and str(variant.woocom_price) or '0.00',
                                'regular_price': variant.woocom_regular_price and str(variant.woocom_regular_price) or '0.00',
                                'weight' : str(variant.product_wght),
                                'attributes': [{'option': avalue.name, 'name':avalue.attribute_id.name} for avalue in variant.attribute_value_ids],
                                "dimensions": {
                                    "length": str(variant.product_lngth),
                                    "width": str(variant.product_width),
                                    "height": str(variant.product_hght),
                                  },
                            }
                            url = "products/" +str(prod_export_res.get('id')) + "/variations"
                            prod_var_res = wcapi.post("products/" +str(prod_export_res.get('id')) + "/variations", variation_vals).json()
                            if prod_var_res:    
                                variant.write({'woocom_variant_id': prod_var_res.get('id'),'product_to_be_exported': False})
                    



    @api.model
    def auto_scheduler_process_import_orders(self, cron_mode=True):
        # print ("SCHEDULAR_import_orderssssssssss")
        search_ids = self.search([('auto_import_order', '=', True)])
        if search_ids:
            search_ids.importWoocomOrder()


    @api.model
    def auto_scheduler_process_import_products(self, cron_mode=True):
        # print ("SCHEDULAR_import_productsssssssssssssssss")
        search_ids = self.search([('auto_import_products', '=', True)])
        if search_ids:
            search_ids.importWoocomProduct()


    @api.model
    def auto_scheduler_process_update_inventory(self, cron_mode=True):
        # print ("SCHEDULAR_update_inventoryyyyyyyyyy")
        search_ids = self.search([('auto_update_inventory', '=', True)])
        if search_ids:
            search_ids.importWoocomInventory()


    @api.model
    def auto_scheduler_process_update_orders(self, cron_mode=True):
        # print ("SCHEDULAR_update_orderssssssssssss")
        search_ids = self.search([('auto_update_order_status', '=', True)])
        if search_ids:
            search_ids.updateWoocomOrderStatus()


    @api.model
    def auto_scheduler_process_update_products(self, cron_mode=True):
        # print ("SCHEDULAR_update_productsssssssss")
        search_ids = self.search([('auto_update_product_data', '=', True)])
        if search_ids:
            search_ids.updateWoocomProduct()


    @api.model
    def auto_scheduler_process_update_customers(self, cron_mode=True):
        # print ("SCHEDULAR_update_customerssssssssss")
        search_ids = self.search([('auto_update_customer_data', '=', True)])
        if search_ids:
            search_ids.updateWoocomCustomer()
        