from openerp import models, fields, tools, api
from openerp.exceptions import except_orm, Warning
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

    
class ama_account_payment_term_line(models.Model):
    _inherit = "account.payment.term.line"

    is_discount = fields.Boolean('Is Cash Discount', related='payment_id.is_discount', readonly=True)
    discount_income_account_id = fields.Many2one('account.account', string="Discount Income Account", help="This account will be used to post the cash discount income", company_dependent=True)
    discount_expense_account_id = fields.Many2one('account.account', string="Discount Expense Account", help="This account will be used to post the cash discount expense", company_dependent=True)
    