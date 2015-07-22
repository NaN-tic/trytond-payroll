# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelSQL, ModelView, fields
from trytond.pyson import Bool, Date, Eval
from trytond.pool import Pool, PoolMeta

__all__ = ['PayslipLineType', 'Payslip', 'PayslipLine', 'Entitlement',
    'LeavePayment', 'WorkingShift']
__metaclass__ = PoolMeta


class PayslipLineType(ModelSQL, ModelView):
    'Payslip Line Type'
    __name__ = 'payroll.payslip.line.type'
    name = fields.Char('Name', required=True, translate=True)


class Payslip(ModelSQL, ModelView):
    'Payslip'
    __name__ = 'payroll.payslip'
    employee = fields.Many2One('company.employee', 'Employee', required=True,
        select=True)
    contract = fields.Many2One('payroll.contract', 'Contract', required=True,
        select=True, domain=[
            ('employee', '=', Eval('employee', -1)),
            ], depends=['employee'])
    contract_start = fields.Function(fields.Date('Contract Start'),
        'on_change_with_contract_start')
    contract_end = fields.Function(fields.Date('Contract Start'),
        'on_change_with_contract_end')
    start = fields.Date('Start', required=True)
    end = fields.Date('End', required=True, domain=[
            ('end', '>', Eval('start')),
            ], depends=['start'])

    lines = fields.One2Many('payroll.payslip.line', 'payslip', 'Lines')
    working_shifts = fields.Function(fields.One2Many('working_shift',
            'payslip', 'Working Shifts'),
        'get_working_shifts')
    generated_entitlements = fields.Function(fields.One2Many(
            'employee.leave.entitlement', 'payslip', 'Generated Entitlements'),
        'get_generated_entitlements')
    leave_payments = fields.Function(fields.One2Many('employee.leave.payment',
            'payslip', 'Leave Payments'),
        'get_leave_payments')
    worked_hours = fields.Function(fields.Numeric('Worked Hours',
            digits=(16, 2)),
        'get_worked_hours')
    leave_hours = fields.Function(fields.Numeric('Leave Hours',
            digits=(16, 2)),
        'get_leave_hours')
    generated_entitled_hours = fields.Function(
        fields.Numeric('Generated Entitled Hours', digits=(16, 2)),
        'get_generated_entitled_hours')
    leave_payment_hours = fields.Function(fields.Numeric('Leave Payment Hours',
            digits=(16, 2)),
        'get_leave_payment_hours')
    total_hours = fields.Function(fields.Numeric('Total Hours',
            digits=(16, 2)),
        'get_total_hours')
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'get_currency_digits')
    amount = fields.Function(fields.Numeric('Amount',
            digits=(16, Eval('currency_digits', 2)),
            depends=['currency_digits']),
        'get_amount')

    @fields.depends('employee')
    def on_change_employee(self):
        if self.employee:
            current_contract = self.employee.current_payroll_contract
            if current_contract:
                return {
                    'contract': current_contract.id,
                    'contract_start': current_contract.start,
                    'contract_end': current_contract.end,
                    }
        return {}

    @fields.depends('contract.start')
    def on_change_with_contract_start(self, name=None):
        if self.contract:
            return self.contract.start

    @fields.depends('contract.end')
    def on_change_with_contract_end(self, name=None):
        if self.contract:
            return self.contract.end

    def get_working_shifts(self, name):
        return [s.id for l in self.lines for s in l.working_shifts]

    def get_generated_entitlements(self, name):
        return [e.id for l in self.lines for e in l.generated_entitlements]

    def get_leave_payments(self, name):
        return [p.id for l in self.lines for p in l.leave_payments]

    def get_worked_hours(self, name):
        return sum(l.worked_hours for l in self.lines)

    def get_leave_hours(self, name):
        return sum(l.leave_hours for l in self.lines)

    def get_generated_entitled_hours(self, name):
        return sum(l.generated_entitled_hours for l in self.lines)

    def get_total_hours(self, name):
        return sum(l.total_hours for l in self.lines)

    def get_leave_payment_hours(self, name):
        return sum(l.leave_payment_hours for l in self.lines)

    @staticmethod
    def default_currency_digits():
        return 2

    def get_currency_digits(self, name):
        return self.employee.company.currency.digits

    def get_amount(self, name):
        return sum([x.amount for x in self.lines])


