from openerp import models, api, fields
from openerp import tools, SUPERUSER_ID

class mail_notification(models.Model):
    _inherit = 'mail.notification'

    @api.v7
    def get_signature_footer(self, cr, uid, user_id, res_model=None, res_id=None, context=None, user_signature=True):
        footer = ""
        if not user_id:
            return footer

        # add user signature
        user = self.pool.get("res.users").browse(cr, SUPERUSER_ID, [user_id], context=context)[0]
        if user_signature:
            if user.signature:
                signature = user.signature
            else:
                # signature = "--<br />%s" % user.name
                signature = ""
            footer = tools.append_content_to_html(footer, signature, plaintext=False)

        return footer

        
class ir_mail_server(models.Model):
    _inherit = "ir.mail_server"
    
    force_from_to_reply = fields.Boolean('Erzwinge FROM als REPLY', default=False, help='Uebernimmt den Wert aus dem VON-Feld ins ANTWORT-AN-Feld')
    force_return_path = fields.Boolean('Erzwinge RETURN-PATH', default=False, help='Uebernimmt den Wert von ANTWORT-AN bzw VON in den RETURN-PATH')
    auto_CC_addresses = fields.Text('AUTO CC Adressen', default='', help='Komma-separierte Liste von E-Mail-Adressen, die automatisch dem CC hinzugefuegt werden sollen')
    auto_BCC_addresses = fields.Text('AUTO BCC Adressen', default='', help='Komma-separierte Liste von E-Mail-Adressen, die automatisch dem BCC hinzugefuegt werden sollen')
    
    @api.v7
    def send_email(self, cr, uid, message, mail_server_id=None, smtp_server=None, smtp_port=None, smtp_user=None, smtp_password=None, smtp_encryption=None, smtp_debug=False, context=None):

        ir_mail_server_pool = self.pool.get('ir.mail_server')

        if not mail_server_id:
            mail_server_id = ir_mail_server_pool.search(cr, uid, [])[0]

        server = ir_mail_server_pool.browse(cr, uid, mail_server_id)

        if server.force_from_to_reply:
            del message['Reply-to']
            message['Reply-to'] = message['From']
        
        # mail.bounce.alias has to be NOT set in system parameters
        if server.force_return_path:
            del message['Return-Path']
            message['Return-Path'] = message['Reply-to'] or message['From']

        if server.auto_BCC_addresses:
            if not message['Bcc']:
                message['Bcc'] = server.auto_BCC_addresses
            else:
                bcc = message['Bcc']
                del message['Bcc']
                message['Bcc'] = bcc + "," + server.auto_BCC_addresses

        if server.auto_CC_addresses:
            if not message['Cc']:
                message['Cc'] = server.auto_CC_addresses
            else:
                cc = message['Cc']
                del message['Cc']
                message['Cc'] = cc + "," + server.auto_CC_addresses

        return super(ir_mail_server, self).send_email(cr, uid, message, mail_server_id, smtp_server, smtp_port,
               smtp_user, smtp_password, smtp_encryption, smtp_debug,
               context)