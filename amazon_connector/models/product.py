# -*- coding: utf-8 -*-
import logging
from odoo.api import model
logger = logging.getLogger('amazon')
import time
from datetime import  datetime
from odoo import api, fields, models, _
from odoo.addons.amazon_connector.amazon_api import amazonerp_osv as amazon_api_obj
from odoo.exceptions import UserError
class ProductCategory(models.Model):
    _inherit = "product.category"
    
    amazon_category = fields.Boolean(string='Amazon Category')
    amazon_cat_id = fields.Char(string="Amazon Category ID")
    shop_ids = fields.Many2many('sale.shop', 'categ_amazon_shop_rel', 'categ_amazon_id', 'shop_id', string="Shops")
#     shop_ids = fields.One2many('sale.shop', 'shop_amazon_categ_id', string="Shops")
    
    @api.multi
    def create_amazon_category(self, shops, categ_list):
        logger.info("Create Category From List")
        
        # create category from list of category dict
        # categ_list : List of category_info list
        if isinstance(categ_list, dict):
            categ_list = [categ_list]
        for categ in categ_list:
#             print"categ",categ
            parents = categ.get('browsePathById', False)
            p_id = False
            if parents:
                p_datas = parents.split(',')
                if len(p_datas) >= 2:
                    parent_values = p_datas[:-1]
                    if parent_values:
                        parent_id = parent_values[len(parent_values)-1]
                        p_ids = self.search([('amazon_cat_id', '=', parent_id)])
                        if p_ids:
                            p_id = p_ids[0].id
            
            c_ids = self.search([('amazon_cat_id', '=', categ.get('browseNodeId', False))])    
            if c_ids:
                self.env.cr.execute("select categ_amazon_id from categ_amazon_shop_rel where categ_amazon_id = %s and shop_id = %s"%(c_ids[0].id, shops.id))
                if not self.env.cr.fetchone():
                    self.env.cr.execute("insert into categ_amazon_shop_rel values(%s, %s)"%(c_ids[0].id, shops.id,))
                continue
            cat_vals = {
                'amazon_category' : True,
                'amazon_cat_id' : categ.get('browseNodeId', False),
                'name' : categ.get('browseNodeName', False),
                'parent_id' : p_id
            }
#             try:
            c_id = self.create(cat_vals)
            logger.info("Created Category : %s with ID %s"%(c_id.name, c_id.id,))
            self.env.cr.execute("select categ_amazon_id from categ_amazon_shop_rel where categ_amazon_id = %s and shop_id = %s"%(c_id.id, shops.id))
            if not self.env.cr.fetchone():
                self.env.cr.execute("insert into categ_amazon_shop_rel values(%s, %s)"%(c_id.id, shops.id,))
            self.env.cr.commit()
#             except Exception as e:
#                 logger.info('Error %s', e, exc_info=True)
#                 pass
    
    @api.multi
    def price_compute(self, price_type, uom=False, currency=False, company=False):
        print ("======price_compute======>",self.env.context)
        # TDE FIXME: delegate to template or not ? fields are reencoded here ...
        # compatibility about context keys used a bit everywhere in the code
        if not uom and self._context.get('uom'):
            uom = self.env['product.uom'].browse(self._context['uom'])
        if not currency and self._context.get('currency'):
            currency = self.env['res.currency'].browse(self._context['currency'])

        products = self
        if price_type == 'standard_price':
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            products = self.with_context(force_company=company and company.id or self._context.get('force_company', self.env.user.company_id.id)).sudo()

        prices = dict.fromkeys(self.ids, 0.0)
        for product in products:
            prices[product.id] = product[price_type] or 0.0
            if price_type == 'list_price':
                prices[product.id] += product.price_extra

            if uom:
                prices[product.id] = product.uom_id._compute_price(prices[product.id], uom)

            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                prices[product.id] = product.currency_id.compute(prices[product.id], currency)

        return prices
            


class AmazonProductsMaster(models.Model):
    _name = "amazon.products.master"

    name =fields.Char('Product Name', size=64)
    product_asin= fields.Char('ASIN',size=10)
    product_category=  fields.Char('Category', size=64)
    product_id=fields.Many2one('product.product', 'Product')
    amazon_product_attributes= fields.Text('Extra Product Details')

class AmazonProductLlisting(models.Model):
    _name = "amazon.product.listing"
    
        
#     def cal_diff_price(self,cr,uid,ids,args1=None,args2=None,context=None):
#         vals={}
#         amt=0.0
#         for rec in self.browse(cr,uid,ids):
#             
#             currency_id=self.pool.get('res.currency').search(cr,uid,[('name','=',rec.currency_id.name)])[0]
#             currency_obj=self.pool.get('res.currency').browse(cr,uid,currency_id)
#             if rec.product_id.lst_price and currency_obj:
#                 if currency_obj.rate:
#                     amt=rec.product_id.lst_price*currency_obj.rate
#             vals[rec.id]=amt
#         return vals

#     def default_get(self, cr ,uid, fields, context=None):
#         x=super(amazon_product_listing,self).default_get(cr,uid,fields,context=context) 
#         self.get_name(cr,uid,context=context)
#         print x
#         print context
#         return True


    def get_data(self,vals):
        prod_obj=self.env['product.product']
        if self._context.get('default_product_id'):
            prod_ids = prod_obj.browse(self._context.get('default_product_id'))
            if vals=='name':
                name=prod_ids.name
                return name
            elif vals == 'desp':
                desp=prod_ids.amazon_desc
                return desp
            elif vals== 'asin':
                asin=prod_ids.asin
                return asin
            elif vals== 'upc':
                upc=prod_ids.upc
                return upc
            elif vals == 'prod_id':
                prod_id=prod_ids.id
                return prod_id
    
    def get_listn(self):
        if self._context.get('new_lstn'):
            new_lstn=self._context.get('new_lstn')
            return new_lstn
    
    name = fields.Char('Name',size=64,required=True)
    default_code = fields.Char('SKU',size=64)
    asin = fields.Char('ASIN',size=64)
    fulfilled_by = fields.Char('Fulfilled By')
    product_id = fields.Many2one('product.product', string='Product Name',ondelete='cascade')
    condition = fields.Char('Condition')
    amazon_condition = fields.Selection([('New','New'),('UsedLikeNew','Used Like New'),('UsedVeryGood','Used Very Good'),('UsedGood','Used Good'),('UsedAcceptable','Used Acceptable'),('CollectibleLikeNew','Collectible Like New'),('CollectibleVeryGood','Collectible Very Good'),('CollectibleGood','Collectible Good'),('CollectibleAcceptable','Collectible Acceptable'),('Refurbished','Refurbished'),('Club','Club')],'Condition')
    stock_status = fields.Char('Supply Type')
    currency_id = fields.Many2one('res.currency','Currency')
    prod_dep = fields.Text('Product Description' ,store=True)
    price = fields.Float('Price')
    title = fields.Text('Title')
    code_type = fields.Char('UPC/ISBN',size=20)
    fulfillment_by = fields.Selection([
        ('MFN','Fulfilled by Merchant(MFN)'),
        ('AFN','Fulfilled by Amazon(AFN)')],'Fulfillment By')
    shop_id = fields.Many2one('sale.shop','Shop')
    quantity = fields.Float('Quantity')
    listing_id = fields.Char('Listing ID')
    new_lstn = fields.Boolean('New Listing')
   
