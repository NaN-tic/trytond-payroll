from trytond.model import ModelSQL, ModelView, MatchMixin, fields
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta
from decimal import Decimal

__all__ = ['EmployeeContract', 'PayslipLineType', 'EmployeeContractRule',
    'Payslip', 'PayslipLine', 'Entitlement', 'LeavePayment', 'WorkingShift']
__metaclass__ = PoolMeta


class EmployeeContract(ModelSQL, ModelView):
    'Employee Contract'
    __name__ = 'payroll.contract'
    employee = fields.Many2One('company.employee', 'Employee', required=True)
    start = fields.Date('Start', required=True)
    end = fields.Date('End')
    yearly_hours = fields.Numeric('Yearly Hours')
# TODO: We should add a functional one2many field that returned the number
# of hours worked by the employee and the total number of hours remaining to
# be worked for each year (LeavePeriod)
# We should think how leaves and leave payments affect these numbers
    rules = fields.One2Many('payroll.contract.rule', 'contract',
        'Payslip Rules')

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


class PayslipLineType(ModelSQL, ModelView):
    'Payslip Line Type'
    __name__ = 'payroll.payslip.line.type'
    name = fields.Char('Name', required=True, translate=True)


class EmployeeContractRule(ModelSQL, ModelView, MatchMixin):
    'Employee Contract Rule'
    __name__ = 'payroll.contract.rule'
    contract = fields.Many2One('payroll.contract', 'Contract',
        required=True)
    # Matching
    hours = fields.Numeric('Hours')

    # Result
    hour_type = fields.Many2One('payroll.payslip.line.type', 'Hour Type',
        required=True)
    formula = fields.Char('Formula', required=True)


class Payslip(ModelSQL, ModelView):
    'Payslip'
    __name__ = 'payroll.payslip'
    employee = fields.Many2One('company.employee', 'Employee', required=True)
    contract = fields.Many2One('payroll.contract', 'Contract', required=True)
    start = fields.Date('Start', required=True)
    end = fields.Date('End', required=True)
    # TODO: Consider calculating it from dates
    working_shifts = fields.Function(fields.One2Many('payroll.working_shift',
            'payslip', 'Working Shifts'), 'get_working_shifts')
    entitlements = fields.Function(fields.One2Many('employee.leave.entitlement',
            'payslip', 'Entitlements'), 'get_entitlements')
    leave_payments = fields.Function(fields.One2Many('employee.leave.payment',
            'payslip', 'Leave Payments'), 'get_leave_payments')
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

    lines = fields.One2Many('payroll.payslip.line', 'payslip', 'Lines')
    amount = fields.Function(fields.Numeric('Amount'), 'get_amount')

    def get_working_shifts(self, name):
        res = []
        for line in self.lines:
            res += [x.id for x in line.working_shifts]
        return res

    def get_entitlements(self, name):
        res = []
        for line in self.lines:
            res += [x.id for x in line.entitlements]
        return res

    def get_worked_hours(self, name):
        res = Decimal('0.0')
        for line in self.lines:
            res += sum([x.hours for x in self.working_shifts])
        return res

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

    def get_amount(self, name):
        return sum([x.amount for x in self.lines])

    @classmethod
    def copy(cls, payslips, default=None):
        if default is None:
            default = {}
        if 'working_shifts' not in default:
            default['working_shifts'] = None
        return super(Payslip, cls).copy(payslips, default)



