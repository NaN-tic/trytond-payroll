# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .payroll import *

def register():
    Pool.register(
        EmployeeContract,
        PayslipHourType,
        EmployeeContractRule,
        Payslip,
        PayslipHour,
        Entitlement,
        LeavePayment,
        WorkingShift,
        module='payroll', type_='model')
