# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime, time
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from sql import Literal
from sql.aggregate import Max

from trytond.model import ModelSQL, ModelView, MatchMixin, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.modules.product import price_digits

__all__ = ['ContractRuleSet', 'ContractRule',
    'Contract', 'ContractHoursSummary', 'Employee']
__metaclass__ = PoolMeta


class ContractRuleSet(ModelSQL, ModelView):
    '''Payroll Contract Ruleset'''
    __name__ = 'payroll.contract.ruleset'
    name = fields.Char('Name', required=True)
    rules = fields.One2Many('payroll.contract.rule', 'ruleset', 'Rules')
    compute_interventions = fields.Function(
        fields.Boolean('Compute Interventions'),
        'get_compute_interventions')

    def get_compute_interventions(self, name):
        return any(r.compute_method == 'intervention' for r in self.rules)


class ContractRule(ModelSQL, ModelView, MatchMixin):
    'Payroll Contract Rule'
    __name__ = 'payroll.contract.rule'
    ruleset = fields.Many2One('payroll.contract.ruleset', 'Ruleset',
        required=True, select=True, ondelete='CASCADE')
    sequence = fields.Integer('Sequence')
    # Matching
    compute_method = fields.Selection([
            ('working_shift', 'Working Shifts'),
            ('intervention', 'Interventions'),
            ], 'Compute Method', required=True)
    hours = fields.Numeric('Hours', domain=[
            ['OR',
                ('hours', '=', None),
                ('hours', '>', Decimal(0)),
                ],
            ])
    # Result
    hour_type = fields.Many2One('payroll.payslip.line.type', 'Hour Type',
        required=True, help="Used to automatically fill payslip lines.")
    cost_price = fields.Numeric('Cost Price', digits=price_digits,
        required=True,
        help="Price per working shift or intervention to compute the amount "
        "of payslips.")

    @classmethod
    def __setup__(cls):
        super(ContractRule, cls).__setup__()
        cls._order = [
            ('ruleset', 'ASC'),
            ('sequence', 'ASC'),
            ]

    @staticmethod
    def order_sequence(tables):
        table, _ = tables[None]
        return [table.sequence == None, table.sequence]

    def get_rec_name(self, name):
        return '%s, %s' % (self.ruleset.rec_name, self.sequence)

    @classmethod
    def search_rec_name(cls, name, clause):
        return [
            ('ruleset',) + tuple(clause[1:]),
            ]

    @staticmethod
    def default_compute_method():
        return 'working_shift'

    def match(self, pattern):
        if 'hours' in pattern and self.hours:
            pattern = pattern.copy()
            if self.hours < pattern.pop('hours'):
                return False
        return super(ContractRule, self).match(pattern)


