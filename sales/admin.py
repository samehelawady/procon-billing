from django.contrib import admin
from django.forms import TextInput
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Client, Project, BOQItem, Invoice, InvoiceItem, CompanyProfile, money
from django.urls import reverse
from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.urls import path
from datetime import date


# --- BRANDING ---
admin.site.site_header = "Procon General Contracting LLC"
admin.site.site_title = "Procon Billing"
admin.site.index_title = "Billing & Project Management Portal"


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_person", "vat_number", "statement_button", "outstanding_button", "progress_button"]

    # -----------------------------------------------------------------
    # REPORT BUTTONS
    # -----------------------------------------------------------------
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

    # -----------------------------------------------------------------
    # REPORT VIEWS
    # -----------------------------------------------------------------
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


# =============================================================================
@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ["company_name", "trn_number", "phone","bank"]


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


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    inlines = [BOQItemInline]
    list_display = [
        "project_id_code", "view_invoices", "analytics_button", "project_name", "client", "fmt_po",
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

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:pk>/analytics/', self.admin_site.admin_view(self.analytics_view), name='project_analytics'),
        ]
        return custom + urls

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

    def fmt_po(self, obj):
        return mark_safe(f'<div style="text-align: right; font-weight: bold;">{obj.po_amount:,.2f}</div>')

    fmt_po.short_description = 'PO Amount'  # Sets the column header name
    fmt_po.admin_order_field = 'po_amount'  # Keeps the column sortable

    fmt_po.short_description = "PO Amount"

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
    # RESTORED: status and inv_type to list_display
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

    # -----------------------------------------------------------------
    # NEW: Retention Recovery UI Methods
    # -----------------------------------------------------------------
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
        # Determine Title Header based on inv_type
        if inv.inv_type == "P":
            header_title = "PROFORMA INVOICE"
        else:
            header_title = "TAX INVOICE"

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

        # Build footer rows with retention recovery
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

        # Add retention recovery rows if applicable
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

        # Header image URL
        header_img_url = company.letter_header.url if company and company.letter_header else ''
        footer_img_url = company.letter_footer.url if company and company.letter_footer else ''

        html = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        /* ============================================
           CRITICAL: Page setup with margins
           ============================================ */
        @page {{
            size: A4 landscape;  /* or portrait - change as needed */
            margin: 18mm 10mm 18mm 10mm;

            /* Running headers/footers for WeasyPrint */
            @top-center {{
                content: element(page-header);
                vertical-align: top;
            }}
            @bottom-center {{
                content: element(page-footer);
                vertical-align: bottom;
            }}
        }}

        /* ============================================
           RUNNING HEADER & FOOTER
           These appear on EVERY page automatically
           ============================================ */
        #page-header {{
            position: running(page-header);
            width: 100%;
            text-align: center;
            margin-bottom: 8px;
        }}

        #page-header img {{
            max-height: 130px;
            width: 100%;
            object-fit: contain;
        }}

        #page-footer {{
            position: running(page-footer);
            width: 100%;
            text-align: center;
            margin-top: 8px;
        }}

        #page-footer img {{
            max-height: 100px;
            width: 100%;
            object-fit: contain;
        }}

        /* ============================================
           BASE STYLES
           ============================================ */
        * {{
            box-sizing: border-box;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: "Segoe UI", Arial, Helvetica, sans-serif;
            font-size: 8.5px;
            line-height: 1.3;
            color: #222;
            width: 100%;
        }}

        /* ============================================
           INVOICE HEADER (content header, not page header)
           ============================================ */
        .invoice-title {{
            font-size: 15px;
            font-weight: bold;
            text-align: center;
            margin: 8px 0 12px 0;
            color: #000080;
            letter-spacing: 1px;
        }}

        .invoice-meta {{
            margin-bottom: 10px;
        }}

        .invoice-meta-row {{
            font-size: 11px;
            font-weight: bold;
            margin-bottom: 4px;
        }}

        .parties-row {{
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            gap: 20px;
        }}

        .party-block {{
            flex: 1;
        }}

        .party-name {{
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 3px;
        }}

        .party-detail {{
            font-size: 10px;
            margin-bottom: 2px;
        }}

        .project-name {{
            font-size: 10px;
            margin: 8px 0 10px 0;
        }}

        .section-title {{
            text-align: center;
            font-size: 13px;
            font-weight: bold;
            margin: 8px 0 6px 0;
            color: #111;
        }}

        /* ============================================
           TABLE - FIXED RIGHT BORDER ISSUE
           ============================================ */
        .boq-table {{
            width: 100%;
            max-width: 100%;
            border-collapse: collapse;
            margin-top: 6px;
            font-size: 8px;
            table-layout: fixed;  /* CRITICAL: prevents overflow */
        }}

        .boq-table thead {{
            display: table-header-group;  /* Repeats on every page */
        }}

        .boq-table th {{
            background: #e8e8e8;
            border: 1px solid #666;
            padding: 4px 2px;
            font-weight: bold;
            text-align: center;
            font-size: 7.5px;
            word-wrap: break-word;
        }}

        .boq-table td {{
            border: 1px solid #666;
            padding: 3px 4px;
            vertical-align: top;
        }}

        /* Column widths - CRITICAL for preventing overflow */
        .col-item {{ width: 4%; text-align: center; }}
        .col-desc {{ width: 32%; text-align: left; }}
        .col-unit {{ width: 5%; text-align: center; }}
        .col-num {{ width: 6.5%; text-align: right; white-space: nowrap; }}
        .col-label {{ text-align: right; font-weight: bold; padding-right: 8px; }}

        /* Description cell - smaller font */
        .boq-table td.col-desc {{
            font-size: 6px;
            line-height: 1.2;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: auto;
        }}

        /* Total rows */
        .total-row td {{
            font-weight: bold;
            background: #f0f0f0;
            border-top: 2px solid #333;
        }}

        .grand-total-row td {{
            font-weight: bold;
            background: #f5f5f5;
            border-top: 2px solid #333;
            border-bottom: 2px solid #333;
        }}

        /* Prevent row splitting across pages */
        .boq-table tr {{
            page-break-inside: avoid;
        }}

        /* ============================================
           SUMMARY BOXES
           ============================================ */
        .summary-wrapper {{
            display: flex;
            justify-content: space-between;
            margin-top: 15px;
            gap: 15px;
            page-break-inside: avoid;
        }}

        .summary-box {{
            border: 1px solid #666;
            padding: 8px 12px;
        }}

        .summary-box.bank {{
            flex: 1;
            max-width: 45%;
        }}

        .summary-box.totals {{
            flex: 1;
            max-width: 45%;
            margin-left: auto;
        }}

        .summary-box-title {{
            font-weight: bold;
            margin-bottom: 5px;
            text-decoration: underline;
            font-size: 9px;
        }}

        .summary-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
            font-size: 9px;
        }}

        .summary-row.border-top {{
            border-top: 1px solid #333;
            margin-top: 5px;
            padding-top: 5px;
        }}

        .red-text {{
            color: #000080;
            font-weight: bold;
            font-size: 1.4em;
        }}

        .bank-content {{
            font-family: "Courier New", monospace;
            font-size: 10px;
            font-weight: bold;
            color: #000080;
            line-height: 1.4;
        }}

        /* ============================================
           PAGE BREAK CONTROL
           ============================================ */
        .page-break-avoid {{
            page-break-inside: avoid;
        }}

        /* ============================================
           FALLBACK FOR BROWSER PRINT
           If using browser print instead of WeasyPrint
           ============================================ */
        @media print {{
            #page-header {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
            }}

            #page-footer {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
            }}

            body {{
                padding-top: 140px;
                padding-bottom: 110px;
            }}
        }}

    </style>
    </head>
    <body>

        <!-- ============================================
             RUNNING PAGE HEADER - Appears on EVERY page
             ============================================ -->
        <div id="page-header">
            {"<img src='" + header_img_url + "' alt='Header'>" if header_img_url else ""}
        </div>

        <!-- ============================================
             MAIN CONTENT
             ============================================ -->
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

        <!-- ============================================
             RUNNING PAGE FOOTER - Appears on EVERY page
             ============================================ -->
        <div id="page-footer">
            {"<img src='" + footer_img_url + "' alt='Footer'>" if footer_img_url else ""}
        </div>

        <script>window.onload = function() {{ window.print(); }}</script>
    </body>
    </html>"""
        return HttpResponse(html)