#     @api.onchange('shop_id')
#     def onchange_product_shop(self):
#         currency_obj = self.env['res.currency']
#         product_obj=self.env['product.product']
#         res=self.default_get(['product_id'])
#         vals={}
#         product_id = res.get('product_id')
#         if product_id:
#             sku = self.product_id.default_code
#             print "sku", sku
#             if self.shop_id:
#                 name = self.shop_id.name
#                 print "name",name
#                 if '-FBM' in name:
#                     if '-CA' in name:
#                         new_sku=sku +'-CA-FBM'
#                         currency_id=currency_obj.search([('name','=','CAD')])[0]
#                         if name.lower() == 'amazon-su-ca-fbm':
#                             self.product_id.write({'su_ca_fbm':True})
#                             
#                         elif name.lower() == 'amazon-dc-ca-fbm':
#                             self.product_id.write({'dc_ca_fbm':True})
#                            
#                             
#                     elif '-MX' in name:
#                         new_sku=sku +'-MX-FBM'
#                         currency_id=currency_obj.search([('name','=','MXN')])[0]
#                         if name.lower() == 'amazon-su-mx-fbm':
#                             self.product_id.write({'su_mx_fbm':True})
#                             
#                         elif name.lower() == 'amazon-dc-mx-fbm':
#                             self.product_id.write({'dc_mx_fbm':True})
#                     else:
#                         new_sku=sku +'-FBM'
#                         currency_id=currency_obj.search([('name','=','USD')])[0]
#                         if name.lower() == 'amazon-su-us-fbm':
#                             self.product_id.write({'su_us_fbm':True})        
#                                             
#                         elif name.lower() == 'amazon-dc-us-fbm':
#                             self.product_id.write({'dc_us_fbm':True})
#                     
#                     vals.update({'default_code':new_sku,'fulfillment_by':'MFN','currency_id':currency_id})
#                 
#                 elif '-FBA' in name:
#                     if '-CA' in name:
#                         new_sku=sku +'-CA-FBA'
#                         currency_id=currency_obj.search([('name','=','CAD')])[0]
#                         if name.lower() == 'amazon-su-ca-fba':
#                             self.product_id.write({'su_ca_fba':True})  
#                             
#                         elif name.lower() == 'amazon-dc-ca-fba':
#                             self.product_id.write({'dc_ca_fba':True}) 
#                             
#                     elif '-MX' in name:
#                         new_sku=sku +'-MX-FBA'
#                         currency_id=currency_obj.search([('name','=','MXN')])[0]
#                         if name.lower() == 'amazon-su-mx-fba':
#                             self.product_id.write({'su_mx_fba':True}) 
#                         elif name.lower() == 'amazon-dc-mx-fba':
#                             print "=======elif======"
#                         if name.lower() == 'amazon-su-us-fba':
#                             product_obj.write({'su_us_fba':True})      
#                         elif name.lower() == 'amazon-dc-us-fba':
#                             product_obj.write({'dc_us_fba':True})
#                                       
#                     vals.update({'default_code':new_sku,'fulfillment_by':'AFN','currency_id':currency_id})
#                 elif '-SFP' in name:
#                     new_sku=sku + '-SFP'
#                     currency_id=currency_obj.search([('name','=','USD')])[0]
#                     
#                     if name.lower() == 'amazon-su-us-sfp':
#                         self.product_id.write({'su_us_sfp':True})
#                         
#                     elif name.lower() == 'amazon-dc-us-sfp':
#                         self.product_id.write({'dc_us_sfp':True})  
#                     vals.update({'default_code':new_sku,'fulfillment_by':'MFN','currency_id':currency_id})        
#         return {'value':vals}


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    amazon_categ_id = fields.Many2one('product.category',string="Amazon Category")
    
    def _calculate_amazon_margin(self, name, arg):
        shop_obj = self.env['sale.shop']
        manufacturer_obj = self.env['manufacturer.master']
        margin_obj = self.env['margin.calculation']
        res = {}
        for data_prod in self:
            standard_price=data_prod.standard_price
            margin=60
            amazon_shop_id=shop_obj.search([('amazon_shop','=',True)])
            if len(amazon_shop_id):
                get_amazon_margin = amazon_shop_id[0].amazon_margin
                if get_amazon_margin != 0.0:
                    margin=get_amazon_margin
            margin_ids = margin_obj.search([('shop_id','=',amazon_shop_id)])
            for sin_id in margin_ids:
                if (float(data_prod.standard_price) >=float(sin_id.cost_up) and float(data_prod.standard_price)<=float(sin_id.cost_to)):
                        margin = sin_id.per
                        print('Your Amazon margin is=========================>',margin)
                        break
            margin_val = standard_price * margin/100
            res[data_prod.id] = standard_price + margin_val
            get_additional_margin = (standard_price + margin_val) * 21/100
            
            #added 12% amazon tax
            get_p = margin_val * 0.13636
            ex = 0.13636 * (standard_price + get_additional_margin + margin_val)
            total_valsf = standard_price + get_additional_margin + margin_val + ex
            res[data_prod.id] = total_valsf
        return res
    
    def _amazon_browse_node_get(self):
        amazon_browse_node_obj = self.env['amazon.browse.node']
        amazon_browse_node_ids = amazon_browse_node_obj.search([], order='browse_node_name')
        amazon_browse_node = amazon_browse_node_obj.read(amazon_browse_node_ids, ['id','browse_node_name'])
        return [(node['browse_node_name'],node['browse_node_name']) for node in amazon_browse_node]

#    def _amazon_instance_get(self, cr, uid, context=None):
#        amazon_instance_obj = self.pool.get('amazon.instance')
#        amazon_instance_ids = amazon_instance_obj.search(cr, uid, [], order='name')
#        amazon_instances = amazon_instance_obj.read(cr, uid, amazon_instance_ids, ['id','name'], context=context)
#        return [(instance['id'],instance['name']) for instance in amazon_instances]

    ''' Assign by default one instance id to selection field on amazon instance '''
#    def _assign_default_amazon_instance(self, cr, uid, context=None):
#        amazon_instance_obj = self.pool.get('amazon.instance')
#        amazon_instance_ids = amazon_instance_obj.search(cr, uid, [], order='name')
#        amazon_instances = amazon_instance_obj.read(cr, uid, amazon_instance_ids, ['id','name'], context=context)
#        if amazon_instances:
#            return amazon_instances[0]['id']
#        else:
#            return False
    @api.multi
    def amazon_product_lookup(self):
        """
        Function to search product on amazon based on ListMatchingProduct Operation
        """
        amazon_instance_obj = self.env['amazon.instance']
        for prodcut_lookup in self:
            if not prodcut_lookup.amazon_instance_id:
                raise UserError('Warning !','Please select Amazon Instance and try again.')
            product_query = self.prod_query
            if not product_query:
                raise UserError('Warning !','Please enter Product Search Query and try again')
            product_query = product_query.strip().replace(' ','%')
            prod_query_contextid = self.prod_query_contextid
            productData = False
            try:
                productData = amazon_api_obj.call(amazon_instance_obj, 'ListMatchingProducts',product_query,prod_query_contextid)
                print('productData===--==-',productData)
            except Exception as e:
                raise UserError(_('Error !'),e)
            if productData:
                ### Flushing amazon.products.master data to show new search data ###
                delete_all_prods = self._cr.execute('delete from amazon_products_master where product_id=%s',(self[0].id,))
                for data in productData:
                    keys_val = data.keys()
                    prod_category = ''
                    if 'Binding' in keys_val:
                        prod_category = data['Binding']
                    prodvals = {
                            'name' : data['Title'],
                            'product_asin' : data['ASIN'],
                            'product_category' : prod_category,
                            'product_id' : self[0].id,
                            'amazon_product_attributes' : data
                        }
                    amazon_prod_master_obj = self.pool.get('amazon.products.master')
                    amazon_prod_master_id  = amazon_prod_master_obj.create(prodvals)
            else:
                     raise UserError(_('Warning !'),'No products found on Amazon as per your search query. Please try again')
        return True
    