class Contract(ModelSQL, ModelView):
    'Payroll Contract'
    __name__ = 'payroll.contract'
    employee = fields.Many2One('company.employee', 'Employee', required=True,
        select=True)
    start = fields.Date('Start', required=True)
    end = fields.Date('End', domain=[
            ['OR',
                ('end', '=', None),
                ('end', '>=', Eval('start'))],
            ], depends=['start'])
    yearly_hours = fields.Numeric('Yearly Hours', domain=[
            ['OR',
                ('yearly_hours', '=', None),
                ('yearly_hours', '>=', Decimal(0)),
                ],
            ], required=True)
    working_shift_hours = fields.Numeric('Working Shift Hours', domain=[
            ['OR',
                ('working_shift_hours', '=', None),
                ('working_shift_hours', '>=', Decimal(0)),
                ],
            ], required=True)
    working_shift_price = fields.Numeric('Working Shift Price', required=True,
        digits=price_digits, domain=[
            ['OR',
                ('working_shift_price', '=', None),
                ('working_shift_price', '>=', Decimal(0)),
                ],
            ],
        help="Price used to compute the amount corresponding to leaves.")
    hours_summary = fields.One2Many('payroll.contract.hours_summary',
        'contract', 'Hours Summary', readonly=True)
    ruleset = fields.Many2One('payroll.contract.ruleset', 'Ruleset',
        required=True)
    rules = fields.Function(fields.One2Many('payroll.contract.rule', None,
            'Payslip Rules'),
        'on_change_with_rules')

    @classmethod
    def __setup__(cls):
        super(Contract, cls).__setup__()
        cls._order.insert(0, ('start', 'ASC'))
        cls._error_messages.update({
                'overlaping_contract': (
                    'The Payroll Contract "%(current_contract)s" overlaps '
                    'with existing contract "%(overlaped_contract)s".'),
                })

    def get_rec_name(self, name):
        return '%s (%s)' % (self.employee.rec_name, self.start)

    @classmethod
    def search_rec_name(cls, name, clause):
        return [
            ('employee',) + tuple(clause[1:]),
            ]

    @fields.depends('ruleset')
    def on_change_with_rules(self, name=None):
        return [r.id for r in self.ruleset.rules] if self.ruleset else None

    @classmethod
    def validate(cls, contracts):
        for contract in contracts:
            contract.check_overlaping_contracts()

    def check_overlaping_contracts(self):
        domain = [
            ('id', '!=', self.id),
            ('employee', '=', self.employee.id),
            ['OR',
                ('end', '=', None),
                ('end', '>=', self.start)],
            ]
        if self.end:
            domain.append(('start', '<=', self.end))
        overlaping_contracts = self.search(domain)
        if overlaping_contracts:
            self.raise_user_error('overlaping_contract', {
                    'current_contract': self.rec_name,
                    'overlaped_contract': overlaping_contracts[0].rec_name,
                    })

    def compute_working_shift_matching_rule(self, working_shift, pattern=None):
        if pattern is None:
            pattern = {}
        else:
            pattern = pattern.copy()
        pattern['hours'] = working_shift.hours
        for rule in self.rules:
            if rule.compute_method != 'working_shift':
                continue
            if rule.match(pattern):
                return rule

    def compute_intervention_matching_rule(self, intervention, pattern=None):
        if pattern is None:
            pattern = {}
        else:
            pattern = pattern.copy()
        pattern['hours'] = intervention.hours
        for rule in self.rules:
            if rule.compute_method != 'intervention':
                continue
            if rule.match(pattern):
                return rule