class PayslipLine(ModelSQL, ModelView):
    'Payslip Line'
    __name__ = 'payroll.payslip.line'
    payslip = fields.Many2One('payroll.payslip', 'Payslip', required=True,
        select=True, ondelete='CASCADE')
    type = fields.Many2One('payroll.payslip.line.type', 'Type', required=True,
        select=True)
    working_hours = fields.Numeric('Working Hours', digits=(16, 2), domain=[
            ('working_hours', '>=', Decimal(0)),
            ],
        help='Number of working hours in the current month. Usually 8 * 20.')
    payslip_employee = fields.Function(fields.Many2One('company.employee',
            'Payslip Employee'),
        'on_change_with_payslip_employee')
    payslip_start = fields.Function(fields.Date('Payslip Start'),
        'on_change_with_payslip_start')
    payslip_end = fields.Function(fields.Date('Payslip Start'),
        'on_change_with_payslip_end')
    working_shifts = fields.One2Many('working_shift', 'payslip_line',
        'Working Shifts', domain=[
            ('employee', '=', Eval('payslip_employee')),
            ('state', '=', 'done'),
            ],
        add_remove=[
            ('payslip_line', '=', None),
            ],
        depends=['payslip_employee'])
    generated_entitlements = fields.One2Many('employee.leave.entitlement',
        'payslip_line', 'Generated Entitlements', domain=[
            ('employee', '=', Eval('payslip_employee')),
            ('date', '>=', Eval('payslip_start', Date())),
            ('date', '<=', Eval('payslip_end', Date())),
            ], depends=['payslip_employee', 'payslip_start', 'payslip_end'])
    leave_payments = fields.One2Many('employee.leave.payment', 'payslip_line',
        'Leave Payments', domain=[
            ('employee', '=', Eval('payslip_employee')),
            ('date', '>=', Eval('payslip_start', Date())),
            ('date', '<=', Eval('payslip_end', Date())),
            ],
        add_remove=[
            ('payslip_line', '=', None),
            ], depends=['payslip_employee', 'payslip_start', 'payslip_end'])
    worked_hours = fields.Function(fields.Numeric('Worked Hours',
            digits=(16, 2)),
        'get_worked_hours')
    leave_hours = fields.Function(fields.Numeric('Leave Hours', digits=(16, 2),
            states={
                'invisible': ~Bool(Eval('working_hours', 0)),
                }, depends=['working_hours']),
        'get_leave_hours')
    generated_entitled_hours = fields.Function(
        fields.Numeric('Generated Entitled Hours', digits=(16, 2), states={
                'invisible': ~Bool(Eval('working_hours', 0)),
                }, depends=['working_hours']),
        'get_generated_entitled_hours')
    total_hours = fields.Function(fields.Numeric('Total Hours', digits=(16, 2),
            states={
                'invisible': ~Bool(Eval('working_hours', 0)),
                }, depends=['working_hours']),
        'get_total_hours')
    remaining_hours = fields.Function(fields.Numeric('Remaining Hours',
            digits=(16, 2), states={
                'invisible': ~Eval('working_hours', 0),
                }, depends=['working_hours']),
        'get_remaining_hours')
    leave_payment_hours = fields.Function(fields.Numeric('Leave Payment Hours',
            digits=(16, 2), states={
                'invisible': ~Bool(Eval('working_hours', 0)),
                }, depends=['working_hours']),
        'get_leave_payment_hours')
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'get_currency_digits')
    amount = fields.Function(fields.Numeric('Amount',
            digits=(16, Eval('currency_digits', 2)),
            depends=['currency_digits']),
        'get_amount')

    @classmethod
    def __setup__(cls):
        super(PayslipLine, cls).__setup__()
        cls._error_messages.update({
                'not_unique_with_hours': (
                    'You can\'t set Working Hours to Payslip Line '
                    '"%(current_line)s" because already exists line '
                    '"%(existing_line)s" with hours in the same Payslip.'),
                })

    @fields.depends('_parent_payslip.employee')
    def on_change_with_payslip_employee(self, name=None):
        if self.payslip and self.payslip.employee:
            return self.payslip.employee.id

    @fields.depends('_parent_payslip.start')
    def on_change_with_payslip_start(self, name=None):
        if self.payslip:
            return self.payslip.start

    @fields.depends('_parent_payslip.end')
    def on_change_with_payslip_end(self, name=None):
        if self.payslip:
            return self.payslip.end

    @staticmethod
    def default_currency_digits():
        return 2

    def get_worked_hours(self, name):
        if not self.working_shifts:
            return Decimal(0)
        return sum([s.cost_hours for s in self.working_shifts])

    # Only payslip lines with working_hours set will take into account
    # leave_hours as most of the time they will be holidays and it doesn't
    # make much sense that two different kinds of payslip line type can
    # "allocate" holidays. Also it makes things much more complex as the user
    # should have to decide how many of the total number of holidays the
    # employee has consumed should go to each line type. As it is not
    # a requirement in this case, we just don't implement that
    def get_leave_hours(self, name):
        # Search on 'employee.leave' and find the number of hours that fit
        # inside this payslip
        Leave = Pool().get('employee.leave')
        return Leave.get_leave_hours(self.payslip.employee, self.payslip_start,
            self.payslip_end, type_=self.type)

    def get_generated_entitled_hours(self, name):
        if not self.generated_entitlements:
            return Decimal(0)
        return sum([x.hours for x in self.generated_entitlements])

    def get_total_hours(self, name):
        return (self.worked_hours + self.leave_hours
            - self.generated_entitled_hours)

    def get_remaining_hours(self, name):
        return self.working_hours - self.total_hours

    def get_leave_payment_hours(self, name):
        if not self.leave_payments:
            return Decimal(0)
        return sum([p.hours for p in self.leave_payments])

    def get_currency_digits(self, name):
        return self.payslip.employee.company.currency.digits

    def get_amount(self, name):
        if not self.working_shifts:
            return Decimal(0)
        # TODO: Sum leave hours? substract entitled hours? how to sum leave
        # payment amount?
        return sum([s.cost for s in self.working_shifts])

    @classmethod
    def validate(cls, lines):
        super(PayslipLine, cls).validate(lines)
        for line in lines:
            line.check_unique_in_payslip()

    def check_unique_in_payslip(self):
        if self.working_hours == Decimal(0):
            return
        other_lines = self.search([
                ('id', '!=', self.id),
                ('payslip', '=', self.payslip.id),
                ('working_hours', '!=', Decimal(0)),
                ])
        if other_lines:
            self.raise_user_error('not_unique_with_hours', {
                    'current_line': self.rec_name,
                    'existing_line': other_lines[0].rec_name,
                    })


