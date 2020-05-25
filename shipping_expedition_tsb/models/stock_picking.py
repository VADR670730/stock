# -*- coding: utf-8 -*-
from operator import attrgetter
from openerp import _, api, exceptions, fields, models

import logging
import urllib, cStringIO

_logger = logging.getLogger(__name__)

import base64
from datetime import datetime

import base64
import os
import ftplib

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    @api.one
    def generate_shipping_expedition(self):
        #operations
        if self.carrier_id.carrier_type=='tsb':
            self.generate_shipping_expedition_tsb()
        #return
        return super(StockPicking, self).generate_shipping_expedition()
        
    @api.one
    def generate_shipping_expedition_tsb(self):
        if self.shipping_expedition_id.id==0 and self.carrier_id.carrier_type=='tsb' and self.partner_id.id>0:
            res = self.generate_shipping_expedition_tsb_real()[0]
            #operations
            if res['errors']==True:
                #logger
                _logger.info(res)
                #action_error_create_shipping_expedition_message_slack
                self.action_error_create_shipping_expedition_message_slack({
                    'error': res['error']
                })  
                #raise
                raise exceptions.Warning(res['error'])
            else:
                #file_name
                file_name = self.name.replace('/','-')+'.txt'
                #vals
                ir_attachment_vals = {
                    'name': file_name,
                    'datas': base64.encodestring(res['txt_line']),
                    'datas_fname': file_name,
                    'res_model': 'stock.picking',
                    'res_id': self.id
                }
                ir_attachment_obj = self.env['ir.attachment'].sudo().create(ir_attachment_vals)                             
                #create            
                shipping_expedition_vals = {
                    'picking_id': self.id,
                    'carrier_id': self.carrier_id.id,
                    'partner_id': self.partner_id.id,
                    'code': '',
                    'delivery_code': 'Generado '+str(self.name),
                    'date': datetime.today().strftime("%Y-%m-%d"),
                    'hour': '',
                    'origin': self.name,
                    'observations': '',
                    'state': 'generate',
                    'state_code': 2,
                    'ir_attachment_id': ir_attachment_obj.id                
                }
                # order_id
                if self.order_id.id > 0:
                    shipping_expedition_vals['order_id'] = self.order_id.id
                    # user_id
                    if self.order_id.user_id.id > 0:
                        shipping_expedition_vals['user_id'] = self.order_id.user_id.id
                # create
                if 'user_id' in shipping_expedition_vals:
                    shipping_expedition_obj = self.env['shipping.expedition'].sudo(shipping_expedition_vals['user_id']).create(shipping_expedition_vals)
                else:
                    shipping_expedition_obj = self.env['shipping.expedition'].sudo().create(shipping_expedition_vals)
                #update ir_attachment_id
                ir_attachment_obj.write({
                    'res_model': 'shipping.expedition',
                    'res_id': shipping_expedition_obj.id
                })
                #update
                self.shipping_expedition_id = shipping_expedition_obj.id
    
    @api.one
    def generate_shipping_expedition_tsb_real(self):
        #define
        today = datetime.today()
        datetime_body = today.strftime('%d/%m/%Y')
        separator_fields = '#'        
        #partner_name
        if self.partner_id.name==False:
            partner_name = self.partner_id.parent_id.name 
        else:
            partner_name = self.partner_id.name
        #partner_phone        
        if self.partner_id.phone==False:
            partner_phone = ''
        else:
            partner_phone = self.partner_id.phone    
        #email
        if self.partner_id.email==False:
            partner_email = ''
        else:
            partner_email = self.partner_id.email
        #shipping_expedition_note    
        if self.shipping_expedition_note==False:
            observations = ''
        else:
            observations = self.shipping_expedition_note
        #txt_fields    
        txt_fields = [
            {
                'type': 'customer_reference',
                'value': str(self.name),
                'size': 24,
            },
            {
                'type': 'sender_customer',
                'value': self.carrier_id.tsb_sender_customer,
                'size': 11,
            },
            {
                'type': 'sender_center',
                'value': self.carrier_id.tsb_sender_center,
                'size': 4,
            },
            {
                'type': 'sender_name',
                'value': str(self.company_id.name),
                'size': 60,
            },
            {
                'type': 'sender_address',
                'value': str(self.company_id.street),
                'size': 60,
            },
            {
                'type': 'sender_country',
                'value': str(self.company_id.country_id.code),
                'size': 5,
            },
            {
                'type': 'sender_zip',
                'value': str(self.company_id.zip),
                'size': 7,
            },
            {
                'type': 'sender_city',
                'value': str(self.company_id.city),
                'size': 60,
            },
            {
                'type': 'sender_cif',
                'value': str(self.company_id.vat),
                'size': 16,
            },
            {
                'type': 'receiver_name',
                'value': str(partner_name[0:60]),
                'size': 60,
            },
            {
                'type': 'receiver_address',
                'value': str(self.partner_id.street),
                'size': 60,
            },
            {
                'type': 'receiver_country',
                'value': str(self.partner_id.country_id.code),
                'size': 5,
            },
            {
                'type': 'receiver_zip',
                'value': str(self.partner_id.zip),
                'size': 7,
            },
            {
                'type': 'receiver_city',
                'value': str(self.partner_id.city),
                'size': 60,
            },
            {
                'type': 'receiver_cif',
                'value': str(self.partner_id.vat),
                'size': 16,
            },
            {
                'type': 'receiver_person',
                'value': str(partner_name),
                'size': 60,
            },
            {
                'type': 'receiver_phone',
                'value': str(partner_phone),
                'size': 20,
            },
            {
                'type': 'packs',
                'value': str(self.number_of_packages),
                'size': 4,
            },
            {
                'type': 'kgs',
                'value': str(int(self.weight)),
                'size': 5,
            },
            {
                'type': 'volume',
                'value': '000.000',
                'size': 7.3,
            },
            {
                'type': 'shipping_type',
                'value': 'P',
                'size': 4,
            },
            {
                'type': 'observations',
                'value': str(observations),
                'size': 250,
            },
            {
                'type': 'order_number',
                'value': '',
                'size': 24,
            },
            {
                'type': 'date_deferred_delivery',
                'value': '',
                'size': 10,
            },
            {
                'type': 'maximum_delivery_date',
                'value': '',
                'size': 10,
            },
            {
                'type': 'reference_grouping',
                'value': '',
                'size': 24,
            },
            {
                'type': 'locator',
                'value': '',
                'size': 20,
            },
            {
                'type': 'return_conform',
                'value': 'N',
                'size': 1,
            },
            {
                'type': 'identicket',
                'value': 'N',
                'size': 1,
            },
            {
                'type': 'sender_department',
                'value': '',
                'size': 60,
            },
            {
                'type': 'reference2',
                'value': '',
                'size': 35,
            },
            {
                'type': 'exit_date_set',
                'value': '',
                'size': 10,
            },
            {
                'type': 'refund_amount',
                #'value': '0000000.00',
                'value': str(format(self.total_cashondelivery, '.2f')),
                'size': 10.2,
            },            
            {
                'type': 'type_commission_reimbursement_commission',
                'value': 'P',
                'size': 1,
            },
            {
                'type': 'declared_value_amount',
                'value': '0000000.00',
                'size': 10.2,
            },
            {
                'type': 'tk_mailidio',
                'value': str(self.partner_id.country_id.code),
                'size': 5,
            },
            {
                'type': 'tk_mail',
                'value': '',
                'value': str(partner_email),
                'size': 250,
            },
            {
                'type': 'liberated_expedition',
                'value': 'S',
                'size': 1,
            },
            {
                'type': 'label_printer',
                'value': '',
                'size': 30,
            },                                                                                    
        ]
        
        txt_line = ''
        for txt_field in txt_fields:                    
            txt_line = txt_line + str(txt_field['value'])+separator_fields
                
        txt_line = txt_line[:-1]#fix remove last character
        txt_line = txt_line + '\r\n'#fix new line
        #error prev
        response = {
            'errors': True, 
            'error': "", 
            'return': "",
            'txt_line': txt_line
        }                                
        #open file for reading
        picking_name_replace = self.name.replace("/", "-")
        file_name_real = str(picking_name_replace)+'.txt'
        file_name = os.path.dirname(os.path.abspath(__file__))+'/'+str(self.carrier_id.type)+'/'+file_name_real
        #folder_name
        folder_name = str(os.path.abspath(__file__))
        folder_name = folder_name.replace('/models/stock_picking.py', '/'+str(self.carrier_id.carrier_type))
        file_name_real = str(folder_name)+'/'+str(file_name_real)                     
        #check if exists line
        line_exist_in_file = False
        if os.path.isfile(file_name_real):
            line_exist_in_file=True                        
        #continue line_exist_in_file
        if line_exist_in_file==False:
            fh = open(file_name,'a')# if file does not exist, create it                            
            fh.write(txt_line)
            fh.close()
                    
            #upload ftp tsb (open port 21 outbound in security groups)
            ftp = ftplib.FTP(self.carrier_id.tsb_ftp_host)
            
            try:
                ftp.login(self.carrier_id.tsb_ftp_user, self.carrier_id.tsb_ftp_password)
            except ftplib.error_perm as e:
                os.remove(file_name_real)#Fix remove file previously generate
                
                response = {
                    'errors': True, 
                    'error': "Login incorrecto FTP TSB", 
                    'return': "",
                }
                return response
            #remove              
            ftp.cwd(self.carrier_id.tsb_ftp_directory_upload)
            f_h = open(file_name,'rb')
            ftp.storbinary('STOR ' + file_name_real, f_h)  
            ftp.quit()
            #change return and generate shipping_expedition
            response['errors'] = False                      
        else:
            response = {
                'errors': True, 
                'error': "Ya existe este albaran en el archivo .txt", 
                'return': "",
            }
        #return            
        return response                                                            