#     @api.multi
#     def  export_amazon_product(self):
#         sale_shop_obj = self.env['sale.shop']
#         prod_obj = self.env['product.product']
#         shop_id=sale_shop_obj.search([('amazon_shop','=',True)])
#         print shop_id
#         instance_obj = sale_shop_obj.browse(shop_id[0]).amazon_instance_id
#         merchant_string = ''
#         standard_product_string = ''
#         if instance_obj:
#             merchant_string ="<MerchantIdentifier>%s</MerchantIdentifier>"%(instance_obj.aws_merchant_id)
#             release_date = datetime.datetime.now()
#             release_date = release_date.strftime("%Y-%m-%dT%H:%M:%S")
#             date_string = """<LaunchDate>%s</LaunchDate>
#                      <ReleaseDate>%s</ReleaseDate>"""%(release_date,release_date)
#             message_information = ''
#             message_id = 1
#             for product_data in self:
#                 item_type = product_data.amazon_product_category
#                 product_sku = product_data.default_code
#                 if product_data.name:
#                     title = product_data.name
# 
#                 if product_data.description_sale:
#                     sale_description = product_data.description_sale
#                     if sale_description:
#                         desc = "<Description><![CDATA[%s]]></Description>"%(sale_description)
#                 product_asin=product_data.asin
#                 if not product_asin:
#                     raise UserError(_('Error'), _('ASIN Required!!'))
#                 if product_data.ean13:
#                     standard_product_string = """
#                         <StandardProductID>
#                         <Type>EAN</Type>
#                         <Value>%s</Value>
#                         </StandardProductID>
#                         """%(product_data.ean13)
#                 elif product_data.upc:
#                     standard_product_string = """
#                     <StandardProductID>
#                     <Type>UPC</Type>
#                     <Value>%s</Value>
#                     </StandardProductID>
#                     """%(product_data.upc)
#                 else:
#                     standard_product_string = """
#                     <StandardProductID>
#                     <Type>ASIN</Type>
#                     <Value>%s</Value>
#                     </StandardProductID>
#                     """%(product_asin)
#                 platinum_keywords = ''
#                 if product_data.platinum_keywords:
#                     platinum_keyword_list = product_data.platinum_keywords.split('|')
#                     for keyword in platinum_keyword_list:
#                         platinum_keywords += '<PlatinumKeywords><![CDATA[%s]]></PlatinumKeywords>'%(keyword)
#                 if platinum_keywords == '':
#                     platinum_keywords = '<PlatinumKeywords>No Keywords</PlatinumKeywords>'
#                 search_term = ''
#                 if product_data.tag_ids:
#                     for search_tag in product_data.tag_ids:
#                         search_term += '<SearchTerms><![CDATA[%s]]></SearchTerms>' % (search_tag.name)
# 
#                 style_keywords = ''
#                 if product_data.style_keywords:
#                     style_keyword_list = product_data.style_keywords.split('|')
#                     for keyword_style in style_keyword_list:
#                             style_keywords += '<StyleKeywords><![CDATA[%s]]></StyleKeywords>'%(keyword_style)
#                 if style_keywords == '':
#                     style_keywords = '<StyleKeywords>No Keywords</StyleKeywords>'
# 
#                 message_information += """<Message><MessageID>%s</MessageID>
#                                             <OperationType>Update</OperationType>
#                                             <Product>
#                                             <SKU>%s</SKU>%s
#                                             <ProductTaxCode>A_GEN_NOTAX</ProductTaxCode>
#                                             %s<DescriptionData>
#                                             <Title><![CDATA[%s]]></Title>"""%(message_id,product_sku,standard_product_string,date_string,title)
# 
#                 if not product_data.product_id.bulletpoint_1:
#                     bullet_points ="""<BulletPoint><![CDATA[%s]]></BulletPoint>""" %product_data.product_id.bulletpoint_1
#                 else:
#                     bullet_points = '<BulletPoint>No Bullet points</BulletPoint>'
# 
# 
#                 if not product_data.product_id.bulletpoint_2:
#                     bullet_points +="""<BulletPoint><![CDATA[%s]]></BulletPoint>""" %product_data.product_id.bulletpoint_2
# 
#                 if not product_data.product_id.bulletpoint_3:
#                     bullet_points +="""<BulletPoint><![CDATA[%s]]></BulletPoint>""" %product_data.product_id.bulletpoint_3
# 
#                 if not product_data.product_id.bulletpoint_4:
#                     bullet_points +="""<BulletPoint><![CDATA[%s]]></BulletPoint>""" %product_data.product_id.bulletpoint_4
# 
#                 if not product_data.product_id.bulletpoint_5:
#                     bullet_points +="""<BulletPoint><![CDATA[%s]]></BulletPoint>""" %product_data.product_id.bulletpoint_5
# 
#                 if product_data.brand_name:
#                     message_information += """<Brand><![CDATA[%s]]></Brand>"""%(product_data.brand_name)
#                 message_information +="""<MSRP currency="EUR">10000</MSRP>"""
#                 if product_data.amazon_manufacturer:
#                     message_information +="""<Manufacturer><![CDATA[%s]]></Manufacturer>"""%(product_data.amazon_manufacturer)
#                 message_information +=""" <ItemType><![CDATA[%s]]></ItemType>
#                                                 </DescriptionData>
#                                                 <ProductData>
#                                                 <Lighting>
#                                                <ProductType>
#                                                 <LightsAndFixtures></LightsAndFixtures>
#                                                </ProductType>
#                                               </Lighting>
#                                               </ProductData>
#                                               """%(item_type)
#                 print "**********"
#                 message_information += """</Product>"""
# 
#                 prod_obj.write(product_data.id,{'amazon_export':True})
# 
#                 message_id = message_id + 1
#                 product_str = """<MessageType>Product</MessageType>
#                                 <PurgeAndReplace>false</PurgeAndReplace>"""
#                 product_data_xml = sale_shop_obj.xml_format(product_str,merchant_string,message_information)
#                 print "====",product_data_xml
# 
#                 if product_data_xml:
#                     product_submission_id = amazon_api_obj.call(instance_obj, 'POST_PRODUCT_DATA',product_data_xml)
#                     count = 0
#                     while ( len(product_submission_id) == 0 ):
#                         count = count + 1
#                         time.sleep(10)
#                         product_submission_id = amazon_api_obj.call(instance_obj, 'POST_PRODUCT_DATA',product_data_xml)
#                         if count >= 5:
#                             break
#         return True
    
    @api.multi
    def  export_amazon_product(self):
        sale_shop_obj = self.env['sale.shop']
        prod_obj = self.env['product.product']
        shop_id=sale_shop_obj.search([('amazon_shop','=',True)])
        print (shop_id)
        instance_obj = sale_shop_obj.browse(shop_id[0]).amazon_instance_id
        merchant_string = ''
        standard_product_string = ''
        if instance_obj:
            merchant_string ="<MerchantIdentifier>%s</MerchantIdentifier>"%(instance_obj.aws_merchant_id)
            release_date = datetime.datetime.now()
            release_date = release_date.strftime("%Y-%m-%dT%H:%M:%S")
            date_string = """<LaunchDate>%s</LaunchDate>
                     <ReleaseDate>%s</ReleaseDate>"""%(release_date,release_date)
            message_information = ''
            message_id = 1
            for product_data in self:
                item_type = product_data.amazon_product_category
                product_sku = product_data.default_code
                if product_data.name:
                    title = product_data.name

                if product_data.description_sale:
                    sale_description = product_data.description_sale
                    if sale_description:
                        desc = "<Description><![CDATA[%s]]></Description>"%(sale_description)
                product_asin=product_data.asin
                if not product_asin:
                    raise UserError(_('Error'), _('ASIN Required!!'))
                if product_data.ean13:
                    standard_product_string = """
                        <StandardProductID>
                        <Type>EAN</Type>
                        <Value>%s</Value>
                        </StandardProductID>
                        """%(product_data.ean13)
                elif product_data.upc:
                    standard_product_string = """
                    <StandardProductID>
                    <Type>UPC</Type>
                    <Value>%s</Value>
                    </StandardProductID>
                    """%(product_data.upc)
                else:
                    standard_product_string = """
                    <StandardProductID>
                    <Type>ASIN</Type>
                    <Value>%s</Value>
                    </StandardProductID>
                    """%(product_asin)
                platinum_keywords = ''
                if product_data.platinum_keywords:
                    platinum_keyword_list = product_data.platinum_keywords.split('|')
                    for keyword in platinum_keyword_list:
                        platinum_keywords += '<PlatinumKeywords><![CDATA[%s]]></PlatinumKeywords>'%(keyword)
                if platinum_keywords == '':
                    platinum_keywords = '<PlatinumKeywords>No Keywords</PlatinumKeywords>'
                search_term = ''
                if product_data.tag_ids:
                    for search_tag in product_data.tag_ids:
                        search_term += '<SearchTerms><![CDATA[%s]]></SearchTerms>' % (search_tag.name)

                style_keywords = ''
                if product_data.style_keywords:
                    style_keyword_list = product_data.style_keywords.split('|')
                    for keyword_style in style_keyword_list:
                            style_keywords += '<StyleKeywords><![CDATA[%s]]></StyleKeywords>'%(keyword_style)
                if style_keywords == '':
                    style_keywords = '<StyleKeywords>No Keywords</StyleKeywords>'

                message_information += """<Message><MessageID>%s</MessageID>
                                            <OperationType>Update</OperationType>
                                            <Product>
                                            <SKU>%s</SKU>%s
                                            <ProductTaxCode>A_GEN_NOTAX</ProductTaxCode>
                                            %s<DescriptionData>
                                            <Title><![CDATA[%s]]></Title>"""%(message_id,product_sku,standard_product_string,date_string,title)

                if not product_data.product_id.bulletpoint_1:
                    bullet_points ="""<BulletPoint><![CDATA[%s]]></BulletPoint>""" %product_data.product_id.bulletpoint_1
                else:
                    bullet_points = '<BulletPoint>No Bullet points</BulletPoint>'


                if not product_data.product_id.bulletpoint_2:
                    bullet_points +="""<BulletPoint><![CDATA[%s]]></BulletPoint>""" %product_data.product_id.bulletpoint_2

                if not product_data.product_id.bulletpoint_3:
                    bullet_points +="""<BulletPoint><![CDATA[%s]]></BulletPoint>""" %product_data.product_id.bulletpoint_3

                if not product_data.product_id.bulletpoint_4:
                    bullet_points +="""<BulletPoint><![CDATA[%s]]></BulletPoint>""" %product_data.product_id.bulletpoint_4

                if not product_data.product_id.bulletpoint_5:
                    bullet_points +="""<BulletPoint><![CDATA[%s]]></BulletPoint>""" %product_data.product_id.bulletpoint_5

                if product_data.brand_name:
                    message_information += """<Brand><![CDATA[%s]]></Brand>"""%(product_data.brand_name)
                message_information +="""<MSRP currency="EUR">10000</MSRP>"""
                if product_data.amazon_manufacturer:
                    message_information +="""<Manufacturer><![CDATA[%s]]></Manufacturer>"""%(product_data.amazon_manufacturer)
                message_information +=""" <ItemType><![CDATA[%s]]></ItemType>
                                                </DescriptionData>
                                                <ProductData>
                                                <Lighting>
                                               <ProductType>
                                                <LightsAndFixtures></LightsAndFixtures>
                                               </ProductType>
                                              </Lighting>
                                              </ProductData>
                                              """%(item_type)
                print ("**********")
                message_information += """</Product>"""

                prod_obj.write(product_data.id,{'amazon_export':True})

                message_id = message_id + 1
                product_str = """<MessageType>Product</MessageType>
                                <PurgeAndReplace>false</PurgeAndReplace>"""
                product_data_xml = sale_shop_obj.xml_format(product_str,merchant_string,message_information)
                print( "==>>>>>product_data_xml>>>>>==",product_data_xml)

                if product_data_xml:
                    product_submission_id = amazon_api_obj.call(instance_obj, 'POST_PRODUCT_DATA',product_data_xml)
                    count = 0
                    while ( len(product_submission_id) == 0 ):
                        count = count + 1
                        time.sleep(10)
                        product_submission_id = amazon_api_obj.call(instance_obj, 'POST_PRODUCT_DATA',product_data_xml)
                        if count >= 5:
                            break
        return True
    
    
    @api.multi
    def export_image(self):
        message_count=1
        sale_shop_obj=self.env['sale.shop']
        image_obj = self.env['product.images']
        shop_id=sale_shop_obj.search([('amazon_shop','=',True)])
        instance_obj = sale_shop_obj.browse(shop_id[0]).amazon_instance_id
        xml_information=''
        xml_information+="""<?xml version="1.0" encoding="utf-8"?>
                        <AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">
                        <Header>
                            <DocumentVersion>1.01</DocumentVersion>
                            <MerchantIdentifier>%s</MerchantIdentifier>
                        </Header>
                    <MessageType>ProductImage</MessageType>
                    """%(instance_obj.aws_merchant_id)
        image_location=''
        for product_data in self:
            SKU=product_data.default_code
            if not product_data.product_id.name:
                raise UserError(_('Error'), _('Please enter Product SKU for Image Feed "%s"'% (product_data.name)))
            for imagedata in product_data.image_ids:
                image_location=imagedata.url
                parent_sku=product_data.default_code
                if not image_location:
                    raise UserError(_('Error'), _('Image location not found for this product"%s"'% (product_data.name)))
                xml_information += """<Message>
                                        <MessageID>%s</MessageID>
                                        <OperationType>Update</OperationType>
                                            <ProductImage>
                                                <SKU>%s</SKU>
                                                <ImageType>Main</ImageType>
                                                <ImageLocation>%s</ImageLocation>
                                                </ProductImage></Message>
                                         """%(message_count,parent_sku,image_location)
                message_count+=1
        xml_information +="""</AmazonEnvelope>"""

        product_submission_id = amazon_api_obj.call(instance_obj, 'POST_PRODUCT_IMAGE_DATA',xml_information)
        if product_submission_id.get('FeedSubmissionId',False):
            time.sleep(10)
            submission_results = amazon_api_obj.call(instance_obj, 'GetFeedSubmissionResult',product_submission_id.get('FeedSubmissionId',False))
            return True



    def export_inventory(self):
        xml_data=""
        sale_shop_obj = self.env['sale.shop']

        shop_ids = sale_shop_obj.search([('amazon_shop','=',True)])
        amazon_inst_data = shop_ids[0].amazon_instance_id
        message_count = 1

        merchant_string ="<MerchantIdentifier>%s</MerchantIdentifier>"%(amazon_inst_data.aws_merchant_id)
        message_type = '<MessageType>Inventory</MessageType>'
        for product in self:
            if not product.name:
                raise shop_ids(_('Error'), _('Please enter Product SKU for Image Feed "%s"'% (product.name)))

            parent_sku= product.default_code
            inventory = product.bom_stock
            lead_time = product.sale_delay
            #WE MAY WANT TO IMPLEMENT LATER
            #if product.fulfillment_by != 'AFN':
            update_xml_data = '''<SKU>%s</SKU>
                                <Quantity>%s</Quantity><FulfillmentLatency>%s</FulfillmentLatency>'''%(parent_sku,inventory,lead_time)
            xml_data += '''<Message>
                        <MessageID>%s</MessageID><OperationType>Update</OperationType>
                        <Inventory>%s</Inventory></Message>
                    '''% (message_count,update_xml_data)

    #Uploading Product Inventory Feed
            message_count+=1
        str = """
                <?xml version="1.0" encoding="utf-8"?>
                <AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">
                <Header>
                <DocumentVersion>1.01</DocumentVersion>
                """+merchant_string+"""
                </Header>
                """+message_type+xml_data+"""
                """
        str +="""</AmazonEnvelope>"""

        logger.info('                        API STRING:         %s                ',str)
        product_submission_id = amazon_api_obj.call(amazon_inst_data, 'POST_INVENTORY_AVAILABILITY_DATA',str)
        if product_submission_id.get('FeedSubmissionId',False):
            logger.info('Feed Submission ID: %s',product_submission_id.get('FeedSubmissionId'))
            time.sleep(20)
            submission_results = amazon_api_obj.call(amazon_inst_data, 'GetFeedSubmissionResult',product_submission_id.get('FeedSubmissionId',False))
            logger.info('                       SUBMISSION RESULTS        %s                ',submission_results)
        return True
 


    @api.multi
    def export_pricing(self):
