from openerp import models, api, fields
from openerp import tools, SUPERUSER_ID
import xmlrpclib
import email
import logging

_logger = logging.getLogger(__name__)


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

               
class mail_thread(models.Model):
    _inherit = 'mail.thread'

    @api.v7
    def message_process(self, cr, uid, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None, context=None):
        """ Process an incoming RFC2822 email message, relying on
            ``mail.message.parse()`` for the parsing operation,
            and ``message_route()`` to figure out the target model.

            Once the target model is known, its ``message_new`` method
            is called with the new message (if the thread record did not exist)
            or its ``message_update`` method (if it did).

            There is a special case where the target model is False: a reply
            to a private message. In this case, we skip the message_new /
            message_update step, to just post a new message using mail_thread
            message_post.

           :param string model: the fallback model to use if the message
               does not match any of the currently configured mail aliases
               (may be None if a matching alias is supposed to be present)
           :param message: source of the RFC2822 message
           :type message: string or xmlrpclib.Binary
           :type dict custom_values: optional dictionary of field values
                to pass to ``message_new`` if a new record needs to be created.
                Ignored if the thread record already exists, and also if a
                matching mail.alias was found (aliases define their own defaults)
           :param bool save_original: whether to keep a copy of the original
                email source attached to the message after it is imported.
           :param bool strip_attachments: whether to strip all attachments
                before processing the message, in order to save some space.
           :param int thread_id: optional ID of the record/thread from ``model``
               to which this mail should be attached. When provided, this
               overrides the automatic detection based on the message
               headers.
        """
        if context is None:
            context = {}

        # extract message bytes - we are forced to pass the message as binary because
        # we don't know its encoding until we parse its headers and hence can't
        # convert it to utf-8 for transport between the mailgate script and here.
        if isinstance(message, xmlrpclib.Binary):
            message = str(message.data)
        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
            
        msg_txt = email.message_from_string(message)
        
        # Fix to avoid finding parent message, so new lead will generated every time
        if 'In-Reply-To' in msg_txt:
            msg_txt.replace_header('In-Reply-To', '')
        if 'References' in msg_txt:
            msg_txt.replace_header('References', '')
            
        # Fix to avoid the auto-pass of bounced mails
        if 'Content-Type' in msg_txt:
            if msg_txt['Content-Type'].startswith('multipart/report;'):
                _logger.debug(msg_txt['Content-Type'])
                msg_txt.replace_header('Content-Type', 'multipart/mixed;' + str(msg_txt['Content-Type'].split(';')[-1:][0])) #multipart/mixed; 
                save_original = True
                _logger.debug(msg_txt['Content-Type'])
        
        if 'From' in msg_txt:
            if 'mailer-daemon' in msg_txt['From'].lower():
                _logger.debug(msg_txt['From'])
                #bounce_alias = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.bounce.alias", context=context)
                #catchall_domain = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.catchall.domain", context=context)
                #msg_txt.replace_header('To', bounce_alias + '@' + catchall_domain)
                msg_txt.replace_header('From', 'mailer_daemon@' + str(msg_txt['From'].split('@')[-1:][0]))
                save_original = True
                _logger.debug(msg_txt['From'])
                    
        # parse the message, verify we are not in a loop by checking message_id is not duplicated
        msg = self.message_parse(cr, uid, msg_txt, save_original=save_original, context=context)
        
        if strip_attachments:
            msg.pop('attachments', None)

        if msg.get('message_id'):   # should always be True as message_parse generate one if missing
            existing_msg_ids = self.pool.get('mail.message').search(cr, SUPERUSER_ID, [
                                                                ('message_id', '=', msg.get('message_id')),
                                                                ], context=context)
            if existing_msg_ids:
                _logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                                msg.get('from'), msg.get('to'), msg.get('message_id'))
                return False

        # find possible routes for the message
        routes = self.message_route(cr, uid, msg_txt, msg, model, thread_id, custom_values, context=context)
        thread_id = self.message_route_process(cr, uid, msg_txt, msg, routes, context=context)
        return thread_id