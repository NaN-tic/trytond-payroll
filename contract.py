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
from trytond.tools import safe_eval
from trytond.tools.decimal_ import decistmt
from trytond.transaction import Transaction

__all__ = ['Contract', 'ContractHoursSummary', 'ContractRule', 'Employee']
__metaclass__ = PoolMeta


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
            ('yearly_hours', '>=', Decimal(0)),
            ])
    hours_summary = fields.One2Many('payroll.contract.hours_summary',
        'contract', 'Hours Summary', readonly=True)
    rules = fields.One2Many('payroll.contract.rule', 'contract',
        'Payslip Rules')

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
            ['OR',
                ('employee',) + clause[1:],
                ('start',) + clause[1:]],
            ]

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

    def compute_matching_rule(self, working_shift, pattern=None):
        if pattern is None:
            pattern = {}
        else:
            pattern = pattern.copy()
        pattern['hours'] = working_shift.hours
        for rule in self.rules:
            if rule.match(pattern):
                return rule


class ContractHoursSummary(ModelSQL, ModelView):
    'Payroll Contract Hours Summary'
    __name__ = 'payroll.contract.hours_summary'
    _rec_name = 'leave_period'
    contract = fields.Many2One('payroll.contract', 'Payroll', readonly=True)
    leave_period = fields.Many2One('employee.leave.period', 'Period',
        readonly=True)
    worked_hours = fields.Function(fields.Numeric('Worked Hours',
            digits=(16, 2)),
        'get_worked_hours')
    leave_hours = fields.Function(fields.Numeric('Leave Hours',
            digits=(16, 2)),
        'get_leave_hours')
    entitled_hours = fields.Function(fields.Numeric('Entitled Hours',
            digits=(16, 2)),
        'get_entitled_hours')
    total_hours = fields.Function(fields.Numeric('Total Hours',
            digits=(16, 2)),
        'get_total_hours')
    remaining_hours = fields.Function(fields.Numeric('Remaining Hours',
            digits=(16, 2)),
        'get_remaining_hours')
    leave_payment_hours = fields.Function(fields.Numeric('Leave Payment Hours',
            digits=(16, 2)),
        'get_leave_payment_hours')

    def get_worked_hours(self, name):
        pool = Pool()
        WorkingShift = pool.get('working_shift')

        period_end = self.leave_period.end + relativedelta(days=1)
        period_end = datetime.combine(period_end, time(0, 0))
        working_shifts = WorkingShift.search([
                ('employee', '=', self.contract.employee.id),
                ('payslip_line.payslip.start', '>=', self.leave_period.start),
                ('payslip_line.payslip.end', '<=', self.leave_period.end),
                ('state', '=', 'done'),
                ('payslip_line.payslip.contract', '=', self.contract.id),
                ])
        if not working_shifts:
            return Decimal(0)
        return sum([s.cost_hours for s in working_shifts])

    def get_leave_hours(self, name):
        Leave = Pool().get('employee.leave')
        return Leave.get_leave_hours(self.contract.employee,
            self.leave_period.start, self.leave_period.end)

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
        return sum([e.hours for e in entitlements])

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
        return sum([p.hours for p in leave_payments])

    def get_total_hours(self, name):
        return self.worked_hours + self.leave_hours - self.entitled_hours

    def get_remaining_hours(self, name):
        pool = Pool()
        PayslipLine = pool.get('payroll.payslip.line')
        lines = PayslipLine.search([
                ('payslip.contract', '=', self.contract.id),
                ('payslip.start', '<', self.leave_period.end),
                ('payslip.end', '>=', self.leave_period.start),
                ('working_hours', '!=', Decimal(0)),
                ])
        if lines:
            working_hours = sum(l.working_hours for l in lines)
            return working_hours - self.total_hours
        return Decimal(0)

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


class ContractRule(ModelSQL, ModelView, MatchMixin):
    'Payroll Contract Rule'
    __name__ = 'payroll.contract.rule'
    contract = fields.Many2One('payroll.contract', 'Contract',
        required=True, select=True, ondelete='CASCADE')
    sequence = fields.Integer('Sequence')
    # Matching
    hours = fields.Numeric('Hours', domain=[
            ('hours', '>=', Decimal(0)),
            ])
    # Result
    hour_type = fields.Many2One('payroll.payslip.line.type', 'Hour Type',
        required=True, help="Used to automatically fill payslip lines.")
    product = fields.Many2One('product.product', 'Product', required=True)
    formula = fields.Char('Formula', required=True)

    @classmethod
    def __setup__(cls):
        super(ContractRule, cls).__setup__()
        cls._order = [
            ('contract', 'ASC'),
            ('sequence', 'ASC'),
            ]

    @staticmethod
    def order_sequence(tables):
        table, _ = tables[None]
        return [table.sequence == None, table.sequence]

    def get_rec_name(self, name):
        return '%s, %s' % (self.contract.rec_name, self.sequence)

    def match(self, pattern):
        if 'hours' in pattern:
            pattern = pattern.copy()
            if self.hours < pattern.pop('hours'):
                return False
        return super(ContractRule, self).match(pattern)

    def get_unit_price(self):
        '''
        Return unit price (as Decimal)
        '''
        context = Transaction().context.copy()
        context['Decimal'] = Decimal
        res = safe_eval(decistmt(self.formula), context)
        return Decimal(res)


class Employee:
    __name__ = 'company.employee'
    payroll_contracts = fields.One2Many('payroll.contract', 'employee',
        'Contracts')

    @property
    def current_payroll_contract(self):
        Date = Pool().get('ir.date')
        today = Date.today()
        for contract in reversed(self.payroll_contracts):
            if contract.start <= today:
                if not contract.end or contract.end >= today:
                    return contract
            else:
                return
        return
