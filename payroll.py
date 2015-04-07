from trytond.model import ModelSQL, ModelView, MatchMixin, fields
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta
from decimal import Decimal

__all__ = ['EmployeeContract', 'PayslipHourType', 'EmployeeContractRule',
    'Payslip', 'PayslipHour', 'Entitlement', 'LeavePayment', 'WorkingShift']
__metaclass__ = PoolMeta


class EmployeeContract(ModelSQL, ModelView):
    'Employee Contract'
    __name__ = 'payroll.contract'
    employee = fields.Many2One('company.employee', 'Employee', required=True)
    start = fields.Date('Start', required=True)
    end = fields.Date('End')
    rules = fields.One2Many('payroll.contract.hour.rule', 'contract',
        'Hour Rules')

    @classmethod
    def __setup__(cls):
        super(EmployeeContract, cls).__setup__()
        cls._error_messages.update({
                'invalid_dates': ('Start may not be later than end date in '
                    'contract %s.')
                })

    @classmethod
    def validate(cls, contracts):
        for contract in contracts:
            contract.check_dates()

    def check_dates(self):
        if self.end and self.start > self.end:
            self.raise_user_error('invalid_dates', self.rec_name)


class PayslipHourType(ModelSQL, ModelView):
    'Payslip Hour Type'
    __name__ = 'payroll.hour.type'
    name = fields.Char('Name', required=True, translate=True)


class EmployeeContractRule(ModelSQL, ModelView, MatchMixin):
    'Employee Contract Rule'
    __name__ = 'payroll.contract.hour.rule'
    contract = fields.Many2One('payroll.contract', 'Contract',
        required=True)
    # Matching
    hours = fields.Numeric('Hours')
    # Result
    hour_type = fields.Many2One('payroll.hour.type', 'Hour Type',
        required=True)
    formula = fields.Char('Formula', required=True)


class Payslip(ModelSQL, ModelView):
    'Payslip'
    __name__ = 'payroll.payslip'
    employee = fields.Many2One('company.employee', 'Employee', required=True)
    contract = fields.Many2One('payroll.contract', 'Contract', required=True)
    start = fields.Date('Start', required=True)
    end = fields.Date('End', required=True)
    working_hours = fields.Numeric('Working Hours', required=True,
        help='Number of working hours in the current month. Usually 8 * 20.')
    # TODO: Consider calculating it from dates
    working_shifts = fields.One2Many('payroll.working_shift', 'payslip',
        'Working Shifts', add_remove=[
            ('payslip', '=', None),
            ])
    entitlements = fields.One2Many('employee.leave.entitlement', 'payslip',
        'Entitlements', add_remove=[
            ('payslip', '=', None),
            ])
    leave_payments = fields.One2Many('employee.leave.payment', 'payslip',
        'Leave Payments')
    worked_hours = fields.Function(fields.Numeric('Worked Hours'),
        'get_worked_hours')
    leave_hours = fields.Function(fields.Numeric('Leave Hours'),
        'get_leave_hours')
    entitled_hours = fields.Function(fields.Numeric('Entitled Hours'),
        'get_entitled_hours')
    total_hours = fields.Function(fields.Numeric('Total Hours'),
        'get_total_hours')
    remaining_hours = fields.Function(fields.Numeric('Remaining Hours'),
        'get_remaining_hours')

    hours = fields.One2Many('payroll.payslip.hour', 'payslip', 'Hours')
    amount = fields.Function(fields.Numeric('Amount'), 'get_amount')

    @fields.depends('start', 'end')
    def on_change_with_working_hours(self, name=None):
        # TODO: Calculate working days taking into account the weekends.
        # An extension could take into account national holidays, for example.
        return Decimal(20 * 8)

    def get_worked_hours(self, name):
        return sum([x.hours for x in self.working_shifts])

    def get_leave_hours(self, name):
        # Search on 'employee.leave' and find the number of hours that fit
        # inside this payslip
        Leave = Pool().get('employee.leave')
        return Leave.get_leave_hours(self.employee, None, self.start,
            self.end)

    def get_entitled_hours(self, name):
        return sum([x.hours for x in self.entitlements])

    def get_total_hours(self, name):
        return self.worked_hours - self.entitled_hours + self.leave_hours

    def get_remaining_hours(self, name):
        return self.working_hours - self.total_hours

    def get_amount(self, name):
        return sum([x.amount for x in self.hours])

    @classmethod
    def copy(cls, payslips, default=None):
        if default is None:
            default = {}
        if 'working_shifts' not in default:
            default['working_shifts'] = None
        return super(Payslip, cls).copy(payslips, default)


class PayslipHour(ModelSQL, ModelView):
    'Payslip Hour'
    __name__ = 'payroll.payslip.hour'
    payslip = fields.Many2One('payroll.payslip', 'Payslip', required=True)
    type = fields.Many2One('payroll.hour.type', 'Type', required=True)
    hours = fields.Numeric('Hours', required=True)
    price = fields.Numeric('Price', required=True)
    amount = fields.Function(fields.Numeric('Amount'), 'get_amount')

    def get_amount(self, name):
        return self.price * Decimal(str(self.hours))


class Entitlement:
    __name__ = 'employee.leave.entitlement'
    payslip = fields.Many2One('payroll.payslip', 'Payslip')


class LeavePayment:
    __name__ = 'employee.leave.payment'
    payslip = fields.Many2One('payroll.payslip', 'Payslip')


class WorkingShift(ModelSQL, ModelView):
    'Working Shift'
    __name__ = 'payroll.working_shift'
    code = fields.Char('Code', required=True)
    employee = fields.Many2One('company.employee', 'Employee', required=True)
    start_date = fields.DateTime('Start Date', required=True)
    end_date = fields.DateTime('End Date')
    hours = fields.Function(fields.Numeric('Hours'), 'get_hours')
    payslip = fields.Many2One('payroll.payslip', 'Payslip', readonly=True)

    def get_hours(self, name):
        if not self.end_date:
            return
        hours = (self.end_date - self.start_date).total_seconds() / 3600.0
        return Decimal('{:.2}'.format(hours))