#Form Parent XML
        str=''
        sale_shop_obj = self.env['sale.shop']
        company_obj = self.env['res.company']
        shop_ids = sale_shop_obj.search([('amazon_shop','=',True)])
        amazon_inst_data = shop_ids.amazon_instance_id
        message_count = 1
        merchant_string ="<MerchantIdentifier>%s</MerchantIdentifier>"%(amazon_inst_data.aws_merchant_id)
        message_type = '<MessageType>Price</MessageType>'

        res_company_id=company_obj.search([('name','=','Stockton International')])
        if res_company_id:
            currency=res_company_id.currency_id.name
        start_date = datetime.datetime.now()
        start_date = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
#Form Child XML
        parent_xml_data = ''
        for product_data in self:
            if not product_data.name:
                raise UserError(_('Error'), _('Please enter Product SKU for "%s"'% (product_data.name)))
            parent_sku = product_data.default_code
            
#if the product has a new price set it to the current before listing
            if product_data.amazon_price_new:
                product_data.write({'price_amazon_current' : float(product_data.amazon_price_new),'amazon_price_new':False})
            else:
                continue
            cost_final=product_data.price_amazon_current
            parent_xml_data += '''<Message><MessageID>%s</MessageID>
                                <Price>
                                <SKU>%s</SKU>
                                <StandardPrice currency="%s">%s</StandardPrice>
                                </Price></Message>
                            '''% (message_count,parent_sku,currency,cost_final)
            message_count = message_count + 1
        str += """
                <?xml version="1.0" encoding="utf-8"?>
                <AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">
                <Header>
                <DocumentVersion>1.01</DocumentVersion>
                """+merchant_string+"""
                </Header>
                """+message_type+parent_xml_data+"""
                """
        str +="""</AmazonEnvelope>"""
        product_submission_id = amazon_api_obj.call(amazon_inst_data, 'POST_PRODUCT_PRICING_DATA',str)
        if product_submission_id.get('FeedSubmissionId',False):
            time.sleep(10)
            submission_results = amazon_api_obj.call(amazon_inst_data, 'GetFeedSubmissionResult',product_submission_id.get('FeedSubmissionId',False))
            
        return True
    
    @api.multi
    def get_lowest_price_asin(self):
        shop_obj = self.env['sale.shop']
        shop_ids = shop_obj.search([('amazon_shop','=',True)])
        instance_obj = shop_ids.amazon_instance_id
        n = 0
        for product_data in self:
            n += 1
            if n % 10 == 0:
                time.sleep(1)
            if product_data.asin:
                results = amazon_api_obj.call(instance_obj, 'GetLowestOfferListingsForASIN', product_data.asin)
                if results != None:
                    return float(results.get('lowestamount'))
                else:
                    return False
            else:
                raise UserError(('Error'),('Asin is not available for this product'))
        return False
    
    @api.multi
    def price_compute(self, price_type, uom=False, currency=False, company=False):
        # TDE FIXME: delegate to template or not ? fields are reencoded here ...
        # compatibility about context keys used a bit everywhere in the code
        if not uom and self._context.get('uom'):
            uom = self.env['product.uom'].browse(self._context['uom'])
        if not currency and self._context.get('currency'):
            currency = self.env['res.currency'].browse(self._context['currency'])

        templates = self
        if price_type == 'standard_price':
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            templates = self.with_context(force_company=company and company.id or self._context.get('force_company', self.env.user.company_id.id)).sudo()

        prices = dict.fromkeys(self.ids, 0.0)
        for template in templates:
            if price_type=='amazon_standard_price':
                prices[template.id] = template['tem_standard_price'] or 0.0
            else:
                prices[template.id] = template[price_type] or 0.0

            if uom:
                prices[template.id] = template.uom_id._compute_price(prices[template.id], uom)

            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                prices[template.id] = template.currency_id.compute(prices[template.id], currency)

        return prices

    is_prime = fields.Boolean('Is Prime')
    fulfillment_by = fields.Selection([('MFN','Fulfilled by Merchant(MFN)'),('FBA','Fulfilled by Amazon(FBA)')],'Fulfillment By')
    style_keywords = fields.Text(string='Style Keywords')
    platinum_keywords = fields.Text(string='Platinum Keywords')
    orderitemid = fields.Char(string='Orderitemid', size=16)
    product_order_item_id = fields.Char(string='Order_item_id', size=256)
    amazon_export = fields.Boolean(string='To be Exported')
    amazon_response = fields.Boolean(string='Amazon response')
    amazon_category = fields.Many2one('product.category',string='Amazon Category')
    amazon_product_category = fields.Char(string='Amazon Category',size=64)
    brand_name = fields.Char(string='Brand',size=64)
    amazon_manufacturer = fields.Char(string='Manufacturer',size=64)
    amazon_updated_price = fields.Float(string='Amazon Updated Price',digits=(16,2))
    amazon_price = fields.Float(string='Amazon Price',digits=(16,2))
    tem_standard_price = fields.Float('Amazon Price')
    upc_temp = fields.Char(string='UPC',size=64)
    ean_barcode = fields.Char('EAN/Barcode')
    isbn_temp = fields.Char('ISBN')
    product_group = fields.Char(string='Product Group',size=64)
    amazon_title = fields.Char(string='Amazon title',size=64)
    amazon_lowest_listing_price = fields.Float(string='Lowest Listing Price')
    bom_stock_list = fields.Float(string='Bom Stock')
    amazon_product = fields.Boolean(string='Amazon Product')
    item_price = fields.Float(string='Item Price')
    item_tax = fields.Float(string='Item taxes')
    shipping_price = fields.Float(string='Shipping price')
    taxes = fields.Float(string='taxes')
    gift_costs = fields.Float(string='gift costs')
    product_group = fields.Char(string='ProductGroup')
    package_dimension_length = fields.Float(string='PackageDimensionsLength')
    label = fields.Char(string='Label')
    product_type_name = fields.Char(string='ProductTypeName')
    small_image_height = fields.Integer(string='SmallImageHeight')
    package_quantity = fields.Integer(string='PackageQuantity')
    item_dimension_weight = fields.Float(string='ItemDimensionsWeight')
    brand = fields.Char(string='Brand')
    studio = fields.Char(string='Studio')
    manufacturer_part = fields.Char(string='Manufacturer Part Number')
    publisher = fields.Char(string='Publisher')
    package_dimension_width = fields.Float(string='PackageDimensionsWidth')
    package_dimension_weight = fields.Float(string='PackageDimensionsWeight')
    color = fields.Char(string='Color')
    package_dimension_height = fields.Float(string='PackageDimensionsHeight')
    small_image_url = fields.Char(string='SmallImageURL')
    binding = fields.Char(string='Bindings')
    small_image_width = fields.Float(string='SmallImageWidth')
    feature = fields.Text(string='Features')
    updated_data = fields.Boolean(string='Updated', default=False)
    amazon_sku = fields.Char(string='ASIN')
