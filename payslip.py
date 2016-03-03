# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelSQL, ModelView, fields
from trytond.pyson import Bool, Date, Eval
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['PayslipLineType', 'Payslip', 'PayslipLine', 'Entitlement',
    'LeavePayment', 'WorkingShift', 'InvoiceLine']
__metaclass__ = PoolMeta

STATES = {
    'readonly': Bool(Eval('supplier_invoice')),
    }
DEPENDS = ['supplier_invoice']


class PayslipLineType(ModelSQL, ModelView):
    'Payslip Line Type'
    __name__ = 'payroll.payslip.line.type'
    name = fields.Char('Name', required=True, translate=True)
    product = fields.Many2One('product.product', 'Product', required=True)


class Payslip(ModelSQL, ModelView):
    'Payslip'
    __name__ = 'payroll.payslip'
    employee = fields.Many2One('company.employee', 'Employee', required=True,
        select=True, states=STATES, depends=DEPENDS)
    contract = fields.Many2One('payroll.contract', 'Contract', required=True,
        select=True, domain=[
            ('employee', '=', Eval('employee', -1)),
            ],
        states=STATES, depends=DEPENDS + ['employee'])
    contract_start = fields.Function(fields.Date('Contract Start'),
        'on_change_with_contract_start')
    contract_end = fields.Function(fields.Date('Contract Start'),
        'on_change_with_contract_end')
    start = fields.Date('Start', required=True, states=STATES, depends=DEPENDS)
    end = fields.Date('End', required=True, domain=[
            ('end', '>', Eval('start')),
            ],
        states=STATES, depends=DEPENDS + ['start'])

    lines = fields.One2Many('payroll.payslip.line', 'payslip', 'Lines',
        states=STATES, depends=DEPENDS)
    working_shifts = fields.Function(fields.One2Many('working_shift',
            'payslip', 'Working Shifts'),
        'get_working_shifts')
    leaves = fields.Function(fields.One2Many('employee.leave', None,
            'Leaves'),
        'get_leaves')
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
    supplier_invoice = fields.Many2One('account.invoice', 'Supplier Invoice',
        domain=[
            ('type', '=', 'in_invoice'),
            ], readonly=True, select=True)

    @classmethod
    def __setup__(cls):
        super(Payslip, cls).__setup__()
        cls._buttons.update({
                'create_supplier_invoices': {
                    'invisible': Bool(Eval('supplier_invoice')),
                    'icon': 'tryton-ok',
                    },
                })

    def get_rec_name(self, name):
        pool = Pool()
        User = pool.get('res.user')
        user = User(Transaction().user)
        date_format = (user.language.date if (user and user.language)
            else '%d/%m/%y')
        return '%s (%s - %s)' % (self.employee.rec_name,
            self.start.strftime(date_format), self.end.strftime(date_format))

    @classmethod
    def search_rec_name(cls, name, clause):
        return [
            ['OR',
                ('employee',) + clause[1:],
                ('start',) + clause[1:]],
            ]

    @fields.depends('employee', 'start', 'end')
    def on_change_with_contract(self, name=None):
        if not self.employee or not self.start or not self.end:
            return
        employee_contract = self.employee.get_payroll_contract(
            self.start, self.end)
        if employee_contract:
            return employee_contract.id

    @fields.depends('contract', methods=['contract'])
    def on_change_with_contract_start(self, name=None):
        if self.contract:
            return self.contract.start

    @fields.depends('contract', methods=['contract'])
    def on_change_with_contract_end(self, name=None):
        if self.contract:
            return self.contract.end

    def get_working_shifts(self, name):
        return [s.id for l in self.lines for s in l.working_shifts]

    def get_leaves(self, name):
        # Search on 'employee.leave' and find the number of hours that fit
        # inside this payslip
        Leave = Pool().get('employee.leave')
        return [l.id for l in Leave.get_leaves(self.employee, self.start,
                self.end)]

    def get_generated_entitlements(self, name):
        return [e.id for l in self.lines for e in l.generated_entitlements]

    def get_leave_payments(self, name):
        return [p.id for l in self.lines for p in l.leave_payments]

    def get_worked_hours(self, name):
        digits = self.__class__.worked_hours.digits
        return sum(l.worked_hours for l in self.lines).quantize(
            Decimal(str(10 ** -digits[1])))

    def get_leave_hours(self, name):
        digits = self.__class__.leave_hours.digits
        return sum(l.leave_hours for l in self.lines).quantize(
            Decimal(str(10 ** -digits[1])))

    def get_generated_entitled_hours(self, name):
        digits = self.__class__.generated_entitled_hours.digits
        return sum(l.generated_entitled_hours for l in self.lines).quantize(
            Decimal(str(10 ** -digits[1])))

    def get_total_hours(self, name):
        digits = self.__class__.total_hours.digits
        return sum(l.total_hours for l in self.lines).quantize(
            Decimal(str(10 ** -digits[1])))

    def get_leave_payment_hours(self, name):
        digits = self.__class__.leave_payment_hours.digits
        return sum(l.leave_payment_hours for l in self.lines).quantize(
            Decimal(str(10 ** -digits[1])))

    @staticmethod
    def default_currency_digits():
        return 2

    def get_currency_digits(self, name):
        return self.employee.company.currency.digits

    def get_amount(self, name):
        return sum([x.amount for x in self.lines])

    @classmethod
    @ModelView.button
    def create_supplier_invoices(cls, payslips):
        pool = Pool()
        Invoice = pool.get('account.invoice')

        to_write = []
        for payslip in payslips:
            if payslip.supplier_invoice:
                continue

            invoice_lines = []
            for line in payslip.lines:
                invoice_line = line.get_supplier_invoice_line()
                if invoice_line:
                    invoice_lines.append(invoice_line)
            if not invoice_lines:
                continue

            invoice = payslip.get_supplier_invoice()
            if hasattr(invoice, 'lines'):
                invoice_lines = invoice.lines + tuple(invoice_lines)
            invoice.lines = invoice_lines
            invoice.save()

            Invoice.update_taxes([invoice])

            to_write.extend(([payslip], {'supplier_invoice': invoice.id}))

        if to_write:
            cls.write(*to_write)

    def get_supplier_invoice(self):
        pool = Pool()
        try:
            BankAccount = pool.get('bank.account')
        except KeyError:
            BankAccount = None
        Invoice = pool.get('account.invoice')
        Journal = pool.get('account.journal')

        invoices = Invoice.search([
                ('type', '=', 'in_invoice'),
                ('party', '=', self.employee.party.id),
                ('invoice_date', '=', self.end),
                ])
        if invoices:
            return invoices[0]

        journals = Journal.search([
                ('type', '=', 'expense'),
                ], limit=1)
        if journals:
            journal, = journals
        else:
            journal = None

        invoice_address = self.employee.party.address_get(type='invoice')
        payment_term = self.employee.party.supplier_payment_term

        invoice = Invoice(
            type='in_invoice',
            journal=journal,
            invoice_date=self.end,
            party=self.employee.party,
            invoice_address=invoice_address,
            account=self.employee.party.account_payable,
            payment_term=payment_term,
            )

        if hasattr(Invoice, 'payment_type'):
            invoice.payment_type = self.employee.party.supplier_payment_type
            if hasattr(Invoice, 'bank_account') and invoice.payment_type:
                bank_account_id = invoice.on_change_with_bank_account()
                if bank_account_id:
                    invoice.bank_account = BankAccount(bank_account_id)
        return invoice


