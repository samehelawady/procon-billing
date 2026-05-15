from django.contrib import admin
from django.forms import TextInput
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    Client, Project, BOQItem, Invoice, InvoiceItem, CompanyProfile, money,
    ExpenseCategory, SubExpense, Expense,
    Employee, PayrollRecord, PayrollAllocation,
    PricingProject, PricingBOQItem
)
from django.urls import reverse
from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.urls import path
from datetime import date, timedelta
from django.contrib import messages
from django.shortcuts import redirect
from django import forms

# --- BRANDING ---
admin.site.site_header = "Procon General Contracting LLC"
admin.site.site_title = "Procon Billing"
admin.site.index_title = "Billing & Project Management Portal"


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_person", "vat_number", "statement_button", "outstanding_button", "progress_button"]

    def statement_button(self, obj):
        url = reverse('admin:client_statement', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background:#2e7d32; color:white; padding: 2px 8px; border-radius: 4px; font-size:10px;">Statement</a>',
            url)
    statement_button.short_description = "Stmt"

    def outstanding_button(self, obj):
        url = reverse('admin:client_outstanding', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background:#ed6c02; color:white; padding: 2px 8px; border-radius: 4px; font-size:10px;">Outstanding</a>',
            url)
    outstanding_button.short_description = "Outst"

    def progress_button(self, obj):
        url = reverse('admin:client_progress', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background:#0288d1; color:white; padding: 2px 8px; border-radius: 4px; font-size:10px;">Progress</a>',
            url)
    progress_button.short_description = "Prog"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:pk>/statement/', self.admin_site.admin_view(self.statement_view), name='client_statement'),
            path('<int:pk>/outstanding/', self.admin_site.admin_view(self.outstanding_view), name='client_outstanding'),
            path('<int:pk>/progress/', self.admin_site.admin_view(self.progress_view), name='client_progress'),
        ]
        return custom + urls

    def _report_wrapper(self, body_html, header_img_url='', footer_img_url=''):
        return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
    @page {{ size: A4 portrait; margin: 18mm 12mm 18mm 12mm;
        @top-center {{ content: element(page-header); vertical-align: top; }}
        @bottom-center {{ content: element(page-footer); vertical-align: bottom; }}
    }}
    #page-header {{ position: running(page-header); width: 100%; text-align: center; margin-bottom: 8px; }}
    #page-header img {{ max-height: 120px; width: 100%; object-fit: contain; }}
    #page-footer {{ position: running(page-footer); width: 100%; text-align: center; margin-top: 8px; }}
    #page-footer img {{ max-height: 90px; width: 100%; object-fit: contain; }}
    * {{ box-sizing: border-box; margin:0; padding:0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    body {{ font-family: "Segoe UI", Arial, sans-serif; font-size: 10px; color: #222; padding: 20px; }}
    .report-title {{ font-size: 18px; font-weight: bold; text-align: center; color: #000080; margin-bottom: 4px; }}
    .report-subtitle {{ font-size: 12px; text-align: center; color: #666; margin-bottom: 15px; }}
    .meta-box {{ background: #f5f5f5; padding: 10px 15px; border-radius: 6px; margin-bottom: 20px; line-height: 1.6; font-size: 10px; }}
    .section-header {{ font-size: 12px; font-weight: bold; color: #000080; margin: 15px 0 8px 0; border-bottom: 2px solid #000080; padding-bottom: 4px; }}
    .report-table {{ width: 100%; border-collapse: collapse; font-size: 9px; margin-top: 6px; }}
    .report-table th {{ background: #e8e8e8; border: 1px solid #999; padding: 5px; text-align: left; font-weight: bold; }}
    .report-table td {{ border: 1px solid #ccc; padding: 5px; }}
    .report-table .num {{ text-align: right; white-space: nowrap; }}
    .report-table tr:nth-child(even) {{ background: #fafafa; }}
    .total-row td {{ background: #e3f2fd; font-weight: bold; border-top: 2px solid #333; }}
    .grand-total-box {{ margin-top: 20px; padding: 12px; background: #000080; color: white; text-align: center; font-size: 14px; border-radius: 6px; }}
    .cards-container {{ display: flex; flex-direction: column; gap: 15px; }}
    .project-card {{ border: 1px solid #ccc; border-radius: 8px; overflow: hidden; page-break-inside: avoid; }}
    .card-header {{ background: #000080; color: white; padding: 8px 12px; font-size: 11px; font-weight: bold; }}
    .card-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 12px; background: #fafafa; }}
    .metric {{ text-align: center; }}
    .metric-label {{ font-size: 8px; color: #666; text-transform: uppercase; margin-bottom: 3px; }}
    .metric-value {{ font-size: 13px; font-weight: bold; }}
    .bar-section {{ padding: 0 12px 12px 12px; background: #fafafa; }}
    .bar-label {{ font-size: 9px; margin-bottom: 4px; font-weight: bold; }}
    .bar-track {{ width: 100%; height: 18px; background: #e0e0e0; border-radius: 9px; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: linear-gradient(90deg, #447e9b, #2e7d32); border-radius: 9px; transition: width 0.5s; }}
    .retention-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; padding: 12px; background: white; }}
    .ret-block {{ border: 1px solid #e0e0e0; border-radius: 6px; padding: 8px; }}
    .ret-title {{ font-size: 9px; font-weight: bold; color: #000080; margin-bottom: 6px; text-align: center; border-bottom: 1px solid #eee; padding-bottom: 4px; }}
    .ret-row {{ display: flex; justify-content: space-between; font-size: 9px; margin-bottom: 3px; }}
</style></head><body>
    <div id="page-header">{"<img src='" + header_img_url + "' alt='Header'>" if header_img_url else ""}</div>
    {body_html}
    <div id="page-footer">{"<img src='" + footer_img_url + "' alt='Footer'>" if footer_img_url else ""}</div>
</body></html>"""

    def statement_view(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        company = CompanyProfile.objects.first()
        header_img_url = company.letter_header.url if company and company.letter_header else ''
        footer_img_url = company.letter_footer.url if company and company.letter_footer else ''
        invoices = Invoice.objects.filter(
            project__client=client, inv_type='T'
        ).exclude(status='Paid').select_related('project').order_by('date')

        rows = ""
        total_net = Decimal("0")
        total_vat = Decimal("0")
        total_gross = Decimal("0")

        for inv in invoices:
            net = inv.current_net_before_vat
            vat = inv.vat_amount
            gross = inv.total_with_vat
            total_net += net
            total_vat += vat
            total_gross += gross
            rows += f"""<tr>
                <td>{inv.date}</td>
                <td>{inv}</td>
                <td>{inv.project.project_name}</td>
                <td>{inv.status}</td>
                <td class='num'>{net:,.2f}</td>
                <td class='num'>{vat:,.2f}</td>
                <td class='num'><b>{gross:,.2f}</b></td>
            </tr>"""

        html = self._report_wrapper(f"""
            <div class="report-title">STATEMENT OF ACCOUNT</div>
            <div class="report-subtitle">Uncollected Tax Invoices</div>
            <div class="meta-box">
                <b>Client:</b> {client.name}<br>
                <b>TRN:</b> {client.vat_number or 'N/A'}<br>
                <b>Date:</b> {date.today().strftime('%d-%b-%Y')}
            </div>
            <table class="report-table">
                <thead>
                    <tr><th>Date</th><th>Invoice #</th><th>Project</th><th>Status</th><th class='num'>Net Amount</th><th class='num'>VAT</th><th class='num'>Total</th></tr>
                </thead>
                <tbody>{rows}</tbody>
                <tfoot>
                    <tr class="total-row">
                        <td colspan="4"><b>TOTAL OUTSTANDING</b></td>
                        <td class='num'>{total_net:,.2f}</td>
                        <td class='num'>{total_vat:,.2f}</td>
                        <td class='num'><b>{total_gross:,.2f}</b></td>
                    </tr>
                </tfoot>
            </table>
        """, header_img_url, footer_img_url)
        return HttpResponse(html)

    def outstanding_view(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        company = CompanyProfile.objects.first()
        header_img_url = company.letter_header.url if company and company.letter_header else ''
        footer_img_url = company.letter_footer.url if company and company.letter_footer else ''
        invoices = Invoice.objects.filter(
            project__client=client
        ).exclude(status='Paid').select_related('project').order_by('date')

        draft_rows = ""
        approved_rows = ""
        total_draft = Decimal("0")
        total_approved = Decimal("0")

        for inv in invoices:
            gross = inv.total_with_vat
            days = (date.today() - inv.date).days
            row = f"""<tr>
                <td>{inv.date}</td>
                <td>{inv}</td>
                <td>{inv.project.project_name}</td>
                <td>{inv.get_inv_type_display()}</td>
                <td class='num'>{gross:,.2f}</td>
                <td class='num'>{days} days</td>
            </tr>"""
            if inv.status == 'Draft':
                draft_rows += row
                total_draft += gross
            else:
                approved_rows += row
                total_approved += gross

        html = self._report_wrapper(f"""
            <div class="report-title">OUTSTANDING INVOICES REPORT</div>
            <div class="meta-box">
                <b>Client:</b> {client.name}<br>
                <b>TRN:</b> {client.vat_number or 'N/A'}<br>
                <b>Date:</b> {date.today().strftime('%d-%b-%Y')}
            </div>

            <div class="section-header">Draft Invoices</div>
            <table class="report-table">
                <thead><tr><th>Date</th><th>Invoice #</th><th>Project</th><th>Type</th><th class='num'>Amount</th><th class='num'>Age</th></tr></thead>
                <tbody>{draft_rows or '<tr><td colspan="6" style="text-align:center;color:#999;">No draft invoices</td></tr>'}</tbody>
                <tfoot><tr class="total-row"><td colspan="4"><b>DRAFT TOTAL</b></td><td class='num'><b>{total_draft:,.2f}</b></td><td></td></tr></tfoot>
            </table>

            <div class="section-header" style="margin-top:20px;">Approved / Sent Invoices</div>
            <table class="report-table">
                <thead><tr><th>Date</th><th>Invoice #</th><th>Project</th><th>Type</th><th class='num'>Amount</th><th class='num'>Age</th></tr></thead>
                <tbody>{approved_rows or '<tr><td colspan="6" style="text-align:center;color:#999;">No approved invoices</td></tr>'}</tbody>
                <tfoot><tr class="total-row"><td colspan="4"><b>APPROVED TOTAL</b></td><td class='num'><b>{total_approved:,.2f}</b></td><td></td></tr></tfoot>
            </table>

            <div class="grand-total-box">
                <b>GRAND TOTAL OUTSTANDING:</b> {(total_draft + total_approved):,.2f}
            </div>
        """, header_img_url, footer_img_url)
        return HttpResponse(html)

    def progress_view(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        company = CompanyProfile.objects.first()
        header_img_url = company.letter_header.url if company and company.letter_header else ''
        footer_img_url = company.letter_footer.url if company and company.letter_footer else ''
        projects = client.projects.all().prefetch_related('invoices', 'boq_items')

        cards = ""
        for proj in projects:
            latest_inv = Invoice.objects.filter(
                project=proj, is_advance_invoice=False
            ).order_by('-inv_number').first()

            work_done = latest_inv.cumulative_work_done if latest_inv else Decimal("0")
            po = proj.po_amount
            balance = money(po - work_done)
            progress_pct = (work_done / po * 100) if po > 0 else Decimal("0")

            ret_a_cum = latest_inv.cumulative_retention_a if latest_inv else Decimal("0")
            ret_b_cum = latest_inv.cumulative_retention_b if latest_inv else Decimal("0")
            ret_a_rec = latest_inv.cumulative_retention_a_recovered if latest_inv else Decimal("0")
            ret_b_rec = latest_inv.cumulative_retention_b_recovered if latest_inv else Decimal("0")
            net_ret = money((ret_a_cum + ret_b_cum) - (ret_a_rec + ret_b_rec))

            adv_rec = latest_inv.cumulative_advance_recovered if latest_inv else Decimal("0")
            adv_total = proj.total_advance_value

            cards += f"""
            <div class="project-card">
                <div class="card-header">{proj.project_id_code} — {proj.project_name}</div>
                <div class="card-grid">
                    <div class="metric">
                        <div class="metric-label">PO Amount</div>
                        <div class="metric-value">{po:,.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Work Done</div>
                        <div class="metric-value" style="color:#2e7d32;">{work_done:,.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Balance</div>
                        <div class="metric-value" style="color:#d32f2f;">{balance:,.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Net Retention Held</div>
                        <div class="metric-value" style="color:#ed6c02;">{net_ret:,.2f}</div>
                    </div>
                </div>

                <div class="bar-section">
                    <div class="bar-label">Progress: {progress_pct:.1f}%</div>
                    <div class="bar-track">
                        <div class="bar-fill" style="width:{min(float(progress_pct),100)}%;"></div>
                    </div>
                </div>

                <div class="retention-grid">
                    <div class="ret-block">
                        <div class="ret-title">Retention A ({proj.retention_a_percent}%)</div>
                        <div class="ret-row"><span>Deducted:</span><span>{ret_a_cum:,.2f}</span></div>
                        <div class="ret-row"><span>Recovered:</span><span style="color:green;">{ret_a_rec:,.2f}</span></div>
                        <div class="ret-row"><span>Held:</span><span style="font-weight:bold;">{money(ret_a_cum - ret_a_rec):,.2f}</span></div>
                    </div>
                    <div class="ret-block">
                        <div class="ret-title">Retention B ({proj.retention_b_percent}%)</div>
                        <div class="ret-row"><span>Deducted:</span><span>{ret_b_cum:,.2f}</span></div>
                        <div class="ret-row"><span>Recovered:</span><span style="color:green;">{ret_b_rec:,.2f}</span></div>
                        <div class="ret-row"><span>Held:</span><span style="font-weight:bold;">{money(ret_b_cum - ret_b_rec):,.2f}</span></div>
                    </div>
                    <div class="ret-block">
                        <div class="ret-title">Advance ({proj.advance_percent}%)</div>
                        <div class="ret-row"><span>Taken:</span><span>{adv_total:,.2f}</span></div>
                        <div class="ret-row"><span>Recovered:</span><span style="color:green;">{adv_rec:,.2f}</span></div>
                        <div class="ret-row"><span>Balance:</span><span style="font-weight:bold;">{money(adv_total - adv_rec):,.2f}</span></div>
                    </div>
                </div>
            </div>
            """

        html = self._report_wrapper(f"""
            <div class="report-title">CLIENT PROJECT PROGRESS</div>
            <div class="meta-box">
                <b>Client:</b> {client.name}<br>
                <b>TRN:</b> {client.vat_number or 'N/A'}<br>
                <b>Date:</b> {date.today().strftime('%d-%b-%Y')}
            </div>
            <div class="cards-container">{cards}</div>
        """, header_img_url, footer_img_url)
        return HttpResponse(html)


class BOQItemInline(admin.TabularInline):
    model = BOQItem
    extra = 1


class ExpenseInlineForm(forms.ModelForm):
    """Custom form that filters boq_item and sub_category based on parent project."""

    class Meta:
        model = Expense
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter boq_item by the parent project (from inline instance or initial)
        project = None

        # If editing existing expense
        if self.instance and self.instance.pk and self.instance.project:
            project = self.instance.project
        # If adding new expense in project inline, get project from parent
        elif self.initial.get('project'):
            try:
                project = Project.objects.get(pk=self.initial['project'])
            except Project.DoesNotExist:
                pass

        if project:
            self.fields['boq_item'].queryset = BOQItem.objects.filter(project=project)
        else:
            self.fields['boq_item'].queryset = BOQItem.objects.none()

        # Filter sub_category by category
        if self.instance and self.instance.pk and self.instance.category:
            self.fields['sub_category'].queryset = SubExpense.objects.filter(parent=self.instance.category)
        else:
            self.fields['sub_category'].queryset = SubExpense.objects.none()


class ExpenseInline(admin.TabularInline):
    model = Expense
    form = ExpenseInlineForm
    extra = 0
    fields = ["date", "category", "sub_category", "amount", "boq_item", "description", "is_allocated"]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj:
            # Store project on formset class for form access
            formset.parent_project = obj
        return formset

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ["company_name", "trn_number", "phone", "bank"]
    fields = ["company_name", "logo", "letter_header", "letter_footer",
              "trn_number", "address", "bank", "phone", "email", "website"]


# =============================================================================
# AJAX ENDPOINTS FOR DYNAMIC DROPDOWNS
# =============================================================================

@admin.register(BOQItem)
class BOQItemAdmin(admin.ModelAdmin):
    search_fields = ["item_number", "description"]
    list_display = ["item_number", "description", "project", "fmt_qty", "fmt_rate", "fmt_total"]

    def fmt_qty(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.quantity:,.2f}</div>')
    fmt_qty.short_description = "Qty"

    def fmt_rate(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.rate:,.2f}</div>')
    fmt_rate.short_description = "Rate"

    def fmt_total(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.quantity * obj.rate:,.2f}</div>')
    fmt_total.short_description = "Total"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('get-by-project/', self.admin_site.admin_view(self.get_by_project), name='boqitem_get_by_project'),
        ]
        return custom + urls

    def get_by_project(self, request):
        from django.http import JsonResponse
        project_id = request.GET.get('project_id')
        if not project_id:
            return JsonResponse([], safe=False)
        items = BOQItem.objects.filter(project_id=project_id).values('id', 'item_number', 'description')
        data = [{'id': item['id'], 'text': f"{item['item_number']} - {item['description'][:40]}"} for item in items]
        return JsonResponse(data, safe=False)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    inlines = [BOQItemInline, ExpenseInline]
    list_display = [
        "project_id_code", "view_invoices", "analytics_button", "cost_profit_button",
        "project_name", "client", "fmt_po",
        "fmt_boq_total", "is_boq_complete", "fmt_advance",
        "fmt_ret_a_pct", "fmt_ret_b_pct"
    ]
    readonly_fields = ["is_boq_complete"]
    search_fields = ["project_id_code", "project_name"]

    def view_invoices(self, obj):
        app_label = obj._meta.app_label
        url = reverse(f'admin:{app_label}_invoice_changelist') + f'?project__id__exact={obj.id}'
        return format_html(
            '<a class="button" href="{}" style="background:#447e9b; color:white; padding: 2px 8px; border-radius: 4px; font-size:10px;">Invoices</a>',
            url)
    view_invoices.short_description = "Action"

    def analytics_button(self, obj):
        url = reverse('admin:project_analytics', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background:#6a1b9a; color:white; padding: 2px 8px; border-radius: 4px; font-size:10px;">Analytics</a>',
            url)
    analytics_button.short_description = "Analytics"

    def cost_profit_button(self, obj):
        url = reverse('admin:project_cost_profit', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background:#d32f2f; color:white; padding: 2px 8px; border-radius: 4px; font-size:10px;">Cost & P&L</a>',
            url)
    cost_profit_button.short_description = "Cost"

    def cost_profit_view(self, request, pk):
        from django.db.models import Sum
        proj = get_object_or_404(Project, pk=pk)
        company = CompanyProfile.objects.first()
        header_img_url = company.letter_header.url if company and company.letter_header else ''
        footer_img_url = company.letter_footer.url if company and company.letter_footer else ''

        latest_inv = Invoice.objects.filter(
            project=proj, is_advance_invoice=False
        ).order_by('-inv_number').first()

        boq_items = BOQItem.objects.filter(project=proj).order_by('item_number')

        rows = ""
        grand_revenue = Decimal("0")
        grand_expenses = Decimal("0")
        grand_profit = Decimal("0")

        for boq in boq_items:
            inv_items = InvoiceItem.objects.filter(
                boq_item=boq,
                invoice__project=proj,
                invoice__is_advance_invoice=False
            )

            cum_qty = inv_items.aggregate(total=Sum('current_qty'))['total'] or Decimal("0")
            cum_amt = inv_items.aggregate(total=Sum('gross_amount'))['total'] or Decimal("0")
            revenue = money(cum_amt)

            direct_expenses = Expense.objects.filter(
                boq_item=boq, project=proj
            ).aggregate(total=Sum('amount'))['total'] or Decimal("0")

            payroll_allocations = PayrollAllocation.objects.filter(
                boq_item=boq, project=proj
            ).aggregate(total=Sum('total_allocated'))['total'] or Decimal("0")

            total_expenses = money(direct_expenses + payroll_allocations)
            profit_loss = money(revenue - total_expenses)
            profit_pct = (profit_loss / revenue * 100) if revenue > 0 else Decimal("0")

            profit_color = "#2e7d32" if profit_loss >= 0 else "#d32f2f"
            profit_icon = "▲" if profit_loss >= 0 else "▼"

            grand_revenue += revenue
            grand_expenses += total_expenses
            grand_profit += profit_loss

            rows += f"""
                <tr>
                    <td class='col-item'>{boq.item_number}</td>
                    <td class='col-desc'>{boq.description}</td>
                    <td class='col-unit'>{boq.unit}</td>
                    <td class='col-num'>{boq.quantity:,.2f}</td>
                    <td class='col-num'>{boq.rate:,.2f}</td>
                    <td class='col-num'>{boq.quantity * boq.rate:,.2f}</td>
                    <td class='col-num'>{cum_qty:,.2f}</td>
                    <td class='col-num' style='color:#000080; font-weight:bold;'>{revenue:,.2f}</td>
                    <td class='col-num' style='color:#ed6c02;'>{direct_expenses:,.2f}</td>
                    <td class='col-num' style='color:#ed6c02;'>{payroll_allocations:,.2f}</td>
                    <td class='col-num' style='font-weight:bold;'>{total_expenses:,.2f}</td>
                    <td class='col-num' style='color:{profit_color}; font-weight:bold; font-size:11px;'>
                        {profit_icon} {profit_loss:,.2f}
                    </td>
                    <td class='col-num' style='color:{profit_color};'>{profit_pct:.1f}%</td>
                </tr>
                """

        grand_profit_pct = (grand_profit / grand_revenue * 100) if grand_revenue > 0 else Decimal("0")
        grand_color = "#2e7d32" if grand_profit >= 0 else "#d32f2f"

        po_amount = proj.po_amount
        total_work_done = latest_inv.cumulative_work_done if latest_inv else Decimal("0")
        balance = money(po_amount - total_work_done)
        progress_pct = (total_work_done / po_amount * 100) if po_amount > 0 else Decimal("0")

        html = f"""<!DOCTYPE html>
    <html><head><meta charset="UTF-8">
    <style>
        @page {{ size: A4 landscape; margin: 15mm 10mm 15mm 10mm;
            @top-center {{ content: element(page-header); vertical-align: top; }}
            @bottom-center {{ content: element(page-footer); vertical-align: bottom; }}
        }}
        #page-header {{ position: running(page-header); width: 100%; text-align: center; margin-bottom: 6px; }}
        #page-header img {{ max-height: 100px; width: 100%; object-fit: contain; }}
        #page-footer {{ position: running(page-footer); width: 100%; text-align: center; margin-top: 6px; }}
        #page-footer img {{ max-height: 80px; width: 100%; object-fit: contain; }}
        * {{ box-sizing: border-box; margin:0; padding:0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        body {{ font-family: "Segoe UI", Arial, sans-serif; font-size: 9px; color: #222; padding: 15px; }}
        .report-title {{ font-size: 20px; font-weight: bold; text-align: center; color: #000080; margin-bottom: 4px; }}
        .report-subtitle {{ font-size: 12px; text-align: center; color: #666; margin-bottom: 12px; }}
        .meta-box {{ background: #f5f5f5; padding: 10px 15px; border-radius: 6px; margin-bottom: 15px; line-height: 1.5; font-size: 10px; display: flex; justify-content: space-between; }}
        .meta-left {{ flex: 1; }}
        .meta-right {{ flex: 1; text-align: right; }}
        .dashboard {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 15px; }}
        .dash-card {{ border: 1px solid #ccc; border-radius: 6px; padding: 10px; text-align: center; background: #fafafa; }}
        .dash-label {{ font-size: 7px; color: #666; text-transform: uppercase; margin-bottom: 4px; }}
        .dash-value {{ font-size: 14px; font-weight: bold; color: #000080; }}
        .dash-sub {{ font-size: 8px; color: #666; margin-top: 3px; }}
        .section-header {{ font-size: 11px; font-weight: bold; color: #000080; margin: 15px 0 6px 0; border-bottom: 2px solid #000080; padding-bottom: 3px; }}
        .report-table {{ width: 100%; border-collapse: collapse; font-size: 8px; margin-top: 4px; }}
        .report-table th {{ background: #e8e8e8; border: 1px solid #999; padding: 4px 3px; font-weight: bold; text-align: center; font-size: 7.5px; }}
        .report-table td {{ border: 1px solid #ccc; padding: 3px 4px; vertical-align: top; }}
        .report-table .num {{ text-align: right; white-space: nowrap; }}
        .report-table tr:nth-child(even) {{ background: #fafafa; }}
        .col-item {{ width: 5%; text-align: center; }}
        .col-desc {{ width: 22%; text-align: left; }}
        .col-unit {{ width: 4%; text-align: center; }}
        .col-num {{ width: 7%; text-align: right; }}
        .total-row td {{ background: #e3f2fd; font-weight: bold; border-top: 2px solid #333; font-size: 9px; }}
        .grand-total-row td {{ background: {grand_color}; color: white; font-weight: bold; border-top: 3px solid #333; font-size: 11px; }}
        .legend {{ margin-top: 10px; padding: 8px; background: #f9f9f9; border-radius: 4px; font-size: 8px; }}
        .legend-item {{ display: inline-block; margin-right: 15px; }}
        .legend-color {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 3px; vertical-align: middle; }}
        .bar-track {{ width: 100%; height: 16px; background: #e0e0e0; border-radius: 8px; overflow: hidden; margin-top: 4px; }}
        .bar-fill {{ height: 100%; background: linear-gradient(90deg, #447e9b, #2e7d32); border-radius: 8px; }}
        @media print {{ .no-print {{ display: none; }} }}
    </style></head><body>
        <div id="page-header">{"<img src='" + header_img_url + "' alt='Header'>" if header_img_url else ""}</div>
        <div class="report-title">PROJECT COST & PROFITABILITY ANALYSIS</div>
        <div class="report-subtitle">{proj.project_id_code} — {proj.project_name}</div>
        <div class="meta-box">
            <div class="meta-left">
                <b>Client:</b> {proj.client.name}<br>
                <b>PO Number:</b> {proj.po_number or 'N/A'}<br>
                <b>PO Amount:</b> {po_amount:,.2f}
            </div>
            <div class="meta-right">
                <b>Report Date:</b> {date.today().strftime('%d-%b-%Y')}<br>
                <b>BOQ Items:</b> {boq_items.count()}<br>
                <b>Project Progress:</b> {progress_pct:.1f}%
            </div>
        </div>
        <div class="dashboard">
            <div class="dash-card"><div class="dash-label">Total Revenue</div><div class="dash-value" style="color:#000080;">{grand_revenue:,.2f}</div></div>
            <div class="dash-card"><div class="dash-label">Total Expenses</div><div class="dash-value" style="color:#ed6c02;">{grand_expenses:,.2f}</div></div>
            <div class="dash-card"><div class="dash-label">Net Profit / Loss</div><div class="dash-value" style="color:{grand_color};">{grand_profit:,.2f}</div></div>
            <div class="dash-card"><div class="dash-label">Profit Margin</div><div class="dash-value" style="color:{grand_color};">{grand_profit_pct:.1f}%</div></div>
            <div class="dash-card"><div class="dash-label">Balance to Complete</div><div class="dash-value" style="color:#d32f2f;">{balance:,.2f}</div><div class="dash-sub">of {po_amount:,.2f} PO</div></div>
        </div>
        <div class="bar-track"><div class="bar-fill" style="width:{min(float(progress_pct), 100)}%;"></div></div>
        <div class="section-header">BOQ Item Cost Breakdown</div>
        <table class="report-table">
            <thead>
                <tr>
                    <th rowspan="2" class="col-item">Item</th>
                    <th rowspan="2" class="col-desc">Description</th>
                    <th rowspan="2" class="col-unit">Unit</th>
                    <th rowspan="2" class="col-num">BOQ Qty</th>
                    <th rowspan="2" class="col-num">Rate</th>
                    <th rowspan="2" class="col-num">BOQ Value</th>
                    <th colspan="2" style="background:#447e9b; color:white;">REVENUE (Work Done)</th>
                    <th colspan="3" style="background:#ed6c02; color:white;">EXPENSES</th>
                    <th colspan="2" style="background:{grand_color}; color:white;">PROFIT / LOSS</th>
                </tr>
                <tr>
                    <th class="col-num">Cum. Qty</th>
                    <th class="col-num">Amount</th>
                    <th class="col-num">Direct</th>
                    <th class="col-num">Payroll</th>
                    <th class="col-num">Total</th>
                    <th class="col-num">Amount</th>
                    <th class="col-num">%</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
            <tfoot>
                <tr class="total-row">
                    <td colspan="7"><b>GRAND TOTALS</b></td>
                    <td class='col-num'><b>{grand_revenue:,.2f}</b></td>
                    <td class='col-num'></td>
                    <td class='col-num'></td>
                    <td class='col-num'><b>{grand_expenses:,.2f}</b></td>
                    <td class='col-num' style='color:{grand_color}; font-size:11px;'><b>{grand_profit:,.2f}</b></td>
                    <td class='col-num' style='color:{grand_color};'><b>{grand_profit_pct:.1f}%</b></td>
                </tr>
            </tfoot>
        </table>
        <div class="legend">
            <div class="legend-item"><span class="legend-color" style="background:#447e9b;"></span> Revenue = Cumulative work done (invoice gross amount)</div>
            <div class="legend-item"><span class="legend-color" style="background:#ed6c02;"></span> Direct Expenses = Costs linked to BOQ item + Payroll allocations</div>
            <div class="legend-item"><span class="legend-color" style="background:#2e7d32;"></span> Profit = Revenue − Expenses</div>
            <div class="legend-item"><span class="legend-color" style="background:#d32f2f;"></span> Loss = Negative profit (expenses exceed revenue)</div>
        </div>
        <div id="page-footer">{"<img src='" + footer_img_url + "' alt='Footer'>" if footer_img_url else ""}</div>
        <script>window.onload = function() {{ window.print(); }}</script>
    </body></html>"""
        return HttpResponse(html)



    def analytics_view(self, request, pk):
        proj = get_object_or_404(Project, pk=pk)
        invoices = Invoice.objects.filter(project=proj).order_by('inv_number')
        boq_items = BOQItem.objects.filter(project=proj).order_by('item_number')
        company = CompanyProfile.objects.first()
        header_img_url = company.letter_header.url if company and company.letter_header else ''
        footer_img_url = company.letter_footer.url if company and company.letter_footer else ''

        inv_rows = ""
        for inv in invoices:
            inv_rows += f"""<tr>
                <td>{inv}</td>
                <td>{inv.get_inv_type_display()}</td>
                <td>{inv.status}</td>
                <td>{inv.date}</td>
                <td class='num'>{inv.current_net_before_vat:,.2f}</td>
                <td class='num'>{inv.vat_amount:,.2f}</td>
                <td class='num'>{inv.total_with_vat:,.2f}</td>
                <td class='num'>{inv.total_after_vat:,.2f}</td>
            </tr>"""

        boq_rows = ""
        boq_total = Decimal("0")
        for b in boq_items:
            line_total = b.quantity * b.rate
            boq_total += line_total
            boq_rows += f"""<tr>
                <td>{b.item_number}</td>
                <td>{b.description[:50]}</td>
                <td>{b.unit}</td>
                <td class='num'>{b.quantity:,.2f}</td>
                <td class='num'>{b.rate:,.2f}</td>
                <td class='num'>{line_total:,.2f}</td>
            </tr>"""

        latest = Invoice.objects.filter(project=proj, is_advance_invoice=False).order_by('-inv_number').first()
        work_done = latest.cumulative_work_done if latest else Decimal("0")
        ret_a = latest.cumulative_retention_a if latest else Decimal("0")
        ret_b = latest.cumulative_retention_b if latest else Decimal("0")
        ret_a_rec = latest.cumulative_retention_a_recovered if latest else Decimal("0")
        ret_b_rec = latest.cumulative_retention_b_recovered if latest else Decimal("0")
        adv_rec = latest.cumulative_advance_recovered if latest else Decimal("0")
        net_inv = latest.net_total_invoiced_cumulative if latest else Decimal("0")

        po = proj.po_amount
        progress_pct = (work_done / po * 100) if po > 0 else Decimal("0")
        balance = money(po - work_done)

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
    @page {{ size: A4 portrait; margin: 18mm 12mm 18mm 12mm;
        @top-center {{ content: element(page-header); vertical-align: top; }}
        @bottom-center {{ content: element(page-footer); vertical-align: bottom; }}
    }}
    #page-header {{ position: running(page-header); width: 100%; text-align: center; margin-bottom: 8px; }}
    #page-header img {{ max-height: 120px; width: 100%; object-fit: contain; }}
    #page-footer {{ position: running(page-footer); width: 100%; text-align: center; margin-top: 8px; }}
    #page-footer img {{ max-height: 90px; width: 100%; object-fit: contain; }}
    * {{ box-sizing: border-box; margin:0; padding:0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    body {{ font-family: "Segoe UI", Arial, sans-serif; font-size: 10px; color: #222; padding: 20px; }}
    .report-title {{ font-size: 18px; font-weight: bold; text-align: center; color: #000080; margin-bottom: 4px; }}
    .report-subtitle {{ font-size: 12px; text-align: center; color: #666; margin-bottom: 15px; }}
    .meta-box {{ background: #f5f5f5; padding: 10px 15px; border-radius: 6px; margin-bottom: 20px; line-height: 1.6; font-size: 10px; }}
    .section-header {{ font-size: 12px; font-weight: bold; color: #000080; margin: 20px 0 8px 0; border-bottom: 2px solid #000080; padding-bottom: 4px; }}
    .report-table {{ width: 100%; border-collapse: collapse; font-size: 9px; margin-top: 6px; }}
    .report-table th {{ background: #e8e8e8; border: 1px solid #999; padding: 5px; text-align: left; font-weight: bold; }}
    .report-table td {{ border: 1px solid #ccc; padding: 5px; }}
    .report-table .num {{ text-align: right; white-space: nowrap; }}
    .report-table tr:nth-child(even) {{ background: #fafafa; }}
    .total-row td {{ background: #e3f2fd; font-weight: bold; border-top: 2px solid #333; }}
    .dashboard {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }}
    .dash-card {{ border: 1px solid #ccc; border-radius: 8px; padding: 12px; text-align: center; background: #fafafa; }}
    .dash-label {{ font-size: 8px; color: #666; text-transform: uppercase; margin-bottom: 6px; }}
    .dash-value {{ font-size: 16px; font-weight: bold; color: #000080; }}
    .dash-sub {{ font-size: 9px; color: #666; margin-top: 4px; }}
    .bar-track {{ width: 100%; height: 22px; background: #e0e0e0; border-radius: 11px; overflow: hidden; margin-top: 6px; }}
    .bar-fill {{ height: 100%; background: linear-gradient(90deg, #447e9b, #2e7d32); border-radius: 11px; }}
    .progress-label {{ text-align: center; font-weight: bold; font-size: 11px; margin-top: 8px; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
    .panel {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px; background: white; }}
    .panel-title {{ font-size: 10px; font-weight: bold; color: #000080; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 6px; }}
    .panel-row {{ display: flex; justify-content: space-between; font-size: 9px; margin-bottom: 5px; }}
    .panel-row b {{ color: #333; }}
</style></head><body>
    <div id="page-header">{"<img src='" + header_img_url + "' alt='Header'>" if header_img_url else ""}</div>
    <div class="report-title">PROJECT ANALYTICS REPORT</div>
    <div class="report-subtitle">{proj.project_id_code} — {proj.project_name}</div>
    <div class="meta-box">
        <b>Client:</b> {proj.client.name} &nbsp;|&nbsp;
        <b>PO Number:</b> {proj.po_number or 'N/A'} &nbsp;|&nbsp;
        <b>PO Date:</b> {proj.po_date or 'N/A'} &nbsp;|&nbsp;
        <b>BOQ Complete:</b> {'Yes' if proj.is_boq_complete else 'No'}
    </div>
    <div class="dashboard">
        <div class="dash-card">
            <div class="dash-label">PO Amount</div>
            <div class="dash-value">{po:,.2f}</div>
        </div>
        <div class="dash-card">
            <div class="dash-label">Work Done</div>
            <div class="dash-value" style="color:#2e7d32;">{work_done:,.2f}</div>
            <div class="dash-sub">{progress_pct:.1f}% complete</div>
        </div>
        <div class="dash-card">
            <div class="dash-label">Balance</div>
            <div class="dash-value" style="color:#d32f2f;">{balance:,.2f}</div>
        </div>
        <div class="dash-card">
            <div class="dash-label">Net Invoiced</div>
            <div class="dash-value">{net_inv:,.2f}</div>
        </div>
        <div class="dash-card">
            <div class="dash-label">Retention Held</div>
            <div class="dash-value" style="color:#ed6c02;">{money(ret_a + ret_b - ret_a_rec - ret_b_rec):,.2f}</div>
            <div class="dash-sub">A: {money(ret_a - ret_a_rec):,.2f} &nbsp; B: {money(ret_b - ret_b_rec):,.2f}</div>
        </div>
        <div class="dash-card">
            <div class="dash-label">Advance Status</div>
            <div class="dash-value">{adv_rec:,.2f}</div>
            <div class="dash-sub">of {proj.total_advance_value:,.2f} recovered</div>
        </div>
    </div>
    <div class="bar-track">
        <div class="bar-fill" style="width:{min(float(progress_pct),100)}%;"></div>
    </div>
    <div class="progress-label">Project Progress: {progress_pct:.1f}%</div>
    <div class="two-col" style="margin-top:20px;">
        <div class="panel">
            <div class="panel-title">Retention Summary</div>
            <div class="panel-row"><span>Retention A Deducted (Cum):</span><b>{ret_a:,.2f}</b></div>
            <div class="panel-row"><span>Retention A Recovered:</span><b style="color:green;">{ret_a_rec:,.2f}</b></div>
            <div class="panel-row"><span>Retention A Held:</span><b>{money(ret_a - ret_a_rec):,.2f}</b></div>
            <div style="height:1px;background:#eee;margin:8px 0;"></div>
            <div class="panel-row"><span>Retention B Deducted (Cum):</span><b>{ret_b:,.2f}</b></div>
            <div class="panel-row"><span>Retention B Recovered:</span><b style="color:green;">{ret_b_rec:,.2f}</b></div>
            <div class="panel-row"><span>Retention B Held:</span><b>{money(ret_b - ret_b_rec):,.2f}</b></div>
        </div>
        <div class="panel">
            <div class="panel-title">Contract Terms</div>
            <div class="panel-row"><span>Advance Percent:</span><b>{proj.advance_percent}%</b></div>
            <div class="panel-row"><span>Retention A Percent:</span><b>{proj.retention_a_percent}%</b></div>
            <div class="panel-row"><span>Retention B Percent:</span><b>{proj.retention_b_percent}%</b></div>
            <div class="panel-row"><span>Total Advance Value:</span><b>{proj.total_advance_value:,.2f}</b></div>
            <div style="height:1px;background:#eee;margin:8px 0;"></div>
            <div class="panel-row"><span>BOQ Items:</span><b>{boq_items.count()}</b></div>
            <div class="panel-row"><span>BOQ Total:</span><b>{proj.boq_total_value:,.2f}</b></div>
            <div class="panel-row"><span>Total Invoices:</span><b>{invoices.count()}</b></div>
        </div>
    </div>
    <div class="section-header">Invoice History</div>
    <table class="report-table">
        <thead>
            <tr><th>Invoice #</th><th>Type</th><th>Status</th><th>Date</th><th class='num'>Net</th><th class='num'>VAT</th><th class='num'>Total</th><th class='num'>Payable</th></tr>
        </thead>
        <tbody>{inv_rows}</tbody>
    </table>
    <div class="section-header">Bill of Quantities</div>
    <table class="report-table">
        <thead>
            <tr><th>Item</th><th>Description</th><th>Unit</th><th class='num'>Qty</th><th class='num'>Rate</th><th class='num'>Total</th></tr>
        </thead>
        <tbody>{boq_rows}</tbody>
        <tfoot>
            <tr class="total-row">
                <td colspan="5"><b>BOQ TOTAL</b></td>
                <td class='num'><b>{boq_total:,.2f}</b></td>
            </tr>
        </tfoot>
    </table>
    <div id="page-footer">{"<img src='" + footer_img_url + "' alt='Footer'>" if footer_img_url else ""}</div>
</body></html>"""

        return HttpResponse(html)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:pk>/analytics/', self.admin_site.admin_view(self.analytics_view), name='project_analytics'),

            path('<int:pk>/cost-profit/', self.admin_site.admin_view(self.cost_profit_view), name='project_cost_profit'),
        ]
        return custom + urls

    def fmt_po(self, obj):
        return mark_safe(f'<div style="text-align: right; font-weight: bold;">{obj.po_amount:,.2f}</div>')
    fmt_po.short_description = 'PO Amount'
    fmt_po.admin_order_field = 'po_amount'

    def fmt_boq_total(self, obj):
        val = obj.boq_total_value
        color = "green" if obj.is_boq_complete else "red"
        return mark_safe(f'<span style="color: {color}; font-weight: bold; float: right;">{val:,.2f}</span>')
    fmt_boq_total.short_description = "BOQ Total"

    def fmt_advance(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.advance_percent:,.2f}%</div>')
    fmt_advance.short_description = "Adv %"
    fmt_advance.admin_order_field = "advance_percent"

    def fmt_ret_a_pct(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.retention_a_percent:,.2f}%</div>')
    fmt_ret_a_pct.short_description = "Ret A %"
    fmt_ret_a_pct.admin_order_field = "retention_a_percent"

    def fmt_ret_b_pct(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.retention_b_percent:,.2f}%</div>')
    fmt_ret_b_pct.short_description = "Ret B %"
    fmt_ret_b_pct.admin_order_field = "retention_b_percent"


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ["rate", "fmt_prev_amt", "fmt_prev_pct", "fmt_gross", "fmt_cum_pct", "fmt_cum_amt", "fmt_ret_a",
                       "fmt_ret_b"]
    fields = [
        "boq_item", "billing_method", "rate",
        "fmt_prev_pct", "fmt_prev_amt",
        "current_percentage", "current_qty", "fmt_gross",
        "fmt_cum_pct", "fmt_cum_amt", "fmt_ret_a", "fmt_ret_b"
    ]

    def fmt_prev_pct(self, obj):
        return mark_safe(f'<div style="text-align:right;">{obj.prev_percentage:,.2f}%</div>')
    fmt_prev_pct.short_description = "Prev %"

    def fmt_prev_amt(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.prev_amount:,.2f}</div>')
    fmt_prev_amt.short_description = "Prev Amt"

    def fmt_gross(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.gross_amount:,.2f}</div>')
    fmt_gross.short_description = "Curr Amt"

    def fmt_cum_pct(self, obj):
        return mark_safe(f'<div style="text-align:right;">{obj.prev_percentage + obj.current_percentage:,.2f}%</div>')
    fmt_cum_pct.short_description = "Cum. %"

    def fmt_cum_amt(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.prev_amount + obj.gross_amount:,.2f}</div>')
    fmt_cum_amt.short_description = "Cum. Amt"

    def fmt_ret_a(self, obj):
        return mark_safe(f'<div style="text-align:right;color:#ed6c02;">{obj.retention_a_amount:,.2f}</div>')
    fmt_ret_a.short_description = "Ret A"

    def fmt_ret_b(self, obj):
        return mark_safe(f'<div style="text-align:right;color:#ed6c02;">{obj.retention_b_amount:,.2f}</div>')
    fmt_ret_b.short_description = "Ret B"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    inlines = [InvoiceItemInline]
    list_display = [
        "fmt_inv_str", "project", "inv_type", "status", "retention_recovery",
        "ui_cumulative_work", "ui_total_invoiced", "ui_previously_invoiced", "ui_subtotal_no_vat",
        "ui_vat", "ui_total_before_deductions", "ui_payable", "print_button"
    ]
    list_filter = ["status", "inv_type", "project", "retention_recovery"]
    search_fields = ["inv_number", "project__project_id_code"]
    readonly_fields = [
        "ui_cumulative_work", "ui_previous_work", "ui_current_work",
        "ui_advance_recovery", "ui_retention_a", "ui_retention_b",
        "ui_retention_a_recovery", "ui_retention_b_recovery",
        "ui_total_invoiced", "ui_previously_invoiced", "ui_subtotal_no_vat",
        "ui_vat", "ui_total_before_deductions", "ui_payable"
    ]

    fieldsets = (
        ("Invoice Details", {
            "fields": ("project", ("inv_type", "status"), ("date", "inv_number"), "revision", ("is_advance_invoice", "retention_recovery"))
        }),
        ("Calculated Billing Summary", {
            "fields": (
                "ui_cumulative_work", "ui_total_invoiced", "ui_previously_invoiced",
                "ui_subtotal_no_vat", "vat_percent", "ui_vat", "ui_total_before_deductions",
                "material_supplied_by_client", "ui_payable"
            )
        }),
    )

    def ui_cumulative_work(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.cumulative_work_done:,.2f}</div>')
    ui_cumulative_work.short_description = "Total Work Done"

    def ui_total_invoiced(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.net_total_invoiced_cumulative:,.2f}</div>')
    ui_total_invoiced.short_description = "Total Invoiced (Cum)"

    def ui_previously_invoiced(self, obj):
        return mark_safe(f'<div style="text-align:right;color:#666;">({obj.previous_net_total_invoiced:,.2f})</div>')
    ui_previously_invoiced.short_description = "Prev Invoiced"

    def ui_subtotal_no_vat(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.current_net_before_vat:,.2f}</div>')
    ui_subtotal_no_vat.short_description = "Sub Total No VAT"

    def ui_vat(self, obj):
        return mark_safe(f'<div style="text-align:right;">{obj.vat_amount:,.2f}</div>')
    ui_vat.short_description = "VAT"

    def ui_total_before_deductions(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.total_with_vat:,.2f}</div>')
    ui_total_before_deductions.short_description = "Total Before Ded."

    def ui_payable(self, obj):
        return mark_safe(f'<div style="text-align:right;"><b style="color:#d32f2f;">{obj.total_after_vat:,.2f}</b></div>')
    ui_payable.short_description = "Payable"

    def ui_previous_work(self, obj):
        return "{:,.2f}".format(obj.previous_work_done)

    def ui_current_work(self, obj):
        return "{:,.2f}".format(obj.current_gross_total)

    def ui_advance_recovery(self, obj):
        return "({:,.2f})".format(obj.current_advance_recovery)

    def ui_retention_a(self, obj):
        return "({:,.2f})".format(obj.current_retention_a)

    def ui_retention_b(self, obj):
        return "({:,.2f})".format(obj.current_retention_b)

    def ui_retention_a_recovery(self, obj):
        if obj.retention_recovery == 'A':
            val = obj.current_retention_a_recovery
            return format_html("<b style='color:green;'>{:,.2f}</b>", val)
        return "0.00"

    ui_retention_a_recovery.short_description = "Ret A Recovery"

    def ui_retention_b_recovery(self, obj):
        if obj.retention_recovery == 'B':
            val = obj.current_retention_b_recovery
            return format_html("<b style='color:green;'>{:,.2f}</b>", val)
        return "0.00"

    ui_retention_b_recovery.short_description = "Ret B Recovery"

    def fmt_inv_str(self, obj):
        return format_html('<div style="font-weight: bold; width:120px;">{}</div>', str(obj))
    fmt_inv_str.short_description = "Invoice ID"

    def print_button(self, obj):
        url = reverse('admin:invoice_print', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background:#447e9b; color:white; padding: 2px 8px; border-radius: 4px;">Print</a>',
            url)
    print_button.short_description = "Report"

    def get_urls(self):
        urls = super().get_urls()
        return [path('<int:pk>/print/', self.admin_site.admin_view(self.print_view), name='invoice_print')] + urls

    def print_view(self, request, pk):
        inv = get_object_or_404(Invoice, pk=pk)
        company = CompanyProfile.objects.first()
        header_title = "PROFORMA INVOICE" if inv.inv_type == "P" else "TAX INVOICE"

        all_boq = BOQItem.objects.filter(project=inv.project).order_by('item_number')
        items_map = {item.boq_item.id: item for item in inv.items.all()}
        rows = ""
        totals = {"prev": Decimal("0"), "curr": Decimal("0"), "cum": Decimal("0")}

        for boq in all_boq:
            item = items_map.get(boq.id)
            if item:
                p_amt, p_pct = item.prev_amount, item.prev_percentage
                c_amt, c_pct = item.gross_amount, item.current_percentage
            else:
                prev_data = InvoiceItem.objects.filter(
                    invoice__project=inv.project,
                    invoice__date__lt=inv.date,
                    boq_item=boq
                ).aggregate(p_amt=Sum('gross_amount'))
                p_amt = prev_data['p_amt'] or Decimal("0")
                p_pct = (p_amt / (boq.quantity * boq.rate) * 100) if (boq.quantity * boq.rate) > 0 else Decimal("0")
                c_pct, c_amt = Decimal("0"), Decimal("0")

            totals["prev"] += p_amt
            totals["curr"] += c_amt
            totals["cum"] += (p_amt + c_amt)

            rows += f"""<tr>
                <td class='col-item'>{boq.item_number}</td>
                <td class='col-desc'>{boq.description}</td>
                <td class='col-unit'>{boq.unit}</td>
                <td class='col-num'>{boq.quantity:,.2f}</td>
                <td class='col-num'>{boq.rate:,.0f}</td>
                <td class='col-num'>{p_pct:,.0f}%</td>
                <td class='col-num'>{p_amt:,.2f}</td>
                <td class='col-num'>{c_pct:,.0f}%</td>
                <td class='col-num'>{c_amt:,.2f}</td>
                <td class='col-num'>{(p_pct + c_pct):,.0f}%</td>
                <td class='col-num'>{(p_amt + c_amt):,.2f}</td>
            </tr>"""

        footer_rows = f"""
            <tr class='total-row'>
                <td colspan='6' class='col-label'>GROSS WORK DONE</td>
                <td class='col-num'>{totals['prev']:,.2f}</td>
                <td></td><td class='col-num'>{totals['curr']:,.2f}</td>
                <td></td><td class='col-num'>{totals['cum']:,.2f}</td>
            </tr>
            <tr>
                <td colspan='6' class='col-label'>Advance Recovery ({inv.project.advance_percent}%)</td>
                <td class='col-num'>({inv.previous_advance_recovered:,.2f})</td>
                <td></td><td class='col-num'>({inv.current_advance_recovery:,.2f})</td>
                <td></td><td class='col-num'>({inv.cumulative_advance_recovered:,.2f})</td>
            </tr>
            <tr>
                <td colspan='6' class='col-label'>Retention A ({inv.project.retention_a_percent}%)</td>
                <td class='col-num'>({inv.previous_retention_a:,.2f})</td>
                <td></td><td class='col-num'>({inv.current_retention_a:,.2f})</td>
                <td></td><td class='col-num'>({inv.cumulative_retention_a:,.2f})</td>
            </tr>
            <tr>
                <td colspan='6' class='col-label'>Retention B ({inv.project.retention_b_percent}%)</td>
                <td class='col-num'>({inv.previous_retention_b:,.2f})</td>
                <td></td><td class='col-num'>({inv.current_retention_b:,.2f})</td>
                <td></td><td class='col-num'>({inv.cumulative_retention_b:,.2f})</td>
            </tr>
        """

        if inv.retention_recovery == 'A':
            footer_rows += f"""
            <tr style='background:#e8f5e9;'>
                <td colspan='6' class='col-label'><b>Retention A Recovery</b></td>
                <td class='col-num'>({inv.previous_retention_a_recovered:,.2f})</td>
                <td></td><td class='col-num'><b>{inv.current_retention_a_recovery:,.2f}</b></td>
                <td></td><td class='col-num'>({inv.cumulative_retention_a_recovered:,.2f})</td>
            </tr>
            """

        if inv.retention_recovery == 'B':
            footer_rows += f"""
            <tr style='background:#e8f5e9;'>
                <td colspan='6' class='col-label'><b>Retention B Recovery</b></td>
                <td class='col-num'>({inv.previous_retention_b_recovered:,.2f})</td>
                <td></td><td class='col-num'><b>{inv.current_retention_b_recovery:,.2f}</b></td>
                <td></td><td class='col-num'>({inv.cumulative_retention_b_recovered:,.2f})</td>
            </tr>
            """

        footer_rows += f"""
            <tr class='grand-total-row'>
                <td colspan='6' class='col-label'>TOTAL</td>
                <td class='col-num'>{inv.previous_net_total_invoiced:,.2f}</td>
                <td></td><td class='col-num'>{inv.current_net_before_vat:,.2f}</td>
                <td></td><td class='col-num'>{inv.net_total_invoiced_cumulative:,.2f}</td>
            </tr>
        """

        header_img_url = company.letter_header.url if company and company.letter_header else ''
        footer_img_url = company.letter_footer.url if company and company.letter_footer else ''
        logo_url = company.logo.url if company and company.logo else ''

        html = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: A4 landscape;
            margin: 18mm 10mm 18mm 10mm;
            @top-center {{ content: element(page-header); vertical-align: top; }}
            @bottom-center {{ content: element(page-footer); vertical-align: bottom; }}
        }}
        #page-header {{ position: running(page-header); width: 100%; text-align: center; margin-bottom: 8px; }}
        #page-header img {{ max-height: 130px; width: 100%; object-fit: contain; }}
        #page-footer {{ position: running(page-footer); width: 100%; text-align: center; margin-top: 8px; }}
        #page-footer img {{ max-height: 100px; width: 100%; object-fit: contain; }}
        * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; margin: 0; padding: 0; }}
        body {{ font-family: "Segoe UI", Arial, Helvetica, sans-serif; font-size: 8.5px; line-height: 1.3; color: #222; width: 100%; }}
        .watermark {{ position: fixed; top: 10%; left: 50%; transform: translate(-50%, -50%); width: 550px; opacity: 0.0; z-index: -1; pointer-events: none; }}
        .watermark img {{ width: 100%; }}
        .invoice-title {{ font-size: 15px; font-weight: bold; text-align: center; margin: 8px 0 12px 0; color: #000080; letter-spacing: 1px; }}
        .invoice-meta {{ margin-bottom: 10px; }}
        .invoice-meta-row {{ font-size: 11px; font-weight: bold; margin-bottom: 4px; }}
        .parties-row {{ display: flex; justify-content: space-between; margin: 10px 0; gap: 20px; }}
        .party-block {{ flex: 1; }}
        .party-name {{ font-size: 13px; font-weight: bold; margin-bottom: 3px; }}
        .party-detail {{ font-size: 10px; margin-bottom: 2px; }}
        .project-name {{ font-size: 10px; margin: 8px 0 10px 0; }}
        .section-title {{ text-align: center; font-size: 13px; font-weight: bold; margin: 8px 0 6px 0; color: #111; }}
        .boq-table {{ width: 100%; max-width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 8px; table-layout: fixed; }}
        .boq-table thead {{ display: table-header-group; }}
        .boq-table th {{ background: #e8e8e8; border: 1px solid #666; padding: 4px 2px; font-weight: bold; text-align: center; font-size: 7.5px; word-wrap: break-word; }}
        .boq-table td {{ border: 1px solid #666; padding: 3px 4px; vertical-align: top; }}
        .col-item {{ width: 4%; text-align: center; }}
        .col-desc {{ width: 32%; text-align: left; }}
        .col-unit {{ width: 5%; text-align: center; }}
        .col-num {{ width: 6.5%; text-align: right; white-space: nowrap; }}
        .col-label {{ text-align: right; font-weight: bold; padding-right: 8px; }}
        .boq-table td.col-desc {{ font-size: 6px; line-height: 1.2; word-wrap: break-word; overflow-wrap: break-word; hyphens: auto; }}
        .total-row td {{ font-weight: bold; background: #f0f0f0; border-top: 2px solid #333; }}
        .grand-total-row td {{ font-weight: bold; background: #f5f5f5; border-top: 2px solid #333; border-bottom: 2px solid #333; }}
        .boq-table tr {{ page-break-inside: avoid; }}
        .summary-wrapper {{ display: flex; justify-content: space-between; margin-top: 15px; gap: 15px; page-break-inside: avoid; }}
        .summary-box {{ border: 1px solid #666; padding: 8px 12px; }}
        .summary-box.bank {{ flex: 1; max-width: 45%; }}
        .summary-box.totals {{ flex: 1; max-width: 45%; margin-left: auto; }}
        .summary-box-title {{ font-weight: bold; margin-bottom: 5px; text-decoration: underline; font-size: 9px; }}
        .summary-row {{ display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 9px; }}
        .summary-row.border-top {{ border-top: 1px solid #333; margin-top: 5px; padding-top: 5px; }}
        .red-text {{ color: #000080; font-weight: bold; font-size: 1.4em; }}
        .bank-content {{ font-family: "Courier New", monospace; font-size: 10px; font-weight: bold; color: #000080; line-height: 1.4; }}
        .page-break-avoid {{ page-break-inside: avoid; }}
        @media print {{
            #page-header {{ position: fixed; top: 0; left: 0; right: 0; }}
            #page-footer {{ position: fixed; bottom: 0; left: 0; right: 0; }}
            body {{ padding-top: 140px; padding-bottom: 110px; }}
        }}
    </style>
    </head>
    <body>
        <div class="watermark">
            {"<img src='" + logo_url + "' alt='Watermark'>" if logo_url else ""}
        </div>
        <div id="page-header">
            {"<img src='" + header_img_url + "' alt='Header'>" if header_img_url else ""}
        </div>
        <div class="invoice-title">{header_title}</div>
        <div class="invoice-meta">
            <div class="invoice-meta-row">Invoice Number: {inv}</div>
            <br>
            <div class="invoice-meta-row">Date : {inv.date}</div>
            <br>
            <div class="invoice-meta-row">PO Number : {getattr(inv.project, 'po_number', 'N/A')}</div>
        </div>
        <div class="parties-row">
            <div class="party-block">
                <div class="party-name">{company.company_name if company else ''}</div>
                <div class="party-detail"><strong>TRN:</strong> {company.trn_number if company and company.trn_number else 'N/A'}</div>
                <br>
                <div class="party-name">{inv.project.client.name}</div>
                <div class="party-detail"><strong>TRN:</strong> {inv.project.client.vat_number or 'N/A'}</div>
            </div>
        </div>
        <div class="project-name"><strong>Project:</strong> {inv.project.project_name}</div>
        <div class="section-title">PROGRESS PAYMENT</div>
        <table class="boq-table">
            <thead>
                <tr>
                    <th rowspan="2" class="col-item">Item</th>
                    <th rowspan="2" class="col-desc">Description</th>
                    <th rowspan="2" class="col-unit">Unit</th>
                    <th rowspan="2" class="col-num">BOQ<br>Qty</th>
                    <th rowspan="2" class="col-num">Rate</th>
                    <th colspan="2">Previous</th>
                    <th colspan="2">Current</th>
                    <th colspan="2">Cumulative</th>
                </tr>
                <tr>
                    <th class="col-num">%</th>
                    <th class="col-num">Amt</th>
                    <th class="col-num">%</th>
                    <th class="col-num">Amt</th>
                    <th class="col-num">%</th>
                    <th class="col-num">Amt</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
            <tfoot>{footer_rows}</tfoot>
        </table>
        <div class="summary-wrapper">
            <div class="summary-box bank">
                <div class="summary-box-title">Bank Account Details:</div>
                <div class="bank-content">
                    {company.bank if company and company.bank else ''}
                </div>
            </div>
            <div class="summary-box totals">
                <div class="summary-row"><span>Total Invoiced (Cumulative):</span><span>{inv.net_total_invoiced_cumulative:,.2f}</span></div>
                <div class="summary-row"><span>Previously Invoiced:</span><span>({inv.previous_net_total_invoiced:,.2f})</span></div>
                <div class="summary-row border-top" style="font-weight:bold;"><span>Sub Total Before VAT:</span><span>{inv.current_net_before_vat:,.2f}</span></div>
                <div class="summary-row"><span>VAT ({inv.vat_percent}%):</span><span>{inv.vat_amount:,.2f}</span></div>
                <div class="summary-row" style="font-weight:bold;"><span>Total Before Deductions:</span><span>{inv.total_with_vat:,.2f}</span></div>
                <div class="summary-row"><span>Deductions (Materials from Client):</span><span>({inv.material_supplied_by_client:,.2f})</span></div>
                <div class="summary-row border-top red-text"><span>Payable Amount:</span><span>{inv.total_after_vat:,.2f}</span></div>
            </div>
        </div>
        <div id="page-footer">
            {"<img src='" + footer_img_url + "' alt='Footer'>" if footer_img_url else ""}
        </div>
        <script>window.onload = function() {{ window.print(); }}</script>
    </body>
    </html>"""
        return HttpResponse(html)


# =============================================================================
# EXPENSE ADMIN
# =============================================================================

class SubExpenseInline(admin.TabularInline):
    model = SubExpense
    extra = 1


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "sub_expense_count"]
    inlines = [SubExpenseInline]
    search_fields = ["name"]

    def sub_expense_count(self, obj):
        return obj.sub_expenses.count()
    sub_expense_count.short_description = "Sub-Expenses"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('subexpense/get-by-category/', self.admin_site.admin_view(self.get_subexpenses), name='subexpense_get_by_category'),
        ]
        return custom + urls

    def get_subexpenses(self, request):
        from django.http import JsonResponse
        category_id = request.GET.get('category_id')
        if not category_id:
            return JsonResponse([], safe=False)
        items = SubExpense.objects.filter(parent_id=category_id).values('id', 'name')
        data = [{'id': item['id'], 'text': item['name']} for item in items]
        return JsonResponse(data, safe=False)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["date", "project", "category", "sub_category", "fmt_amount", "boq_item", "is_allocated"]
    list_filter = ["project", "category", "date", "is_allocated"]
    search_fields = ["description", "reference_number"]
    autocomplete_fields = ["project"]

    class Media:
        js = ('admin/js/vendor/jquery/jquery.min.js', 'admin/js/jquery.init.js', 'admin/js/expense_boq_filter.js')

    def fmt_amount(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.amount:,.2f}</div>')

    fmt_amount.short_description = "Amount"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Filter sub_category by selected category (on both add and change)
        if obj and obj.category:
            form.base_fields['sub_category'].queryset = SubExpense.objects.filter(parent=obj.category)
        else:
            form.base_fields['sub_category'].queryset = SubExpense.objects.none()

        # Filter boq_item by selected project (on both add and change)
        if obj and obj.project:
            form.base_fields['boq_item'].queryset = BOQItem.objects.filter(project=obj.project)
        else:
            form.base_fields['boq_item'].queryset = BOQItem.objects.none()

        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # This runs AFTER the form is instantiated, so we use it for change form
        if db_field.name == "boq_item":
            if request.resolver_match and request.resolver_match.kwargs.get('object_id'):
                obj = self.get_object(request, request.resolver_match.kwargs['object_id'])
                if obj and obj.project:
                    kwargs["queryset"] = BOQItem.objects.filter(project=obj.project)
                else:
                    kwargs["queryset"] = BOQItem.objects.none()
            else:
                kwargs["queryset"] = BOQItem.objects.none()

        elif db_field.name == "sub_category":
            if request.resolver_match and request.resolver_match.kwargs.get('object_id'):
                obj = self.get_object(request, request.resolver_match.kwargs['object_id'])
                if obj and obj.category:
                    kwargs["queryset"] = SubExpense.objects.filter(parent=obj.category)
                else:
                    kwargs["queryset"] = SubExpense.objects.none()
            else:
                kwargs["queryset"] = SubExpense.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =============================================================================
# EMPLOYEE & PAYROLL ADMIN
# =============================================================================

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        "employee_id", "name", "employee_type", "payment_type",
        "cost_center", "fmt_total_salary", "fmt_daily_cost", "is_active"
    ]
    list_filter = ["employee_type", "payment_type", "is_head_office", "is_active", "project"]
    search_fields = ["name", "employee_id"]
    fieldsets = (
        ("Employee Information", {
            "fields": (
                ("employee_id", "name"),
                ("employee_type", "payment_type"),
                ("project", "is_head_office"),
                ("is_active", "date_joined"),
            )
        }),
        ("Salary Components", {
            "fields": (
                ("basic_salary", "housing_allowance"),
                ("transport_allowance", "other_allowances"),
            )
        }),
        ("Annual Administrative Costs", {
            "fields": (
                ("annual_benefits", "annual_eid_cost"),
                ("annual_visa_cost", "annual_ticket_cost"),
            ),
            "description": "These are summed and divided by 12 to produce the monthly admin cost."
        }),
    )

    def cost_center(self, obj):
        if obj.is_head_office:
            return mark_safe('<b style="color:#000080;">HEAD OFFICE</b>')
        return obj.project.project_id_code if obj.project else mark_safe('<span style="color:#999;">—</span>')
    cost_center.short_description = "Cost Center"

    def fmt_total_salary(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.total_salary:,.2f}</div>')
    fmt_total_salary.short_description = "Total Salary"

    def fmt_daily_cost(self, obj):
        return mark_safe(f'<div style="text-align:right;color:#2e7d32;font-weight:bold;">{obj.daily_cost:,.2f}</div>')
    fmt_daily_cost.short_description = "Daily Cost"


class PayrollAllocationInline(admin.TabularInline):
    model = PayrollAllocation
    extra = 0
    readonly_fields = [
        "project", "boq_item", "salary_allocated", "admin_cost_allocated",
        "total_allocated", "project_work_done_pct", "boq_item_work_done_pct", "created_at"
    ]
    can_delete = False


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    inlines = [PayrollAllocationInline]
    list_display = [
        "employee", "month", "fmt_total_salary", "fmt_overtime", "fmt_absence",
        "fmt_advance", "fmt_other_ded", "fmt_net_salary", "allocation_status"
    ]
    list_filter = ["month", "is_allocated", "employee__employee_type", "employee__payment_type"]
    search_fields = ["employee__name", "employee__employee_id"]
    actions = ["allocate_selected"]
    date_hierarchy = "month"

    def fmt_total_salary(self, obj):
        return mark_safe(f'<div style="text-align:right;">{obj.total_salary_snap:,.2f}</div>')
    fmt_total_salary.short_description = "Total Salary"

    def fmt_overtime(self, obj):
        if obj.employee.employee_type == 'Site':
            return mark_safe(f'<div style="text-align:right;">{obj.overtime_hours}h / {obj.overtime_amount_snap:,.2f}</div>')
        return mark_safe('<span style="color:#999;">—</span>')
    fmt_overtime.short_description = "OT (Hrs/Amt)"

    def fmt_absence(self, obj):
        return mark_safe(f'<div style="text-align:right;color:#d32f2f;">({obj.absence_deduction_snap:,.2f})</div>')
    fmt_absence.short_description = "Absence"

    def fmt_advance(self, obj):
        return mark_safe(f'<div style="text-align:right;color:#d32f2f;">({obj.salary_advance:,.2f})</div>')
    fmt_advance.short_description = "Advance"

    def fmt_other_ded(self, obj):
        return mark_safe(f'<div style="text-align:right;color:#d32f2f;">({obj.other_deduction:,.2f})</div>')
    fmt_other_ded.short_description = "Other Ded."

    def fmt_net_salary(self, obj):
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{obj.net_salary_snap:,.2f}</div>')
    fmt_net_salary.short_description = "Net Salary"

    def allocation_status(self, obj):
        if obj.is_allocated:
            return mark_safe('<b style="color:#2e7d32;">ALLOCATED</b>')
        return mark_safe('<b style="color:#d32f2f;">PENDING</b>')
    allocation_status.short_description = "Status"

    @admin.action(description="Allocate selected payroll to projects / BOQ items")
    def allocate_selected(self, request, queryset):
        from .models import allocate_payroll
        done = 0
        skipped = 0
        for rec in queryset:
            if rec.is_allocated:
                skipped += 1
                continue
            if allocate_payroll(rec):
                done += 1
            else:
                skipped += 1
        self.message_user(request, f"Allocated: {done} | Skipped/Failed: {skipped}")

    def changelist_view(self, request, extra_context=None):
        today = date.today()
        first_day = today.replace(day=1)
        last_month = (first_day - timedelta(days=1)).replace(day=1)

        unallocated = PayrollRecord.objects.filter(month=last_month, is_allocated=False).count()
        if unallocated > 0:
            messages.warning(
                request,
                mark_safe(
                    f"<b>PAYROLL ALERT:</b> {unallocated} record(s) for <b>{last_month.strftime('%b %Y')}</b> "
                    f"are not yet allocated to projects. "
                    f"<a href='allocate/' style='color:#d32f2f; text-decoration:underline; font-weight:bold;'>Allocate Now →</a>"
                )
            )
        return super().changelist_view(request, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("allocate/", self.admin_site.admin_view(self.allocate_view), name="payroll_allocate"),
            path("reports/staff/", self.admin_site.admin_view(self.staff_report), name="payroll_staff_report"),
            path("reports/wps/", self.admin_site.admin_view(self.wps_report), name="payroll_wps_report"),
            path("reports/cash/", self.admin_site.admin_view(self.cash_report), name="payroll_cash_report"),
        ]
        return custom + urls

    def allocate_view(self, request):
        today = date.today()
        first_day = today.replace(day=1)
        last_month = (first_day - timedelta(days=1)).replace(day=1)

        unallocated = PayrollRecord.objects.filter(
            month=last_month, is_allocated=False
        ).select_related("employee")

        if request.method == "POST":
            action = request.POST.get("action")
            if action == "yes":
                from .models import allocate_payroll
                done = 0
                for rec in unallocated:
                    if allocate_payroll(rec):
                        done += 1
                messages.success(request, f"{done} payroll record(s) allocated successfully.")
                return redirect("..")
            else:
                messages.info(request, "Allocation postponed. You will be reminded again.")
                return redirect("..")

        rows = ""
        total_net = Decimal("0")
        for rec in unallocated:
            total_net += rec.net_salary_snap
            rows += f"""<tr>
                <td>{rec.employee.employee_id}</td>
                <td>{rec.employee.name}</td>
                <td>{rec.employee.get_employee_type_display()}</td>
                <td>{rec.employee.get_payment_type_display()}</td>
                <td class='num'>{rec.net_salary_snap:,.2f}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
    body {{ font-family: "Segoe UI", Arial, sans-serif; font-size: 12px; padding: 40px; background: #f5f5f5; }}
    .box {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    h2 {{ color: #000080; margin-bottom: 10px; }}
    .subtitle {{ color: #666; margin-bottom: 25px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 11px; }}
    th {{ background: #e8e8e8; border: 1px solid #999; padding: 8px; text-align: left; }}
    td {{ border: 1px solid #ccc; padding: 8px; }}
    .num {{ text-align: right; }}
    .actions {{ margin-top: 25px; display: flex; gap: 15px; }}
    .btn {{ padding: 12px 30px; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; font-weight: bold; }}
    .btn-yes {{ background: #2e7d32; color: white; }}
    .btn-no {{ background: #ed6c02; color: white; }}
    .total-row td {{ font-weight: bold; background: #e3f2fd; border-top: 2px solid #333; }}
</style></head><body>
    <div class="box">
        <h2>Monthly Payroll Allocation</h2>
        <div class="subtitle">Month: {last_month.strftime('%B %Y')} | Unallocated Records: {unallocated.count()}</div>
        <table>
            <thead>
                <tr><th>Emp ID</th><th>Name</th><th>Type</th><th>Payment</th><th class='num'>Net Salary</th></tr>
            </thead>
            <tbody>{rows}</tbody>
            <tfoot>
                <tr class="total-row">
                    <td colspan="4"><b>TOTAL NET TO ALLOCATE</b></td>
                    <td class='num'><b>{total_net:,.2f}</b></td>
                </tr>
            </tfoot>
        </table>
        <div style="background:#fff3cd; padding:12px; border-radius:6px; margin-bottom:20px; border-left:4px solid #ed6c02;">
            <b>Head Office employees</b> will be distributed across projects based on monthly work-done percentages.<br>
            <b>Project employees</b> will be allocated directly to their project's BOQ items.
        </div>
        <form method="post">
            <div class="actions">
                <button type="submit" name="action" value="yes" class="btn btn-yes">YES — Allocate Now</button>
                <button type="submit" name="action" value="no" class="btn btn-no">NO — Remind Me Tomorrow</button>
            </div>
        </form>
    </div>
</body></html>"""
        return HttpResponse(html)

    def staff_report(self, request):
        month = request.GET.get("month")
        qs = PayrollRecord.objects.filter(
            employee__employee_type="Staff",
            employee__payment_type="Bank"
        ).select_related("employee").order_by("-month")
        if month:
            qs = qs.filter(month=month)

        rows = ""
        totals = {"basic": Decimal("0"), "housing": Decimal("0"), "transport": Decimal("0"),
                  "other": Decimal("0"), "total": Decimal("0"), "absence": Decimal("0"),
                  "advance": Decimal("0"), "other_ded": Decimal("0"), "net": Decimal("0")}

        for rec in qs:
            rows += f"""<tr>
                <td>{rec.employee.employee_id}</td>
                <td>{rec.employee.name}</td>
                <td class='num'>{rec.basic_salary_snap:,.2f}</td>
                <td class='num'>{rec.housing_allowance_snap:,.2f}</td>
                <td class='num'>{rec.transport_allowance_snap:,.2f}</td>
                <td class='num'>{rec.other_allowances_snap:,.2f}</td>
                <td class='num'><b>{rec.total_salary_snap:,.2f}</b></td>
                <td class='num'>({rec.absence_deduction_snap:,.2f})</td>
                <td class='num'>({rec.salary_advance:,.2f})</td>
                <td class='num'>({rec.other_deduction:,.2f})</td>
                <td class='num'><b>{rec.net_salary_snap:,.2f}</b></td>
            </tr>"""
            totals["basic"] += rec.basic_salary_snap
            totals["housing"] += rec.housing_allowance_snap
            totals["transport"] += rec.transport_allowance_snap
            totals["other"] += rec.other_allowances_snap
            totals["total"] += rec.total_salary_snap
            totals["absence"] += rec.absence_deduction_snap
            totals["advance"] += rec.salary_advance
            totals["other_ded"] += rec.other_deduction
            totals["net"] += rec.net_salary_snap

        html = self._payroll_report_wrapper(
            "OFFICE STAFF PAYROLL REPORT",
            ["Emp ID", "Name", "Basic", "Housing", "Transport", "Other", "Total", "Absence", "Advance", "Other Ded.", "Net"],
            rows, totals, "Bank Transfer"
        )
        return HttpResponse(html)

    def wps_report(self, request):
        month = request.GET.get("month")
        qs = PayrollRecord.objects.filter(
            employee__employee_type="Site",
            employee__payment_type="WPS"
        ).select_related("employee").order_by("-month")
        if month:
            qs = qs.filter(month=month)

        rows = ""
        totals = {"total": Decimal("0"), "ot": Decimal("0"), "absence": Decimal("0"),
                  "advance": Decimal("0"), "other_ded": Decimal("0"), "net": Decimal("0")}

        for rec in qs:
            rows += f"""<tr>
                <td>{rec.employee.employee_id}</td>
                <td>{rec.employee.name}</td>
                <td class='num'>{rec.total_salary_snap:,.2f}</td>
                <td class='num'>{rec.overtime_hours}h</td>
                <td class='num'>{rec.overtime_amount_snap:,.2f}</td>
                <td class='num'>({rec.absence_deduction_snap:,.2f})</td>
                <td class='num'>({rec.salary_advance:,.2f})</td>
                <td class='num'>({rec.other_deduction:,.2f})</td>
                <td class='num'><b>{rec.net_salary_snap:,.2f}</b></td>
            </tr>"""
            totals["total"] += rec.total_salary_snap
            totals["ot"] += rec.overtime_amount_snap
            totals["absence"] += rec.absence_deduction_snap
            totals["advance"] += rec.salary_advance
            totals["other_ded"] += rec.other_deduction
            totals["net"] += rec.net_salary_snap

        html = self._payroll_report_wrapper(
            "SITE WORKERS PAYROLL REPORT (WPS)",
            ["Emp ID", "Name", "Total Salary", "OT Hrs", "OT Amt", "Absence", "Advance", "Other Ded.", "Net"],
            rows, totals, "WPS Agency"
        )
        return HttpResponse(html)

    def cash_report(self, request):
        month = request.GET.get("month")
        qs = PayrollRecord.objects.filter(
            employee__payment_type="Cash"
        ).select_related("employee").order_by("-month")
        if month:
            qs = qs.filter(month=month)

        rows = ""
        total_net = Decimal("0")
        for rec in qs:
            total_net += rec.net_salary_snap
            rows += f"""<tr>
                <td>{rec.employee.employee_id}</td>
                <td>{rec.employee.name}</td>
                <td>{rec.employee.get_employee_type_display()}</td>
                <td class='num'>{rec.net_salary_snap:,.2f}</td>
                <td style='width:120px; border-bottom:1px solid #333;'></td>
            </tr>"""

        html = self._payroll_report_wrapper(
            "CASH PAYROLL REPORT",
            ["Emp ID", "Name", "Type", "Net Amount", "Signature"],
            rows, {"net": total_net}, "Cash"
        )
        return HttpResponse(html)

    def _payroll_report_wrapper(self, title, headers, rows, totals, payment_method):
        header_cells = "".join(f"<th>{h}</th>" for h in headers)
        total_row = ""
        if "basic" in totals:
            total_row = f"""<tr class='total-row'>
                <td colspan='2'><b>TOTAL</b></td>
                <td class='num'>{totals['basic']:,.2f}</td>
                <td class='num'>{totals['housing']:,.2f}</td>
                <td class='num'>{totals['transport']:,.2f}</td>
                <td class='num'>{totals['other']:,.2f}</td>
                <td class='num'><b>{totals['total']:,.2f}</b></td>
                <td class='num'>({totals['absence']:,.2f})</td>
                <td class='num'>({totals['advance']:,.2f})</td>
                <td class='num'>({totals['other_ded']:,.2f})</td>
                <td class='num'><b>{totals['net']:,.2f}</b></td>
            </tr>"""
        elif "ot" in totals:
            total_row = f"""<tr class='total-row'>
                <td colspan='2'><b>TOTAL</b></td>
                <td class='num'>{totals['total']:,.2f}</td>
                <td></td>
                <td class='num'>{totals['ot']:,.2f}</td>
                <td class='num'>({totals['absence']:,.2f})</td>
                <td class='num'>({totals['advance']:,.2f})</td>
                <td class='num'>({totals['other_ded']:,.2f})</td>
                <td class='num'><b>{totals['net']:,.2f}</b></td>
            </tr>"""
        else:
            total_row = f"""<tr class='total-row'>
                <td colspan='3'><b>TOTAL</b></td>
                <td class='num'><b>{totals['net']:,.2f}</b></td>
                <td></td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
    body {{ font-family: "Segoe UI", Arial, sans-serif; font-size: 10px; padding: 20px; }}
    .report-title {{ font-size: 18px; font-weight: bold; text-align: center; color: #000080; margin-bottom: 4px; }}
    .report-sub {{ font-size: 12px; text-align: center; color: #666; margin-bottom: 15px; }}
    .meta-box {{ background: #f5f5f5; padding: 10px 15px; border-radius: 6px; margin-bottom: 20px; line-height: 1.6; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 9px; margin-top: 6px; }}
    th {{ background: #e8e8e8; border: 1px solid #999; padding: 6px; text-align: left; font-weight: bold; }}
    td {{ border: 1px solid #ccc; padding: 5px; }}
    .num {{ text-align: right; white-space: nowrap; }}
    tr:nth-child(even) {{ background: #fafafa; }}
    .total-row td {{ background: #e3f2fd; font-weight: bold; border-top: 2px solid #333; }}
</style></head><body>
    <div class="report-title">{title}</div>
    <div class="report-sub">Payment Method: {payment_method} | Generated: {date.today().strftime('%d-%b-%Y')}</div>
    <div class="meta-box">
        <b>Report Type:</b> {title}<br>
        <b>Date:</b> {date.today().strftime('%d-%b-%Y')}
    </div>
    <table>
        <thead><tr>{header_cells}</tr></thead>
        <tbody>{rows}</tbody>
        <tfoot>{total_row}</tfoot>
    </table>
    <script>window.onload = function() {{ window.print(); }}</script>
</body></html>"""


# =============================================================================
# PRICING ADMIN
# =============================================================================

class PricingBOQItemInline(admin.TabularInline):
    model = PricingBOQItem
    extra = 1
    fields = [
        "item_number", "description", "unit", "estimated_quantity",
        "reference_boq_item", "historical_rate", "historical_cost", "proposed_rate", "proposed_total"
    ]
    readonly_fields = ["historical_rate", "historical_cost", "proposed_total"]


@admin.register(PricingProject)
class PricingProjectAdmin(admin.ModelAdmin):
    inlines = [PricingBOQItemInline]
    list_display = ["project_name", "client", "created_date", "fmt_total"]
    search_fields = ["project_name", "client__name"]
    filter_horizontal = ["reference_projects"]

    def fmt_total(self, obj):
        total = sum(item.proposed_total for item in obj.boq_items.all())
        return mark_safe(f'<div style="text-align:right;font-weight:bold;">{total:,.2f}</div>')
    fmt_total.short_description = "Proposed Total"