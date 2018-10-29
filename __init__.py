# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import contract
from . import payslip


def register():
    Pool.register(
        payslip.PayslipLineType,
        contract.ContractRuleSet,
        contract.ContractRule,
        contract.Contract,
        contract.ContractHoursSummary,
        contract.Employee,
        payslip.Payslip,
        payslip.PayslipLine,
        payslip.Entitlement,
        payslip.LeavePayment,
        payslip.WorkingShift,
        payslip.Intervention,
        payslip.InvoiceLine,
        module='payroll', type_='model')