class Entitlement:
    __name__ = 'employee.leave.entitlement'
    payslip_line = fields.Many2One('payroll.payslip.line', 'Payslip Line',
        readonly=True)
    payslip = fields.Function(fields.Many2One('payroll.payslip', 'Payslip'),
        'get_payslip', searcher='search_payslip')

    def get_payslip(self, name):
        return self.payslip_line.payslip.id if self.payslip_line else None

    @classmethod
    def search_payslip(cls, name, clause):
        return [
            ('payslip_line.payslip',) + clause[1:],
            ]


class LeavePayment:
    __name__ = 'employee.leave.payment'
    payslip_line = fields.Many2One('payroll.payslip.line', 'Payslip Line',
        readonly=True)
    payslip = fields.Function(fields.Many2One('payroll.payslip', 'Payslip'),
        'get_payslip', searcher='search_payslip')

    def get_payslip(self, name):
        return self.payslip_line.payslip.id if self.payslip_line else None

    @classmethod
    def search_payslip(cls, name, clause):
        return [
            ('payslip_line.payslip',) + clause[1:],
            ]


class WorkingShift:
    __name__ = 'working_shift'
    payslip_line = fields.Many2One('payroll.payslip.line', 'Payslip Line',
        readonly=True)
    payslip = fields.Function(fields.Many2One('payroll.payslip', 'Payslip'),
        'get_payslip', searcher='search_payslip')
    cost_hours = fields.Function(fields.Numeric('Cost Hours', digits=(16, 2)),
        'get_cost_hours')
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'get_currency_digits')
    cost = fields.Function(fields.Numeric('Amount',
            digits=(16, Eval('currency_digits', 2)), domain=[
                ('amount', '>=', Decimal(0)),
                ], depends=['currency_digits']),
        'get_cost')

    def get_payslip(self, name):
        return self.payslip_line.payslip.id if self.payslip_line else None

    @classmethod
    def search_payslip(cls, name, clause):
        return [
            ('payslip_line.payslip',) + clause[1:],
            ]

    def get_cost_hours(self, name):
        '''
        Cost hours should return the number of hours after rounding according
        to employee's configuration.
        '''
        rule = self._compute_matching_rule()
        if rule and rule.hours:
            return rule.hours
        return self.hours

    def get_currency_digits(self, name):
        return self.employee.company.currency.digits

    def get_cost(self, name):
        currency = self.employee.company.currency
        rule = self._compute_matching_rule()
        if rule:
            cost = rule.get_unit_price()
            return currency.round(cost)
        return Decimal(0)

    def _compute_matching_rule(self):
        employee_contract = self.employee.current_payroll_contract
        if employee_contract:
            rule = employee_contract.compute_matching_rule(self)
            if rule:
                return rule
