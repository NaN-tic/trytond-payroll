================
Payroll Scenario
================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date(2015, 7, 17)  # Make it previsible
    >>> now = datetime.datetime(2015, 7, 17, 10, 0, 0)

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install working_shift_contract::

    >>> Module = Model.get('ir.module.module')
    >>> module, = Module.find([('name', '=', 'payroll')])
    >>> module.click('install')
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='U.S. Dollar', symbol='$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point='.', mon_thousands_sep=',')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find([])

Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> config._context = User.get_preferences(True, config.context)

Create fiscal year::

    >>> FiscalYear = Model.get('account.fiscalyear')
    >>> Sequence = Model.get('ir.sequence')
    >>> SequenceStrict = Model.get('ir.sequence.strict')
    >>> fiscalyear = FiscalYear(name=str(today.year))
    >>> fiscalyear.start_date = today + relativedelta(month=1, day=1)
    >>> fiscalyear.end_date = today + relativedelta(month=12, day=31)
    >>> fiscalyear.company = company
    >>> post_move_seq = Sequence(name=str(today.year), code='account.move',
    ...     company=company)
    >>> post_move_seq.save()
    >>> fiscalyear.post_move_sequence = post_move_seq
    >>> invoice_seq = SequenceStrict(name=str(today.year),
    ...     code='account.invoice', company=company)
    >>> invoice_seq.save()
    >>> fiscalyear.out_invoice_sequence = invoice_seq
    >>> fiscalyear.in_invoice_sequence = invoice_seq
    >>> fiscalyear.out_credit_note_sequence = invoice_seq
    >>> fiscalyear.in_credit_note_sequence = invoice_seq
    >>> fiscalyear.save()
    >>> FiscalYear.create_period([fiscalyear.id], config.context)

Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> Journal = Model.get('account.journal')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')
    >>> cash, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('name', '=', 'Main Cash'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.credit_account = cash
    >>> cash_journal.debit_account = cash
    >>> cash_journal.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> PaymentTermLine = Model.get('account.invoice.payment_term.line')
    >>> payment_term = PaymentTerm(name='Direct')
    >>> payment_term_line = PaymentTermLine(type='remainder', days=0)
    >>> payment_term.lines.append(payment_term_line)
    >>> payment_term.save()

Create employees::

    >>> Employee = Model.get('company.employee')
    >>> employee_party = Party(name='Employee')
    >>> employee_party.save()
    >>> employee = Employee()
    >>> employee.party = employee_party
    >>> employee.company = company
    >>> employee.save()

Create products::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> hour, = ProductUom.find([('name', '=', 'Hour')])
    >>> ProductTemplate = Model.get('product.template')
    >>> template = ProductTemplate()
    >>> template.name = 'Large Working Shift'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.salable = True
    >>> template.purchasable = True
    >>> template.list_price = Decimal('800')
    >>> template.cost_price = Decimal('200')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> large_shift, = template.products

    >>> template = ProductTemplate()
    >>> template.name = 'Short Working Shift'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.salable = True
    >>> template.purchasable = True
    >>> template.list_price = Decimal('300')
    >>> template.cost_price = Decimal('70')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> short_shift, = template.products

    >>> template = ProductTemplate()
    >>> template.name = 'guard'
    >>> template.default_uom = hour
    >>> template.type = 'service'
    >>> template.salable = True
    >>> template.purchasable = True
    >>> template.list_price = Decimal('70')
    >>> template.cost_price = Decimal('30')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> guard, = template.products

    >>> template = ProductTemplate()
    >>> template.name = 'Professional Services'
    >>> template.default_uom = hour
    >>> template.type = 'service'
    >>> template.salable = True
    >>> template.purchasable = True
    >>> template.list_price = Decimal('0')
    >>> template.cost_price = Decimal('0')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> professional_services, = template.products

    >>> template = ProductTemplate()
    >>> template.name = 'Extra Professional Services'
    >>> template.default_uom = hour
    >>> template.type = 'service'
    >>> template.salable = True
    >>> template.purchasable = True
    >>> template.list_price = Decimal('0')
    >>> template.cost_price = Decimal('0')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> extra_professional_services, = template.products

Configure sequences::

    >>> WorkingShiftConfig = Model.get('working_shift.configuration')
    >>> Sequence = Model.get('ir.sequence')
    >>> working_shift_config = WorkingShiftConfig(1)
    >>> intervention_sequence, = Sequence.find([
    ...     ('code', '=', 'working_shift.intervention')])
    >>> working_shift_config.intervention_sequence = intervention_sequence
    >>> working_shift_sequence, = Sequence.find([
    ...     ('code', '=', 'working_shift')])
    >>> working_shift_config.working_shift_sequence = working_shift_sequence
    >>> working_shift_config.save()

Create Payslip Types::

    >>> PayslipLineType = Model.get('payroll.payslip.line.type')
    >>> normal_line_type = PayslipLineType(name='Normal')
    >>> normal_line_type.product = professional_services
    >>> normal_line_type.save()
    >>> extra_line_type = PayslipLineType(name='Extra')
    >>> extra_line_type.product = extra_professional_services
    >>> extra_line_type.save()

Create Ruleset::

    >>> RuleSet = Model.get('payroll.contract.ruleset')
    >>> ruleset = RuleSet()
    >>> ruleset.name = 'Employees'
    >>> rule = ruleset.rules.new()
    >>> rule.sequence= 1
    >>> rule.hours = Decimal('4.5')
    >>> rule.hour_type = normal_line_type
    >>> rule.cost_price = Decimal('300')
    >>> rule = ruleset.rules.new()
    >>> rule.sequence= 2
    >>> rule.hours = Decimal(8)
    >>> rule.hour_type = normal_line_type
    >>> rule.cost_price = Decimal('800')
    >>> ruleset.save()

Create Contract::

    >>> Contract = Model.get('payroll.contract')
    >>> contract = Contract()
    >>> contract.employee = employee
    >>> contract.start = today.replace(month=1, day=1)
    >>> contract.end = today.replace(month=12, day=31)
    >>> contract.yearly_hours = Decimal(1840)
    >>> contract.working_shift_hours = Decimal(8)
    >>> contract.working_shift_price = Decimal(360)
    >>> contract.ruleset = ruleset
    >>> contract.save()

Create overlaped Contract::

    >>> contract2 = Contract()
    >>> contract2.employee = employee
    >>> contract2.start = today.replace(month=12, day=1)
    >>> contract2.end = today.replace(month=12, day=31)
    >>> contract2.yearly_hours = Decimal(1840)
    >>> contract2.working_shift_hours = Decimal(8)
    >>> contract2.working_shift_price = Decimal(360)
    >>> contract2.ruleset = ruleset
    >>> contract2.save()
    Traceback (most recent call last):
        ...
    UserError: ('UserError', (u'The Payroll Contract "Employee (2015-12-01)" overlaps with existing contract "Employee (2015-01-01)".', ''))

Create leave periods::

    >>> LeavePeriod = Model.get('employee.leave.period')
    >>> leave_period = LeavePeriod(name='2015')
    >>> leave_period.start = datetime.date(2015, 1, 1)
    >>> leave_period.end = datetime.date(2015, 12, 31)
    >>> leave_period.save()

    >>> leave_period2 = LeavePeriod(name='2016')
    >>> leave_period2.start = datetime.date(2016, 1, 1)
    >>> leave_period2.end = datetime.date(2016, 12, 31)
    >>> leave_period2.save()

Create leave types::

    >>> LeaveType = Model.get('employee.leave.type')
    >>> holidays = LeaveType(name='Holidays')
    >>> holidays.save()
    >>> other = LeaveType(name='Other')
    >>> other.save()

Create year holidays entitlement::

    >>> Entitlement = Model.get('employee.leave.entitlement')
    >>> entitlement = Entitlement()
    >>> entitlement.employee = employee
    >>> entitlement.period = leave_period
    >>> entitlement.type = holidays
    >>> entitlement.hours = Decimal(184)
    >>> entitlement.save()

Create leaves (one gets days from other year)::

    >>> Leave = Model.get('employee.leave')
    >>> leave = Leave()
    >>> leave.employee = employee
    >>> leave.period = leave_period
    >>> leave.type = holidays
    >>> leave.request_date = datetime.date(today.year, 5, 1)
    >>> leave.hours = Decimal(8)
    >>> leave.start = datetime.date(today.year, 5, 5)
    >>> leave.end = datetime.date(today.year, 5, 5)
    >>> leave.save()
    >>> leave.click('approve')
    >>> leave.click('done')

    >>> leave = Leave()
    >>> leave.employee = employee
    >>> leave.period = leave_period
    >>> leave.type = holidays
    >>> leave.request_date = datetime.date(2015, 5, 28)
    >>> leave.hours = Decimal(96)
    >>> leave.start = datetime.date(2015, 12, 27)
    >>> leave.end = datetime.date(2016, 1, 7)
    >>> leave.save()
    >>> leave.click('approve')
    >>> leave.click('done')

Create working shifts::

    >>> WorkingShift = Model.get('working_shift')
    >>> working_shift1 = WorkingShift()
    >>> working_shift1.employee = employee
    >>> working_shift1.start = datetime.datetime(today.year, 5, 6, 9, 0, 0)
    >>> working_shift1.end = datetime.datetime(today.year, 5, 6, 12, 0, 0)
    >>> working_shift1.hours
    Decimal('3.00')
    >>> working_shift1.save()
    >>> working_shift1.click('confirm')
    >>> working_shift1.click('done')

    >>> working_shift2 = WorkingShift()
    >>> working_shift2.employee = employee
    >>> working_shift2.start = datetime.datetime(today.year, 5, 7, 9, 0, 0)
    >>> working_shift2.end = datetime.datetime(today.year, 5, 7, 17, 0, 0)
    >>> working_shift2.hours
    Decimal('8.00')
    >>> working_shift2.save()
    >>> working_shift2.click('confirm')
    >>> working_shift2.click('done')

    >>> working_shift3 = WorkingShift()
    >>> working_shift3.employee = employee
    >>> working_shift3.start = datetime.datetime(today.year, 5, 8, 9, 0, 0)
    >>> working_shift3.end = datetime.datetime(today.year, 5, 8, 16, 30, 0)
    >>> working_shift3.hours
    Decimal('7.50')
    >>> working_shift3.save()
    >>> working_shift3.click('confirm')
    >>> working_shift3.click('done')

    >>> working_shift4 = WorkingShift()
    >>> working_shift4.employee = employee
    >>> working_shift4.start = datetime.datetime(today.year, 5, 9, 9, 0, 0)
    >>> working_shift4.end = datetime.datetime(today.year, 5, 9, 16, 30, 0)
    >>> working_shift4.hours
    Decimal('7.50')
    >>> working_shift4.save()
    >>> working_shift4.click('confirm')
    >>> working_shift4.click('done')

Create leave payments::

    >>> LeavePayment = Model.get('employee.leave.payment')
    >>> leave_payment = LeavePayment()
    >>> leave_payment.employee = employee
    >>> leave_payment.type = holidays
    >>> leave_payment.period = leave_period
    >>> leave_payment.date = datetime.date(today.year, 5, 8)
    >>> leave_payment.hours = Decimal(8)
    >>> leave_payment.save()

Create May Payslip::

    >>> Payslip = Model.get('payroll.payslip')
    >>> payslip = Payslip()
    >>> payslip.employee = employee
    >>> payslip.start = today.replace(month=5, day=1)
    >>> payslip.end = today.replace(month=5, day=31)
    >>> payslip.contract == contract
    True
    >>> line = payslip.lines.new()
    >>> line.type = normal_line_type
    >>> line.working_hours = Decimal('160')
    >>> line.working_shifts.append(working_shift1)
    >>> line.working_shifts.append(working_shift2)
    >>> line.working_shifts.append(working_shift3)
    >>> line.working_shifts.append(working_shift4)
    >>> extra_entitlement = line.generated_entitlements.new()
    >>> extra_entitlement.employee = employee
    >>> extra_entitlement.type = holidays
    >>> extra_entitlement.period = leave_period
    >>> extra_entitlement.date = datetime.date(today.year, 5, 7)
    >>> extra_entitlement.hours = Decimal(4)
    >>> line.leave_payments.append(leave_payment)
    >>> payslip.save()

Check may payslip functionals::

    >>> line, = payslip.lines
    >>> line.worked_hours
    Decimal('32.00')
    >>> line.leave_hours
    Decimal('8.00')
    >>> line.generated_entitled_hours
    Decimal('4.00')
    >>> line.total_hours
    Decimal('36.00')
    >>> line.remaining_hours
    Decimal('124.00')
    >>> line.leave_payment_hours
    Decimal('8.00')
    >>> line.amount
    Decimal('2880.00')

    >>> payslip.worked_hours
    Decimal('32.00')
    >>> payslip.leave_hours
    Decimal('8.00')
    >>> payslip.generated_entitled_hours
    Decimal('4.00')
    >>> payslip.total_hours
    Decimal('36.00')
    >>> line.leave_payment_hours
    Decimal('8.00')
    >>> payslip.amount
    Decimal('2880.00')

Create empty December Payslip::

    >>> payslip = Payslip()
    >>> payslip.employee = employee
    >>> payslip.start = datetime.date(2015, 12, 1)
    >>> payslip.end = datetime.date(2015, 12, 31)
    >>> payslip.contract == contract
    True
    >>> line = payslip.lines.new()
    >>> line.type = normal_line_type
    >>> line.working_hours = Decimal('160')
    >>> payslip.save()

Check payslip functionals::

    >>> line, = payslip.lines
    >>> line.worked_hours
    Decimal('0')
    >>> line.leave_hours
    Decimal('40.00')
    >>> line.generated_entitled_hours
    Decimal('0')
    >>> line.leave_payment_hours
    Decimal('0')
    >>> line.total_hours
    Decimal('40.00')
    >>> line.remaining_hours
    Decimal('120.00')
    >>> line.amount
    Decimal('0')

Check employee contract hours summary::

    >>> contract.reload()
    >>> summary_by_period = {s.leave_period.id: s for s in contract.hours_summary}
    >>> summary_by_period[leave_period.id].worked_hours
    Decimal('32.00')
    >>> summary_by_period[leave_period.id].leave_hours
    Decimal('48.00')
    >>> summary_by_period[leave_period.id].entitled_hours
    Decimal('4.00')
    >>> summary_by_period[leave_period.id].total_hours
    Decimal('76.00')
    >>> summary_by_period[leave_period.id].remaining_hours
    Decimal('244.00')
    >>> summary_by_period[leave_period.id].leave_payment_hours
    Decimal('8.00')

    >>> summary_by_period[leave_period2.id].worked_hours
    Decimal('0')
    >>> summary_by_period[leave_period2.id].leave_hours
    Decimal('56.00')
    >>> summary_by_period[leave_period2.id].entitled_hours
    Decimal('0')
    >>> summary_by_period[leave_period2.id].total_hours
    Decimal('56.00')
    >>> summary_by_period[leave_period2.id].remaining_hours
    Decimal('0')
    >>> summary_by_period[leave_period2.id].leave_payment_hours
    Decimal('0')