class PayslipLine(ModelSQL, ModelView):
    'Payslip Line'
    __name__ = 'payroll.payslip.line'
    payslip = fields.Many2One('payroll.payslip', 'Payslip', required=True)
    type = fields.Many2One('payroll.payslip.line.type', 'Type', required=True)
    working_hours = fields.Numeric('Working Hours',
        help='Number of working hours in the current month. Usually 8 * 20.')
    working_shifts = fields.One2Many('payroll.working_shift', 'payslip_line',
        'Working Shifts')
    entitlements = fields.One2Many('employee.leave.entitlement', 'payslip_line',
        'Entitlements', add_remove=[
            ('payslip_line', '=', None),
            ])
    leave_payments = fields.One2Many('employee.leave.payment', 'payslip_line',
        'Leave Payments')
    amount = fields.Numeric('Amount', required=True)
    worked_hours = fields.Function(fields.Numeric('Worked Hours'),
        'get_worked_hours')
    leave_hours = fields.Function(fields.Numeric('Leave Hours', states={
                'invisible': ~Eval('working_hours', 0),
                }, depends=['working_hours']),
        'get_leave_hours')
    entitled_hours = fields.Function(fields.Numeric('Entitled Hours', states={
                'invisible': ~Eval('working_hours', 0),
                }, depends=['working_hours']),
        'get_entitled_hours')
    total_hours = fields.Function(fields.Numeric('Total Hours', states={
                'invisible': ~Eval('working_hours', 0),
                }, depends=['working_hours']),
        'get_total_hours')
    remaining_hours = fields.Function(fields.Numeric('Remaining Hours', states={
                'invisible': ~Eval('working_hours', 0),
                }, depends=['working_hours']),
        'get_remaining_hours')

    # TODO: Add constriant that ensures that there's only one payslip line
    # with working_hours set.

    # Only payslip lines with working_hours set will take into account
    # leave_hours as most of the time they will be holidays and it doesn't
    # make much sense that two different kinds of payslip line type can
    # "allocate" holidays. Also it makes things much more complex as the user
    # should have to decide how many of the total number of holidays the
    # employee has consumed should go to each line type. As it is not
    # a requirement in this case, we just don't implement that

    def get_worked_hours(self, name):
        return sum([x.hours for x in self.working_shifts])

    def get_leave_hours(self, name):
        # Search on 'employee.leave' and find the number of hours that fit
        # inside this payslip
        Leave = Pool().get('employee.leave')
        if not self.working_hours:
            return Decimal('0.0')
        return Leave.get_leave_hours(self.payslip.employee, None,
            self.payslip.start, self.payslip.end)

    def get_entitled_hours(self, name):
        return sum([x.hours for x in self.entitlements])

    def get_total_hours(self, name):
        return self.worked_hours - self.entitled_hours + self.leave_hours

    def get_remaining_hours(self, name):
        return self.working_hours - self.total_hours


class Entitlement:
    __name__ = 'employee.leave.entitlement'
    payslip_line = fields.Many2One('payroll.payslip.line', 'Payslip Line',
        readonly=True)
    payslip = fields.Function(fields.Many2One('payroll.payslip', 'Payslip'),
        'get_payslip')

    def get_payslip(self, name):
        return self.payslip_line.payslip.id if self.payslip_line else None


class LeavePayment:
    __name__ = 'employee.leave.payment'
    payslip_line = fields.Many2One('payroll.payslip.line', 'Payslip Line',
        readonly=True)
    payslip = fields.Function(fields.Many2One('payroll.payslip', 'Payslip'),
        'get_payslip')

    def get_payslip(self, name):
        return self.payslip_line.payslip.id if self.payslip_line else None


class WorkingShift(ModelSQL, ModelView):
    'Working Shift'
    __name__ = 'payroll.working_shift'
    code = fields.Char('Code', required=True)
    employee = fields.Many2One('company.employee', 'Employee', required=True)
    start_date = fields.DateTime('Start Date', required=True)
    end_date = fields.DateTime('End Date')
    hours = fields.Function(fields.Numeric('Hours'), 'get_hours')
    payslip_line = fields.Many2One('payroll.payslip.line', 'Payslip Line',
        readonly=True)
    payslip = fields.Function(fields.Many2One('payroll.payslip', 'Payslip'),
        'get_payslip')

    def get_hours(self, name):
        if not self.end_date:
            return
        hours = (self.end_date - self.start_date).total_seconds() / 3600.0
        return Decimal('{:.2}'.format(hours))

    def get_payslip(self, name):
        return self.payslip_line.payslip.id if self.payslip_line else None