#     sale_start_date = fields.Datetime('Sale Start Date')
#     sale_end_date = fields.Datetime('Sale End Date')
    
    variationtheme = fields.Selection([("Size-Color",'Size-Color'),('Color','Color'),('Size','Size')], string='Select VariationTheme')
    tmp_asin = fields.Char('ASIN')
    bullet_point = fields.One2many('bullet.point','template_id' ,string='Bullet Point')
    search_keywords = fields.One2many('search.terms','searchterm_temp_id',string='SearchTerms Keywords', help="Data should be amazon categories name like Shoes")
    item_type = fields.Char(string='Item Type', help="Data Should be in this Format casual-formal")
    standard_temp_product = fields.Selection([('EAN','EAN'),('UPC','UPC'),('ASIN','ASIN'),('ISBN','ISBN')], string='Standard Product')
    amazon_fba_sku = fields.Char(string='Amazon FBA SKU')


class BulletPoint(models.Model):
    _name="bullet.point"
    
    bullet = fields.Char('Bullet Point')
    template_id = fields.Many2one('product.template', string="Bullet template")
    
class SearchTerms(models.Model):
    _name="search.terms"
    
    searchterm = fields.Char('Search Term')
    searchterm_temp_id = fields.Many2one('product.template', string="SearchTerm template")
    
