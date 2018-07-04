# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.addons.gt_woocommerce_integration.api import API
from odoo.addons.gt_woocommerce_integration.api import woocom_api
import logging
logger = logging.getLogger('__name__')
import sys, json


class SaleShop(models.Model):
    _inherit = "sale.shop"


    @api.one
    def create_woo_order(self, order_detail, wcapi):
        print ("create_woo_orderrrrrrr111122233")

        ctx = self.env.context.copy()
        sale_order_obj = self.env['sale.order']
        res_partner_obj = self.env['res.partner']
        carrier_obj = self.env['delivery.carrier']
        status_obj = self.env['woocom.order.status']
        payment_obj = self.env['payment.gatway']
        woocom_conector = self.env['woocommerce.connector.wizard']
        avatax_address = self.env['avalara.salestax.address.validate']
        
        if not order_detail.get('line_items'):
            return False
        custm_id = order_detail.get('customer_id')
        # print("===custm_idddddddddddddddddd***********>",custm_id)
        
        if not custm_id:
            # print("===NOTTTTTTTcustm_idcustm_idcustm_id********>",custm_id)
            partner_id = self[0].partner_id.id
            # print ("partner_idssssssss*********>>>>>>>>>",partner_id,self.partner_id)
          
        else:
            # print ("==ELSEEEEORDERRRRRRRRRR**************>")
            part_ids = res_partner_obj.search([('woocom_id', '=', custm_id)])
            if part_ids:
                # print ("iffffff_part_ids**************>",part_ids)
                partner_id = part_ids[0].id
                logger.info('partner id ===> %s', partner_id)
                # print ("part_idsss0000000000000************>",part_ids)

            else:
                # print ("==esleeeeeeee***********>")
                url = 'customers/' + str(custm_id)
                # print ("CUSTOMER_urlllllllll**********",url)
                customer_data = wcapi.get(url)
                customer_data = customer_data.json()
                partner_id = self.create_woo_customer(customer_data, wcapi)[0].id
                # print ("PARTNERRRRRRRRRRRR***********",partner_id)

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

        if order_detail.get('status') == 'draft':
            order_detail.update({'status': 'pending'})
        
        order_vals = {'partner_id': partner_id,
                      'woocom_id' : order_detail.get('id'),
                      'warehouse_id': self.warehouse_id.id,
                      'name': (self.prefix and self.prefix or '') + str(order_detail.get('id')) + (self.suffix and self.suffix or ''),
                      'pricelist_id': self.pricelist_id.id,
                      'order_status' : order_detail.get('status'),
                      'shop_id': self.id,
                      'carrier_woocommerce': car_id or False,
                      'woocom_payment_mode':pay_id,
                       'tax_add_id': partner_id,
        }
        print ("ORDRVALSSSSSSSSSSSSSSSSS**********",order_vals)

        sale_order_ids = sale_order_obj.search([('woocom_id', '=', order_detail.get('id'))])
        # print ("SALEORDERIDDDDDDDD***********",sale_order_ids)


        if not sale_order_ids:
            s_id = sale_order_obj.create(order_vals)
            print ("sidd11111111111111d**********",s_id,s_id.name)

            s_id.delivery_tax_address()
            s_id.partner_id
            ctx.update({'active_id':s_id.partner_id.id})

            address = s_id.partner_id.read(['street', 'street2', 'city', 'state_id', 'zip', 'country_id'])[0]
            # print ("Addresssssssssssssssss",address)

            address['state_id'] = address.get('state_id') and address['state_id'][0]
            # print ("stateidddddddd",address['state_id'])

            address['country_id'] = address.get('country_id') and address['country_id'][0]
            # print ("countryidddddd",address['country_id'])
            

            valid_address = res_partner_obj._validate_address(address)
            data = {
                'original_street': s_id.partner_id.street,
                'original_street2':s_id.partner_id.street2,
                'original_city':s_id.partner_id.city,
                'original_state': res_partner_obj.get_state_code(address['state_id']),
                'original_zip':s_id.partner_id.zip,
                'original_country': res_partner_obj.get_state_code(address['country_id']),

                'street': str(valid_address.Line1 or ''),
                'street2': str(valid_address.Line2 or ''),
                'city': str(valid_address.City or ''),
                'state': str(valid_address.Region or ''),
                'zip': str(valid_address.PostalCode or ''),
                'country': str(valid_address.Country or ''),
                'latitude': str(valid_address.Latitude or ''),
                'longitude': str(valid_address.Longitude or ''),
            }
            # print ("dataaaaaaaaaaaaaa",data)
            res_data = avatax_address.create(data)
            # print ("res_dataaaaaaaaaaaaaaaa",res_data)
            res_date = res_data.with_context(ctx).accept_valid_address()
            # print ("res_dateeeeeeeeeeeeeeeeee===",res_date)

            self._cr.commit()
            
            self.woocomManageOrderLines(s_id, order_detail.get('line_items'), wcapi)
            if order_detail.get('coupon_lines', False):
                    # print ("IIIIIIIIINNNNNNNNN111111111111")
                    self.woocomManageCoupon(s_id, order_detail.get('coupon_lines'), wcapi)
            self.woocomManageOrderWorkflow(s_id, order_detail, order_detail.get('status'))
        else:
            if sale_order_ids.state != 'done':
                s_id = sale_order_ids[0]
                
                # s_id.delivery_tax_address()
                print ("SID22222222222***********",s_id,s_id.name)

                # logger.info('create order ===> %s', s_id.name)
                s_id.write(order_vals)
                self.woocomManageOrderLines(s_id, order_detail.get('line_items'), wcapi)
                if order_detail.get('coupon_lines', False):
                    # print ("IIIIIIIIINNNNNNNNN111111111111")
                    self.woocomManageCoupon(s_id, order_detail.get('coupon_lines'), wcapi)
                self.woocomManageOrderWorkflow(s_id, order_detail, order_detail.get('status'))


        if order_detail.get("meta_data"):
            # print ("IIIIIINNNNNNNNN*****===========>",order_detail) 

            if not isinstance(order_detail.get("meta_data"), list):
                meta_info = order_detail.get("meta_data").values()
                print ("reccccccc22222222",meta_info)
            else:
                meta_info = order_detail.get("meta_data")
                # print ("reccccccc33333333",meta_info)

            for rec in meta_info:
                # print ("reccccccccccccccccccc",rec)
                
                if rec.get('key') == '_aftership_tracking_number':
                    # print ("iiiiiiiifffffffffffffff",rec.get('key'))
                    track_vals={
                        'carrier_tracking_ref' : rec.get('value'),
                    }
                    # print ("elseeeeeetrack_valsssssssssssss",track_vals)
                    track_data = sale_order_ids.picking_ids.write(track_vals)
                    # print ("CREATEEEEEEETRACKDATAAAAAAAAA",track_data)

                    
                
    @api.multi
    def updateWoocomOrderStatus(self):
        print ("updateWoocomOrderStatusssssssssss")
        sale_order_obj = self.env['sale.order']
        status_obj = self.env['woocom.order.status']

        for shop in self:
            wcapi = API(url=shop.woocommerce_instance_id.location, consumer_key=shop.woocommerce_instance_id.consumer_key, consumer_secret=shop.woocommerce_instance_id.secret_key,wp_api=True, version='wc/v2')
            sale_order_ids = sale_order_obj.search([('woocom_id', '!=', False), ('order_status','in',['pending','processing','on-hold','completed','refunded'])])
            track_list = []
            for sale_order in sale_order_ids:
                ordr_url = 'orders/' + str(sale_order.woocom_id)
                order_vals = {
                     'status' : 'completed',
                }
                data1 = {
                    # 'id':222,
                    'key':'_aftership_tracking_number',
                    'value': sale_order.picking_ids.carrier_tracking_ref,
                }
                data2 = {
                    # 'id':222,
                    'key':'_aftership_tracking_shipdate',
                    'value': sale_order.picking_ids.scheduled_date,
                }
                data3 = {
                    # 'id':222,
                    'key':'_aftership_tracking_postal',
                    'value': sale_order.picking_ids.partner_id.zip,
                }
                track_list.append(data1)
                track_list.append(data2)
                track_list.append(data3)
                order_vals.update({'meta_data': track_list})
                
                ord_res = wcapi.post(ordr_url, order_vals).json()
                if ord_res:
                    sale_order.write({'order_status': 'completed'})
                    


    @api.multi
    def expotWoocomOrder(self):
        # print ("expotWoocomOrderrrrrrrrrrrrrrrrrrrr",self)

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

            track_list = []
            for order in order_ids:
                # print ("forrrrrrORDERRRRRRRRRRRR",order)
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
                # print ("DATAAAAAAAAA",data) 
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
                # print ("pickingiddddddddddd",order.picking_ids) 
                data1 = {
                    # 'id':222,
                    'key':'_aftership_tracking_number',
                    'value': order.picking_ids.carrier_tracking_ref,
                }
                data2 = {
                    # 'id':222,
                    'key':'_aftership_tracking_shipdate',
                    'value': order.picking_ids.scheduled_date,
                }
                data3 = {
                    # 'id':222,
                    'key':'_aftership_tracking_postal',
                    'value': order.picking_ids.partner_id.zip,
                }
                track_list.append(data1)
                track_list.append(data2)
                track_list.append(data3)
                # print ("TRACKLISTTTTTTTTTTTT",track_list) 
                data.update({'meta_data': track_list})
                # print ("dataaaaaaaaaaaa",data)
                ordr_export_res = wcapi.post("orders",data).json()
                if ordr_export_res:
                    order.write({'woocom_id': ordr_export_res.get('id'), 'to_be_exported': False})