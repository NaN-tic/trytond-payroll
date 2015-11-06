# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .contract import *
from .payslip import *


def register():
    Pool.register(
        PayslipLineType,
        ContractRuleSet,
        ContractRule,
        Contract,
        ContractHoursSummary,
        Employee,
        Payslip,
        PayslipLine,
        Entitlement,
        LeavePayment,
        WorkingShift,
        module='payroll', type_='model')