class ContractHoursSummary(ModelSQL, ModelView):
    'Payroll Contract Hours Summary'
    __name__ = 'payroll.contract.hours_summary'
    _rec_name = 'leave_period'
    contract = fields.Many2One('payroll.contract', 'Payroll', readonly=True)
    leave_period = fields.Many2One('employee.leave.period', 'Period',
        readonly=True)
    working_hours = fields.Function(fields.Numeric('Working Hours',
            digits=(16, 2)),
        'get_working_hours')
    worked_hours = fields.Function(fields.Numeric('Worked Hours',
            digits=(16, 2)),
        'get_worked_hours')
    leave_hours = fields.Function(fields.Numeric('Leave Hours',
            digits=(16, 2)),
        'get_leave_hours')
    entitled_hours = fields.Function(fields.Numeric('Entitled Hours',
            digits=(16, 2)),
        'get_entitled_hours')
    hours_to_do = fields.Function(fields.Numeric('Hours To Do',
            digits=(16, 2)),
        'get_hours_to_do')
    remaining_hours = fields.Function(fields.Numeric('Remaining Hours',
            digits=(16, 2)),
        'get_remaining_extra_hours')
    extra_hours = fields.Function(fields.Numeric('Extra Hours',
            digits=(16, 2)),
        'get_remaining_extra_hours')
    leave_payment_hours = fields.Function(fields.Numeric('Leave Payment Hours',
            digits=(16, 2)),
        'get_leave_payment_hours')

    def get_working_hours(self, name):
        pool = Pool()
        PayslipLine = pool.get('payroll.payslip.line')

        payslip_lines = PayslipLine.search([
                ('payslip.employee', '=', self.contract.employee.id),
                ('payslip.contract', '=', self.contract.id),
                ('payslip.start', '>=', self.leave_period.start),
                ('payslip.end', '<=', self.leave_period.end),
                ])
        if not payslip_lines:
            return Decimal(0)
        digits = self.__class__.working_hours.digits
        return sum(l.working_hours for l in payslip_lines).quantize(
            Decimal(str(10 ** -digits[1])))

    def get_leave_hours(self, name):
        Leave = Pool().get('employee.leave')
        digits = self.__class__.leave_hours.digits
        return Leave.get_leave_hours(self.contract.employee,
            self.leave_period.start, self.leave_period.end).quantize(
                Decimal(str(10 ** -digits[1])))

    def get_hours_to_do(self, name):
        if not self.working_hours:
            return Decimal(0)
        digits = self.__class__.hours_to_do.digits
        return (self.working_hours - self.leave_hours).quantize(
            Decimal(str(10 ** -digits[1])))

    def get_worked_hours(self, name):
        pool = Pool()
        WorkingShift = pool.get('working_shift')

        working_shifts = WorkingShift.search([
                ('employee', '=', self.contract.employee.id),
                ('payslip_line.payslip.start', '>=', self.leave_period.start),
                ('payslip_line.payslip.end', '<=', self.leave_period.end),
                ('state', '=', 'done'),
                ('payslip_line.payslip.contract', '=', self.contract.id),
                ])
        if not working_shifts:
            return Decimal(0)
        digits = self.__class__.worked_hours.digits
        return (len(working_shifts) * self.contract.working_shift_hours
            ).quantize(Decimal(str(10 ** -digits[1])))

    def get_entitled_hours(self, name):
        pool = Pool()
        Entitlement = pool.get('employee.leave.entitlement')
        entitlements = Entitlement.search([
                ('employee', '=', self.contract.employee.id),
                ('period', '=', self.leave_period.id),
                ('payslip_line.payslip.contract', '=', self.contract.id),
                ])
        if not entitlements:
            return Decimal(0)
        digits = self.__class__.entitled_hours.digits
        return sum([e.hours for e in entitlements]).quantize(
            Decimal(str(10 ** -digits[1])))

    def get_remaining_extra_hours(self, name):
        difference = (self.worked_hours - self.hours_to_do
            - self.entitled_hours)
        if name == 'remaining_hours' and difference < Decimal(0):
            digits = self.__class__.remaining_hours.digits
            return -difference.quantize(Decimal(str(10 ** -digits[1])))
        elif name == 'extra_hours' and difference > 0:
            digits = self.__class__.extra_hours.digits
            return difference.quantize(Decimal(str(10 ** -digits[1])))
        return Decimal(0)

    def get_leave_payment_hours(self, name):
        pool = Pool()
        LeavePayment = pool.get('employee.leave.payment')
        leave_payments = LeavePayment.search([
                ('employee', '=', self.contract.employee.id),
                ('period', '=', self.leave_period.id),
                ('payslip_line.payslip.contract', '=', self.contract.id),
                ])
        if not leave_payments:
            return Decimal(0)
        digits = self.__class__.leave_payment_hours.digits
        return sum([p.hours for p in leave_payments]).quantize(
            Decimal(str(10 ** -digits[1])))

    @classmethod
    def table_query(cls):
        pool = Pool()
        Contract = pool.get('payroll.contract')
        LeavePeriod = pool.get('employee.leave.period')
        contract = Contract.__table__()
        leave_period = LeavePeriod.__table__()

        cursor = Transaction().cursor
        cursor.execute(*contract.select(Max(contract.id)))
        max_contract_id, = cursor.fetchone()
        id_padding = 10 ** len(str(max_contract_id))
        return (contract + leave_period).select(
            (contract.id + (Literal(id_padding) * leave_period.id)).as_('id'),
            contract.create_uid,
            contract.create_date,
            contract.write_uid,
            contract.write_date,
            contract.id.as_('contract'),
            leave_period.id.as_('leave_period'))


class Employee:
    __name__ = 'company.employee'
    payroll_contracts = fields.One2Many('payroll.contract', 'employee',
        'Contracts')

    def get_payroll_contract(self, start_date, end_date):
        """
        Return the payroll contract which period is in the supplied period
        """
        pool = Pool()
        Contract = pool.get('payroll.contract')
        contracts = Contract.search([
                ('employee', '=', self.id),
                ('start', '<=', end_date),
                ['OR',
                    ('end', '=', None),
                    ('end', '>=', start_date),
                    ],
                ],
            order=[('start', 'ASC')],
            limit=1)
        if contracts:
            return contracts[0]