# class ItemType(models.Model):
#     _name="item.types"
#     
#     itemtype = fields.Char('Item Type')
#     itemtype_temp_id = fields.Many2one('product.template', string="ItemType template")
    
class OuterMaterial(models.Model):
    _name="outer.material"
    
    material_type = fields.Char('Item Type')
    material_temp_id = fields.Many2one('product.product', string="Material template")

class ProductProduct(models.Model):
    _inherit='product.product'
    
    @api.multi
    def _get_amazon_product_model_count(self):
        market_p_ids = []
        for market in self:
            market_p_ids = self.env['amazon.log'].search([('res_model_id.model', '=', 'product.product'),('res_id','=',self[0].id)])
            market.amazon_product_model_count = len(market_p_ids)
    
    @api.multi
    def action_view_amazon_log(self):
        amazon_log = []
        amazon_log_ids = self.env['amazon.log'].search([('res_model_id.model', '=', 'product.product'),('res_id','=',self[0].id)])
        print( "amazon_logprooduct", amazon_log_ids)
        if amazon_log_ids:
            amazon_log_ids = list(amazon_log_ids._ids)
            print ("=========amazon_log_ids=============", amazon_log_ids)
        imd = self.env['ir.model.data']
        list_view_id = imd.xmlid_to_res_id('amazon_connector.view_amazon_log_tree')
        form_view_id = imd.xmlid_to_res_id('amazon_connector.view_amazon_log_form')
        result = {
                "type": "ir.actions.act_window",
                "res_model": "amazon.log",
                "views": [[list_view_id, "tree"], [form_view_id, "form"]],
                "domain": [["id", "in", amazon_log_ids]],
                "context":{'group_by':['marketplace_id', 'log_type', 'name']}
        }
        if len(amazon_log_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = amazon_log_ids[0]
        return result
    
    @api.multi
    def _get_prices(self):
        for rec in self:
            rec.product_shop_price_ids = [(0,0, {'shop_id': 1, 'price': 300})]

    amazon_prodlisting_ids = fields.One2many('amazon.product.listing', 'product_id', string='Product Listing')
    asin = fields.Char('Asin',size=64)
    upc = fields.Char('UPC')
    isbn = fields.Char('ISBN')
    manufacturer_part = fields.Char(string='Manufacturer Part Number')
    amazon_active_prod = fields.Boolean('Amazon Product')
    qty_override = fields.Float('Quantity Override')
    amazon_price_new = fields.Float('Amazon New Price')
    price_amazon_current = fields.Float('Amazon Current Price')
    updated_data = fields.Boolean('Updated', default=False)
    amazon_standard_price = fields.Float('Amazon Price')
    amazon_fba_price = fields.Float('Amazon FBA Price')
    # For Log
    amazon_product_model_count = fields.Integer(string='Amazon Log View', compute=_get_amazon_product_model_count)
    product_shop_price_ids = fields.One2many('product.shop.price', 'product_id', string="Prices", compute="_get_prices")
#     standard_product = fields.Selection([('EAN','EAN'),('UPC','UPC'),('ASIN','ASIN'),('ISBN','ISBN')], string='Standard Product')
    shipping_weight = fields.Char('Shipping Weight')
    shipping_weight_uom = fields.Selection([('LB','LB'),('OZ','OZ'),('KG','KG'),('GR','GR')],string='Shipping weight uom')
    style_name = fields.Char(string='Style Name')
    material_type = fields.Char(string='Material Type')
    amazon_afn_sku = fields.Char(string='Amazon AFN SKU')
    fulfillment_channel = fields.Selection([('MFN','Fulfilled by Merchant(MFN)'),('FBA','Fulfilled by Amazon(FBA)')],'Fulfillment By')
#     material_type = fields.One2many('outer.material','material_temp_id',string='Material Type')

    @api.multi
    def ExportVarients(self,products,instance,message_id):
#         print"message_id"
        message_information = ''
        for product in products:
            merchant_string = ''
            standard_product_string = ''
            merchant_string ="<MerchantIdentifier>%s</MerchantIdentifier>"%(instance.amazon_instance_id.aws_merchant_id)
            message_id = message_id+1
            product_sku = product.default_code
            if product.name:
                title = product.name
            product_str = """<MessageType>Product</MessageType>
                            <PurgeAndReplace>false</PurgeAndReplace>"""
            if product.description_sale:
                sale_description = product.description_sale
                if sale_description:
                    desc = "<Description><![CDATA[%s]]></Description>"%(sale_description)
#             if not product.asin:
#                 raise UserError(_('Error'), _('ASIN or EAN Required!!'))
            if product.ean_barcode:
                standard_product_string = """
                    <StandardProductID>
                    <Type>EAN</Type>
                    <Value>%s</Value>
                    </StandardProductID>
                    """%(product.ean_barcode)
            elif product.upc:
                standard_product_string = """
                <StandardProductID>
                <Type>UPC</Type>
                <Value>%s</Value>
                </StandardProductID>
                """%(product.upc)
            elif product.isbn:
                standard_product_string = """
                <StandardProductID>
                <Type>ISBN</Type>
                <Value>%s</Value>
                </StandardProductID>
                """%(product.isbn)
            else:
                standard_product_string = """
                <StandardProductID>
                <Type>ASIN</Type>
                <Value>%s</Value>
                </StandardProductID>
                """%(product.asin)
            message_information += """<Message><MessageID>%s</MessageID>
                                        <OperationType>Update</OperationType>
                                        <Product>
                                        <SKU>%s</SKU>%s
                                        <DescriptionData>
                                        <Title><![CDATA[%s]]></Title>"""%(message_id,product_sku,standard_product_string,title)
            if product.brand_name:
                message_information += """<Brand><![CDATA[%s]]></Brand>"""%(product.brand_name)
#             message_information +="""<MSRP currency="EUR">10000</MSRP>"""
            if product.description_sale:
                message_information += """<Description><![CDATA[%s]]></Description>"""%(product.description_sale)
            if product.shipping_weight:
                message_information += '<ShippingWeight unitOfMeasure="%s">%s</ShippingWeight>'%(product.shipping_weight_uom, product.shipping_weight)
            if product.amazon_manufacturer:
                message_information +="""<Manufacturer><![CDATA[%s]]></Manufacturer>"""%(product.amazon_manufacturer)
            if product.manufacturer_part:
                message_information +="""<MfrPartNumber><![CDATA[%s]]></MfrPartNumber>"""%(product.manufacturer_part)
            if product.amazon_categ_id:
                message_information += """<RecommendedBrowseNode>%s</RecommendedBrowseNode>""" %(product.amazon_categ_id.amazon_cat_id)
            if product.attribute_value_ids:
                variationtheme = ''
                tag = ''
                size = False
                color = False
                size_color = ''
                if product.variationtheme=='Size-Color':
                    for variation in product.attribute_value_ids:
                        if variation.attribute_id.name.lower()=='size':
                            size = variation.name
                        elif variation.attribute_id.name.lower()=='color':
                            color = variation.name
                    size_color += """<Size>%s</Size>
                                    <Color>%s</Color>"""%(size,color)
                elif product.variationtheme=='SizeColor':
                    for variation in product.attribute_value_ids:
                        if variation.attribute_id.name.lower()=='size':
                            size = variation.name
                        elif variation.attribute_id.name.lower()=='color':
                            color = variation.name
                    size_color += """<Size>%s</Size>
                                    <Color>%s</Color>"""%(size,color)
                                    
                elif product.variationtheme=='ColorSize':
                    for variation in product.attribute_value_ids:
                        if variation.attribute_id.name.lower()=='size':
                            size = variation.name
                        elif variation.attribute_id.name.lower()=='color':
                            color = variation.name
                    size_color += """<Color>%s</Color>
                                    <Size>%s</Size>
                                    """%(color,size)
                                    
                elif product.variationtheme=='Size':
                    for variation in product.attribute_value_ids:
                        if variation.attribute_id.name.lower()=='size':
                            size = variation.name
                    size_color += """<Size>%s</Size>"""%(size)
                            
                elif product.variationtheme=='Color':
                    for variation in product.attribute_value_ids:
                        if variation.attribute_id.name.lower()=='color':
                            color = variation.name
                    size_color += """<Color>%s</Color>"""%(color)
#                     if variationtheme:
#                         variationtheme = variationtheme+'-'+variation.attribute_id.name
#                     else:
#                         variationtheme = variation.attribute_id.name
                
#                 if tag:
#                     tag=tag+'\n<'+variation.attribute_id.name + '>' + variation.name + '</'+variation.attribute_id.name + '>'
#                 else:
#                     tag='<'+variation.attribute_id.name + '>' + variation.name + '</'+variation.attribute_id.name + '>'
            message_information +="""</DescriptionData>
                                            <ProductData>
                                            <Home>
                                            <Parentage>child</Parentage>
                                            <VariationData>
                                                <VariationTheme>%s</VariationTheme>%s
                                            </VariationData>
                                            <Material>%s</Material>
                                            </Home>
                                          </ProductData>
                                          """%(product.variationtheme,size_color,product.material_type)
            message_information += """</Product>
                                        </Message>"""
#         logger.info("message_information%s"%(message_information))
#         print"message_informationmessage_information",message_information
        return message_information

    @api.multi
    def RelateVarients(self,products,instance,template):
            str=''
            merchant_string ="<MerchantIdentifier>%s</MerchantIdentifier>"%(instance.amazon_instance_id.aws_merchant_id)
            message_information = ''
            message_id = 1
            message_information += """<MessageType>Relationship</MessageType>
                                        <Message>
                                        <MessageID>%s</MessageID>
                                        <OperationType>Update</OperationType>
                                        <Relationship>
                                        <ParentSKU>%s</ParentSKU>
                                        """%(message_id,template.amazon_sku)
            for product in products:
                message_information += """<Relation>
                                    <SKU>%s</SKU>
                                    <Type>Variation</Type>
                                    </Relation>
                                    """%(product.default_code)
                                    
            message_information += """</Relationship>
                                    </Message>"""
                                    
            str = """
                <?xml version="1.0" encoding="utf-8" ?>
<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amznenvelope.xsd">
<Header>
<DocumentVersion>1.01</DocumentVersion>
                """+merchant_string+"""
                </Header>
                """+message_information+"""
                """
            str +="""</AmazonEnvelope>"""
            print("str",str)
            if str:
                relation_submission_id = amazon_api_obj.call(instance, 'POST_PRODUCT_RELATIONSHIP_DATA',str)
                print("relation_submission_id",relation_submission_id)
#             relation_data_xml = instance.xml_format(merchant_string, message_information)
#             print"relation_data_xmlrelation_data_xml",relation_data_xml


    @api.multi
    def StandardSalePrice(self,products,instance,template):
        str=''
        merchant_string ="<MerchantIdentifier>%s</MerchantIdentifier>"%(instance.amazon_instance_id.aws_merchant_id)
        message_information = ''
        message_id = False
        message_information += """<MessageType>Price</MessageType>
                                """
        for product in products:
            message_id = message_id +1
            offer = ''
            if self.env.context.get('price_list_id'):
                product_rule = self.env.context.get('price_list_id')._compute_price_rule([(product, 1, False)])
            else:
                product_rule = instance.pricelist_id._compute_price_rule([(product, 1, False)])
                
            itemprice = False    
            item_date = self.env['product.pricelist.item'].browse(product_rule.get(product.id)[1])
            print("item_date",item_date)
            if item_date:
                start_date = (item_date.date_start)
                if start_date:
                    start_date = datetime.strptime(start_date,'%Y-%m-%d') 
                    start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S.00Z")
                    print("start_date",start_date)
                end_date = (item_date.date_end)
                if end_date:
                    end_date = datetime.strptime(end_date,'%Y-%m-%d') 
                    end_date = end_date.strftime("%Y-%m-%dT%H:%M:%S.00Z")
                itemprice = product_rule.get(product.id)[0]
                print("itemprice",itemprice)
            message_information += """<Message>
                                    <MessageID>%s</MessageID>
                                    <Price>
                                    <SKU>%s</SKU>
                                    <StandardPrice currency="%s">%s</StandardPrice>
                                """%(message_id, product.default_code,instance.res_currency.name, product.amazon_standard_price)

            if itemprice!=0.0 and itemprice < product.amazon_standard_price:
                offer = """<Sale>
                            <StartDate>%s</StartDate>
                            <EndDate>%s</EndDate>
                             <SalePrice currency="%s">%s</SalePrice>
                            </Sale>"""%(start_date,end_date,instance.res_currency.name, itemprice)
                print("offer",offer)
            if offer:
                message_information += """%s"""%(offer)
            message_information += """</Price>
                                    </Message>"""
                                
        if template:
            message_id = message_id +1
            offer = ''
            if self.env.context.get('price_list_id'):
                product_rule = self.env.context.get('price_list_id')._compute_price_rule([(template, 1, False)])
            else:
                product_rule = instance.pricelist_id._compute_price_rule([(template, 1, False)])
                
            item_date = self.env['product.pricelist.item'].browse(product_rule.get(template.id)[1])
            print("item_date",item_date)
            itemprice = False
            if item_date:
                start_date = item_date.date_start
                print("start_date",start_date)
                if start_date:
                    start_date = datetime.strptime(start_date,'%Y-%m-%d') 
                    start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S.00Z")
                    print("start_date",start_date)
                end_date = (item_date.date_end)
                if end_date:
                    end_date = datetime.strptime(end_date,'%Y-%m-%d') 
                    end_date = end_date.strftime("%Y-%m-%dT%H:%M:%S.00Z")
                itemprice = product_rule.get(template.id)[0]
                print("itemprice",itemprice)
            message_information += """<Message>
                                    <MessageID>%s</MessageID>
                                    <Price>
                                    <SKU>%s</SKU>
                                    <StandardPrice currency="%s">%s</StandardPrice>"""%(message_id, template.amazon_sku,instance.res_currency.name,template.tem_standard_price)
            if itemprice!=0.0 and itemprice < template.tem_standard_price:
                offer = """<Sale>
                            <StartDate>%s</StartDate>
                            <EndDate>%s</EndDate>
                             <SalePrice currency="%s">%s</SalePrice>
                            </Sale>"""%(start_date,end_date,instance.res_currency.name, itemprice)
                print("offer",) 
            if offer:
                message_information += """%s"""%(offer)
            message_information += """</Price>
                                </Message>
                                """
                                
        str = """<?xml version="1.0" encoding="utf-8" ?>
<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amznenvelope.xsd">
<Header>
<DocumentVersion>1.01</DocumentVersion>"""+merchant_string+"""
            </Header>
            """+message_information+"""
            """
        str +="""</AmazonEnvelope>"""
        print("str",str)
        if str:
            relation_submission_id = amazon_api_obj.call(instance, 'POST_PRODUCT_PRICING_DATA',str)
            print("price_submission_id",relation_submission_id)
            
 
            
    @api.multi
    def UpdateAmazonInventory(self,products,instance,template):
        str=''
        merchant_string ="<MerchantIdentifier>%s</MerchantIdentifier>"%(instance.amazon_instance_id.aws_merchant_id)
        message_information = ''
        message_id = False
        message_information += """<MessageType>Inventory</MessageType>
                                    """
        for product in products:
            message_id = message_id +1
            message_information += """<Message>
                                    <MessageID>%s</MessageID>
                                    <OperationType>Update</OperationType>
                                    <Inventory>
                                    <SKU>%s</SKU>"""%(message_id, product.default_code)
            if product.qty_available >0:
                quantity = int(product.qty_available)
                print("quantity",quantity)
                message_information += """<Quantity>%s</Quantity>"""%(quantity)
                                
            message_information += """<FulfillmentLatency>1</FulfillmentLatency> 
                                    </Inventory>
                                    </Message>"""
                                
        if template:
            message_id = message_id +1
            message_information += """<Message>
                                    <MessageID>%s</MessageID>
                                    <OperationType>Update</OperationType>
                                    <Inventory>
                                    <SKU>%s</SKU>"""%(message_id, template.amazon_sku)
            if template.qty_available >0:
                quantity = int(template.qty_available)
                print("quantity",quantity)
                message_information += """<Quantity>%s</Quantity>"""%(quantity)
                                
            message_information += """<FulfillmentLatency>1</FulfillmentLatency> 
                                    </Inventory>
                                    </Message>"""
                                
        str = """<?xml version="1.0" encoding="utf-8" ?>
<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amznenvelope.xsd">
<Header>
<DocumentVersion>1.01</DocumentVersion>"""+merchant_string+"""
            </Header>
            """+message_information+"""
            """
        str +="""</AmazonEnvelope>"""
        print("str",str)
        if str:
            relation_submission_id = amazon_api_obj.call(instance, 'POST_INVENTORY_AVAILABILITY_DATA',str)
            print("inventory_submission_id",relation_submission_id)
            
            

    @api.multi
    def UpdateAmazonImages(self,products,instance,template):
        str=''
        print("products",products)
        merchant_string ="<MerchantIdentifier>%s</MerchantIdentifier>"%(instance.amazon_instance_id.aws_merchant_id)
        message_information = ''
        message_id = False
        message_information += """<MessageType>ProductImage</MessageType>"""
        
        for product in products:
            image_count= False
            for image in product.image_ids:
                message_id = message_id +1
                image_count = image_count+1
                if image_count==1:
                    imagetype = """<ImageType>Main</ImageType>"""
                elif image_count==2:  
                     imagetype = """<ImageType>PT1</ImageType>"""
                elif image_count==3:  
                     imagetype = """<ImageType>PT2</ImageType>"""
                elif image_count==4:  
                     imagetype = """<ImageType>PT3</ImageType>"""
                elif image_count==5:  
                     imagetype = """<ImageType>PT4</ImageType>"""
                elif image_count==6:  
                     imagetype = """<ImageType>PT5</ImageType>"""
                elif image_count==7:  
                     imagetype = """<ImageType>PT6</ImageType>"""
                else:  
                     imagetype = """<ImageType>PT7</ImageType>"""
                message_information += """<Message>
                                <MessageID>%s</MessageID>
                                <OperationType>Update</OperationType>
                                <ProductImage>
                                <SKU>%s</SKU>%s
                                <ImageLocation>%s</ImageLocation>
                                </ProductImage>
                                </Message>"""%(message_id, product.default_code,imagetype,image.url)
                                
        if not products:
            product = self.env['product.product'].search([('product_tmpl_id','=',template.id)])
            if product:
                image_count= False
                for iamge in product.image_ids:
                    message_id = message_id +1
                    image_count = image_count+1
                    if image_count==1:
                        imagetype = """<ImageType>Main</ImageType>"""
                    elif image_count==2:  
                         imagetype = """<ImageType>PT1</ImageType>"""
                    elif image_count==3:  
                         imagetype = """<ImageType>PT2</ImageType>"""
                    elif image_count==4:  
                         imagetype = """<ImageType>PT3</ImageType>"""
                    elif image_count==5:  
                         imagetype = """<ImageType>PT4</ImageType>"""
                    elif image_count==6:  
                         imagetype = """<ImageType>PT5</ImageType>"""
                    else:  
                        imagetype = """<ImageType>PT6</ImageType>"""
                    message_information += """<Message>
                                        <MessageID>%s</MessageID>
                                        <OperationType>Update</OperationType>
                                        <ProductImage>
                                        <SKU>%s</SKU>%s
                                        <ImageLocation>%s</ImageLocation>
                                        </ProductImage>
                                        </Message>"""%(message_id, product.amazon_sku,imagetype,iamge.url)
                                
        str = """<?xml version="1.0" encoding="utf-8" ?>
<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amznenvelope.xsd">
<Header>
<DocumentVersion>1.01</DocumentVersion>"""+merchant_string+"""
            </Header>
            """+message_information+"""
            """
        str +="""</AmazonEnvelope>"""
        print("str",str)
        if str:
            image_submission_id = amazon_api_obj.call(instance, 'POST_PRODUCT_IMAGE_DATA',str)
            print("image_submission_id",image_submission_id)
        

    @api.multi
    def price_compute(self, price_type, uom=False, currency=False, company=False):
        # TDE FIXME: delegate to template or not ? fields are reencoded here ...
        # compatibility about context keys used a bit everywhere in the code
        if not uom and self._context.get('uom'):
            uom = self.env['product.uom'].browse(self._context['uom'])
        if not currency and self._context.get('currency'):
            currency = self.env['res.currency'].browse(self._context['currency'])
 
        products = self
        print("product",products)
        if price_type == 'standard_price':
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            products = self.with_context(force_company=company and company.id or self._context.get('force_company', self.env.user.company_id.id)).sudo()
 
        prices = dict.fromkeys(self.ids, 0.0)
        for product in products:
            prices[product.id] = product[price_type] or 0.0
            print("prices[product.id]",prices[product.id])
            if price_type == 'list_price':
                prices[product.id] += product.price_extra
            if price_type == 'amazon_standard_price':
                print("price_type",price_type)
                if not product.attribute_value_ids:
                    print("product.attribute_value_ids",product.attribute_value_ids)
                    prices[product.id] = product.tem_standard_price
 
            if uom:
                prices[product.id] = product.uom_id._compute_price(prices[product.id], uom)
 
            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                prices[product.id] = product.currency_id.compute(prices[product.id], currency)
 
        return prices
    
    
#     @api.multi
#     def name_get(self):
#         # TDE: this could be cleaned a bit I think
# 
#         def _name_get(d):
#             name = d.get('name', '')
#             code = self._context.get('display_default_code', False) and d.get('default_code', False) or False
#             if code:
#                 name = '%s' % (code,name)
#             return (d['id'], name)
# 
#         partner_id = self._context.get('partner_id')
#         if partner_id:
#             partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
#         else:
#             partner_ids = []
# 
#         # all user don't have access to seller and partner
#         # check access and use superuser
#         self.check_access_rights("read")
#         self.check_access_rule("read")
# 
#         result = []
#         for product in self.sudo():
#             # display only the attributes with multiple possible values on the template
#             variable_attributes = product.attribute_line_ids.filtered(lambda l: len(l.value_ids) > 1).mapped('attribute_id')
#             variant = product.attribute_value_ids._variant_name(variable_attributes)
# 
#             name = variant and "%s (%s)" % (product.name, variant) or product.name
#             sellers = []
#             if partner_ids:
#                 sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and (x.product_id == product)]
#                 if not sellers:
#                     sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and not x.product_id]
#             if sellers:
#                 for s in sellers:
#                     seller_variant = s.product_name and (
#                         variant and "%s (%s)" % (s.product_name, variant) or s.product_name
#                         ) or False
#                     mydict = {
#                               'id': product.id,
#                               'name': seller_variant or name,
#                               'default_code': s.product_code or product.default_code,
#                               }
#                     temp = _name_get(mydict)
#                     if temp not in result:
#                         result.append(temp)
#             else:
#                 mydict = {
#                           'id': product.id,
#                           'name': name,
#                           'default_code': product.default_code,
#                           }
#                 result.append(_name_get(mydict))
#         return result
        


class ProductShopPrice(models.Model):
    _name = 'product.shop.price'
    
    shop_id = fields.Many2one('sale.shop', string="Shop")
    price = fields.Float(string="Price")
    product_id = fields.Many2one('product.product', string="Product")
    
    
    
class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"
    
    base = fields.Selection([
        ('list_price', 'Public Price'),
        ('standard_price', 'Cost'),
        ('pricelist', 'Other Pricelist'),
        ('amazon_standard_price', 'Amazon Price')], "Based on",
        default='list_price', required=True,
        help='Base price for computation.\n'
             'Public Price: The base price will be the Sale/public Price.\n'
             'Cost Price : The base price will be the cost price.\n'
             'Other Pricelist : Computation of the base price based on another Pricelist.')

            
            