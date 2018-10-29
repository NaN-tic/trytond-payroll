================
Payroll Scenario
================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date(2015, 7, 17)  # Make it previsible
    >>> now = datetime.datetime(2015, 7, 17, 10, 0, 0)

Activate payroll::

    >>> config = activate_modules('payroll')

Create company::

    >>> _ = create_company()
    >>> company = get_company()
    >>> party = company.party

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> payable = accounts['payable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> account_cash = accounts['cash']

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create employees::

    >>> Party = Model.get('party.party')
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
    >>> contract.state
    u'draft'

Confirm it:

    >>> contract.click('confirm')
    >>> contract.state
    u'confirmed'

Move to draft it:

    >>> contract.click('draft')
    >>> contract.state
    u'draft'

Cancel it:

    >>> contract.click('cancel')
    >>> contract.state
    u'cancel'

Move to draft it:

    >>> contract.click('draft')
    >>> contract.state
    u'draft'

Confirm it:

    >>> contract.click('confirm')
    >>> contract.state
    u'confirmed'

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
    >>> contract2.state
    u'draft'

Check it can't be confirmed::

    >>> contract2.click('confirm')   # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    UserError: ('UserError', (u'The Payroll Contract "Employee (2015-12-01)" overlaps with existing contract "Employee (2015-01-01)".', ''))

Change contract period to be before the confirmed one::

    >>> contract2.start = today.replace(year=today.year - 1, month=1, day=1)
    >>> contract2.end = today.replace(year=today.year - 1, month=12, day=31)

Confirm it::

    >>> contract2.click('confirm')
    >>> contract2.state
    u'confirmed'

Duplicate it::

    >>> contract3 = Contract(Contract.copy([contract2.id], config.context)[0])
    >>> contract3.state
    u'draft'

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
    >>> line.leave_hours
    Decimal('8.00')
    >>> line.hours_to_do
    Decimal('152.00')
    >>> line.worked_hours
    Decimal('32.00')
    >>> line.generated_entitled_hours
    Decimal('4.00')
    >>> line.remaining_hours
    Decimal('124.00')
    >>> line.leave_payment_hours
    Decimal('8.00')
    >>> line.amount
    Decimal('2880.00')

    >>> payslip.leave_hours
    Decimal('8.00')
    >>> payslip.hours_to_do
    Decimal('152.00')
    >>> payslip.worked_hours
    Decimal('32.00')
    >>> payslip.generated_entitled_hours
    Decimal('4.00')
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
    >>> line.leave_hours
    Decimal('40.00')
    >>> line.hours_to_do
    Decimal('120.00')
    >>> line.worked_hours
    Decimal('0')
    >>> line.generated_entitled_hours
    Decimal('0')
    >>> line.leave_payment_hours
    Decimal('0')
    >>> line.remaining_hours
    Decimal('120.00')
    >>> line.amount
    Decimal('0')

Check employee contract hours summary::

    >>> contract.reload()
    >>> summary_by_period = {s.leave_period.id: s for s in contract.hours_summary}
    >>> summary_by_period[leave_period.id].leave_hours
    Decimal('48.00')
    >>> summary_by_period[leave_period.id].hours_to_do
    Decimal('272.00')
    >>> summary_by_period[leave_period.id].worked_hours
    Decimal('32.00')
    >>> summary_by_period[leave_period.id].entitled_hours
    Decimal('4.00')
    >>> summary_by_period[leave_period.id].remaining_hours
    Decimal('244.00')
    >>> summary_by_period[leave_period.id].leave_payment_hours
    Decimal('8.00')

    >>> summary_by_period[leave_period2.id].leave_hours
    Decimal('56.00')
    >>> summary_by_period[leave_period2.id].hours_to_do
    Decimal('0')
    >>> summary_by_period[leave_period2.id].worked_hours
    Decimal('0')
    >>> summary_by_period[leave_period2.id].entitled_hours
    Decimal('0')
    >>> summary_by_period[leave_period2.id].remaining_hours
    Decimal('0')
    >>> summary_by_period[leave_period2.id].leave_payment_hours
    Decimal('0')