class PayslipLine(ModelSQL, ModelView):
    'Payslip Line'
    __name__ = 'payroll.payslip.line'
    payslip = fields.Many2One('payroll.payslip', 'Payslip', required=True,
        select=True, ondelete='CASCADE')
    type = fields.Many2One('payroll.payslip.line.type', 'Type', required=True,
        select=True)
    working_hours = fields.Numeric('Working Hours', digits=(16, 2), domain=[
            ('working_hours', '>=', Decimal(0)),
            ], required=True,
        help='Number of working hours in the current month. Usually 8 * 20.')
    working_shifts = fields.One2Many('working_shift', 'payslip_line',
        'Working Shifts', domain=[
            ('employee', '=', Eval('_parent_payslip', {}).get('employee')),
            ('state', '=', 'done'),
            ],
        add_remove=[
            ('payslip_line', '=', None),
            ])
    generated_entitlements = fields.One2Many('employee.leave.entitlement',
        'payslip_line', 'Generated Entitlements', domain=[
            ('employee', '=', Eval('_parent_payslip', {}).get('employee')),
            ('date', '>=', Eval('_parent_payslip', {}).get('start', Date())),
            ('date', '<=', Eval('_parent_payslip', {}).get('end', Date())),
            ])
    leave_payments = fields.One2Many('employee.leave.payment', 'payslip_line',
        'Leave Payments', domain=[
            ('employee', '=', Eval('_parent_payslip', {}).get('employee')),
            ('date', '>=', Eval('_parent_payslip', {}).get('start', Date())),
            ('date', '<=', Eval('_parent_payslip', {}).get('end', Date())),
            ],
        add_remove=[
            ('payslip_line', '=', None),
            ])
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
        'get_remaining_extra_hours')
    extra_hours = fields.Function(fields.Numeric('Extra Hours',
            digits=(16, 2), states={
                'invisible': ~Eval('working_hours', 0),
                }, depends=['working_hours']),
        'get_remaining_extra_hours')
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
    supplier_invoice_lines = fields.One2Many('account.invoice.line', 'origin',
        'Invoice Lines', readonly=True)

    @classmethod
    def __setup__(cls):
        super(PayslipLine, cls).__setup__()
        cls._error_messages.update({
                'not_unique_with_hours': (
                    'You can\'t set Working Hours to Payslip Line '
                    '"%(current_line)s" because already exists line '
                    '"%(existing_line)s" with hours in the same Payslip.'),
                'missing_account_expense': ('The product "%s" used to invoice '
                    'payslips doesn\'t have Expense Account.'),
                })

    @staticmethod
    def default_currency_digits():
        return 2

    def get_worked_hours(self, name):
        digits = self.__class__.worked_hours.digits
        if not self.working_shifts:
            return Decimal(0)
        return (len(self.working_shifts)
            * self.payslip.contract.working_shift_hours).quantize(
                Decimal(str(10 ** -digits[1])))

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
        digits = self.__class__.leave_hours.digits
        return Leave.get_leave_hours(self.payslip.employee, self.payslip.start,
            self.payslip.end, type_=self.type).quantize(
                Decimal(str(10 ** -digits[1])))

    def get_generated_entitled_hours(self, name):
        digits = self.__class__.generated_entitled_hours.digits
        if not self.generated_entitlements:
            return Decimal(0)
        return sum([x.hours for x in self.generated_entitlements]).quantize(
            Decimal(str(10 ** -digits[1])))

    def get_total_hours(self, name):
        digits = self.__class__.total_hours.digits
        return (self.worked_hours + self.leave_hours
            - self.generated_entitled_hours).quantize(
                Decimal(str(10 ** -digits[1])))

    def get_remaining_extra_hours(self, name):
        difference = (self.total_hours - self.working_hours)
        if name == 'remaining_hours' and difference < Decimal(0):
            digits = self.__class__.remaining_hours.digits
            return -difference.quantize(Decimal(str(10 ** -digits[1])))
        elif name == 'extra_hours' and difference > 0:
            digits = self.__class__.extra_hours.digits
            return difference.quantize(Decimal(str(10 ** -digits[1])))
        return Decimal(0)

    def get_leave_payment_hours(self, name):
        digits = self.__class__.leave_payment_hours.digits
        if not self.leave_payments:
            return Decimal(0)
        return sum([p.hours for p in self.leave_payments]).quantize(
                Decimal(str(10 ** -digits[1])))

    def get_currency_digits(self, name):
        return self.payslip.employee.company.currency.digits

    @property
    def hour_unit_price(self):
        if (self.payslip.contract.working_shift_price
                and self.payslip.contract.working_shift_hours):
            return (self.payslip.contract.working_shift_price
                / self.payslip.contract.working_shift_hours)
        return Decimal(0)

    def get_amount(self, name):
        if not self.working_shifts:
            return Decimal(0)
        amount = sum([s.cost for s in self.working_shifts])
        amount += self.leave_hours * self.hour_unit_price
        amount -= self.generated_entitled_hours * self.hour_unit_price
        return amount.quantize(Decimal(str(10 ** -self.currency_digits)))

    def get_supplier_invoice_line(self):
        pool = Pool()
        InvoiceLine = pool.get('account.invoice.line')
        Tax = pool.get('account.tax')

        if self.amount == Decimal(0):
            return

        if not self.type.product.account_expense_used:
            self.raise_user_error('missing_account_expense',
                self.type.product.rec_name)

        invoice_line = InvoiceLine()
        invoice_line.invoice_type = 'in_invoice'
        invoice_line.party = self.payslip.employee.party
        invoice_line.type = 'line'
        invoice_line.description = self.type.product.rec_name
        invoice_line.product = self.type.product
        invoice_line.unit_price = self.amount
        invoice_line.quantity = 1
        invoice_line.unit = self.type.product.default_uom
        invoice_line.account = self.type.product.account_expense_used

        invoice_line.taxes = []
        pattern = invoice_line._get_tax_rule_pattern()
        for tax in self.type.product.supplier_taxes_used:
            if invoice_line.party.supplier_tax_rule:
                tax_ids = invoice_line.party.supplier_tax_rule.apply(tax,
                    pattern)
                if tax_ids:
                    invoice_line.taxes.extend(Tax.browse(tax_ids))
                continue
            invoice_line.taxes.append(tax)
        if invoice_line.party.supplier_tax_rule:
            tax_ids = invoice_line.party.supplier_tax_rule.apply(None, pattern)
            if tax_ids:
                invoice_line.taxes.extend(Tax.browse(tax_ids))

        invoice_line.origin = self
        return invoice_line

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

    def get_currency_digits(self, name):
        return self.employee.company.currency.digits

    @property
    def compute_interventions(self):
        return len(self.interventions) > 0

    def get_cost(self, name):
        currency = self.employee.company.currency
        employee_contract = self.employee.get_payroll_contract(
            self.start.date(), self.end.date())
        if not employee_contract:
            return Decimal(0)

        if (employee_contract.ruleset.compute_interventions
                and self.compute_interventions):
            cost = Decimal(0)
            for intervention in self.interventions:
                rule = employee_contract.compute_intervention_matching_rule(
                    intervention)
                if rule:
                    cost += rule.cost_price
            return cost
        rule = employee_contract.compute_working_shift_matching_rule(self)
        if rule:
            return currency.round(rule.cost_price)
        return Decimal(0)


class InvoiceLine:
    __name__ = 'account.invoice.line'

    @property
    def origin_name(self):
        pool = Pool()
        PayslipLine = pool.get('payroll.payslip.line')
        name = super(InvoiceLine, self).origin_name
        if isinstance(self.origin, PayslipLine):
            name = self.origin.rec_name
        return name

    @classmethod
    def _get_origin(cls):
        models = super(InvoiceLine, cls)._get_origin()
        models.append('payroll.payslip.line')
        return models
