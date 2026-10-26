from .currency import check_currency
from .income import check_income
from .keyword import check_keyword
from .refund import check_refund
from .transfer import check_transfer

# Order important hai: pehla jo match kare wohi faisla karta hai
CHECKS = [check_transfer, check_currency, check_refund, check_income, check_keyword]