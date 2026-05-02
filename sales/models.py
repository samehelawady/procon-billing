import decimal
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.db.models import Sum, Max, Q
from django.core.exceptions import ValidationError
from django.contrib import admin
from django.forms import TextInput
from django.utils.html import format_html
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.urls import path, reverse

# =============================================================================
# UTILITIES
# =============================================================================

def money(value):
    """Standardizes decimal rounding to 2 decimal places."""
    if value is None:
        return Decimal("0.00")
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# =============================================================================
# SECTION 1: MODELS
# =============================================================================

class Client(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    vat_number = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

# =============================================================================
# Company Profile
# =============================================================================
class CompanyProfile(models.Model):
    class Meta:
        verbose_name = "Company Profile"
        verbose_name_plural = "Company Profile"

    company_name = models.CharField(max_length=255)

    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)

    letter_header = models.ImageField(
        upload_to="company_headers/",
        blank=True,
        null=True,
        help_text="Invoice header image"
    )

    letter_footer = models.ImageField(
        upload_to="company_footers/",
        blank=True,
        null=True,
        help_text="Invoice footer image"
    )

    trn_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    address = models.TextField(blank=True, null=True)

    bank = models.TextField(blank=True, null=True)

    phone = models.CharField(max_length=100, blank=True, null=True)

    email = models.EmailField(blank=True, null=True)

    website = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.company_name

    # =============================================================================

class Project(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="projects")
    project_id_code = models.CharField(max_length=50, unique=True)
    project_name = models.CharField(max_length=255)
    po_number = models.CharField(max_length=255, blank=True, null=True)
    po_date = models.DateField(blank=True, null=True)
    po_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    advance_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    retention_a_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    retention_b_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_boq_complete = models.BooleanField(
        default=False,
        editable=False,
        help_text="Automatically set to True when BOQ total matches PO Amount."
    )

    @property
    def total_advance_value(self):
        return money(self.po_amount * (self.advance_percent / 100))

    @property
    def boq_total_value(self):
        total = sum(money(item.quantity * item.rate) for item in self.boq_items.all())
        return money(total)

    def save(self, *args, **kwargs):
        if self.pk:
            self.is_boq_complete = (self.boq_total_value == money(self.po_amount))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project_id_code} - {self.project_name}"


class BOQItem(models.Model):
    class Meta:
        verbose_name = "BOQ Item"
        verbose_name_plural = "BOQ Items"

    UNIT_CHOICES = [
        ("M", "M"), ("M2", "M2"), ("M3", "M3"), ("LS", "LS"),
        ("Nos", "Nos"), ("EA", "EA"), ("LM", "LM"),
        ("P.Sum", "P.Sum"), ("Item", "Item"), ("Unit", "Unit"),('Pcs', 'Pcs')
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="boq_items")
    item_number = models.CharField(max_length=10)
    description = models.TextField()
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="LS")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rate = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.project.save()

    def delete(self, *args, **kwargs):
        p = self.project
        super().delete(*args, **kwargs)
        p.save()

    def __str__(self):
        return f"{self.item_number} - {self.description[:30]}"


class Invoice(models.Model):
    INVOICE_TYPES = [("P", "Proforma"), ("T", "Tax")]
    STATUS_CHOICES = [("Draft", "Draft"), ("Approved", "Approved"), ("Paid", "Paid")]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="invoices")
    inv_type = models.CharField(max_length=1, choices=INVOICE_TYPES, default="P")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Draft")
    inv_number = models.IntegerField(null=True, blank=True)
    revision = models.IntegerField(default=0)
    date = models.DateField()
    is_advance_invoice = models.BooleanField(default=False)

    # ═══════════════════════════════════════════════════════════════
    # NEW: Retention Recovery
    # ═══════════════════════════════════════════════════════════════
    RETENTION_RECOVERY_CHOICES = [
        ('', 'None'),
        ('A', 'Retention A'),
        ('B', 'Retention B'),
    ]
    retention_recovery = models.CharField(
        max_length=1,
        choices=RETENTION_RECOVERY_CHOICES,
        blank=True,
        default='',
        help_text="Recover previously deducted retention on this invoice. "
                  "A and B must be recovered in separate invoices."
    )

    vat_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    material_supplied_by_client = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        unique_together = ('project', 'inv_number')

    def __str__(self):
        num = str(self.inv_number or 0).zfill(2)
        return f"PGC-S{self.project.project_id_code}-{self.inv_type}-INV-{num}R{str(self.revision).zfill(2)}"

    def clean(self):
        if self.project and not self.project.is_boq_complete:
            raise ValidationError(
                f"Invoicing disabled. BOQ ({self.project.boq_total_value:,.2f}) != PO ({self.project.po_amount:,.2f})")

    # --- Calculation Helpers ---

    @property
    def was_advance_taken(self):
        return Invoice.objects.filter(project=self.project, is_advance_invoice=True,
                                      inv_number__lte=self.inv_number).exists()

    @property
    def cumulative_work_done(self):
        if self.is_advance_invoice: return Decimal("0.00")
        total = InvoiceItem.objects.filter(
            invoice__project=self.project,
            invoice__inv_number__lte=self.inv_number,
            invoice__is_advance_invoice=False
        ).aggregate(total=Sum('gross_amount'))['total']
        return money(total)

    @property
    def previous_work_done(self):
        prev = Invoice.objects.filter(project=self.project, inv_number__lt=self.inv_number,
                                      is_advance_invoice=False).order_by('-inv_number').first()
        return prev.cumulative_work_done if prev else Decimal("0.00")

    @property
    def current_gross_total(self):
        if self.is_advance_invoice: return Decimal("0.00")
        return self.items.aggregate(total=Sum('gross_amount'))['total'] or Decimal("0.00")

    # Recovery A / Advance
    @property
    def cumulative_advance_recovered(self):
        if self.is_advance_invoice or not self.was_advance_taken: return Decimal("0.00")
        recovery = money(self.cumulative_work_done * (self.project.advance_percent / 100))
        return min(recovery, self.project.total_advance_value)

    @property
    def previous_advance_recovered(self):
        prev = Invoice.objects.filter(project=self.project, inv_number__lt=self.inv_number,
                                      is_advance_invoice=False).order_by('-inv_number').first()
        return prev.cumulative_advance_recovered if prev else Decimal("0.00")

    @property
    def current_advance_recovery(self):
        return money(self.cumulative_advance_recovered - self.previous_advance_recovered)

    # Retention A
    @property
    def cumulative_retention_a(self):
        if self.is_advance_invoice: return Decimal("0.00")
        return money(self.cumulative_work_done * (self.project.retention_a_percent / 100))

    @property
    def previous_retention_a(self):
        prev = Invoice.objects.filter(project=self.project, inv_number__lt=self.inv_number,
                                      is_advance_invoice=False).order_by('-inv_number').first()
        return prev.cumulative_retention_a if prev else Decimal("0.00")

    @property
    def current_retention_a(self):
        return money(self.cumulative_retention_a - self.previous_retention_a)

    # Retention B
    @property
    def cumulative_retention_b(self):
        if self.is_advance_invoice: return Decimal("0.00")
        return money(self.cumulative_work_done * (self.project.retention_b_percent / 100))

    @property
    def previous_retention_b(self):
        prev = Invoice.objects.filter(project=self.project, inv_number__lt=self.inv_number,
                                      is_advance_invoice=False).order_by('-inv_number').first()
        return prev.cumulative_retention_b if prev else Decimal("0.00")

    @property
    def current_retention_b(self):
        return money(self.cumulative_retention_b - self.previous_retention_b)

    @property
    def cumulative_retention_total(self):
        return money(self.cumulative_retention_a + self.cumulative_retention_b)

    # -----------------------------------------------------------------
    # NEW: Retention Recovery Properties
    # -----------------------------------------------------------------

    @property
    def was_retention_a_recovered(self):
        return Invoice.objects.filter(
            project=self.project, retention_recovery='A',
            inv_number__lt=self.inv_number
        ).exists()

    @property
    def was_retention_b_recovered(self):
        return Invoice.objects.filter(
            project=self.project, retention_recovery='B',
            inv_number__lt=self.inv_number
        ).exists()

    @property
    def previous_retention_a_recovered(self):
        prev = Invoice.objects.filter(
            project=self.project, inv_number__lt=self.inv_number,
            is_advance_invoice=False
        ).order_by('-inv_number').first()
        return prev.cumulative_retention_a_recovered if prev else Decimal("0.00")

    @property
    def previous_retention_b_recovered(self):
        prev = Invoice.objects.filter(
            project=self.project, inv_number__lt=self.inv_number,
            is_advance_invoice=False
        ).order_by('-inv_number').first()
        return prev.cumulative_retention_b_recovered if prev else Decimal("0.00")

    @property
    def current_retention_a_recovery(self):
        if self.retention_recovery == 'A' and not self.was_retention_a_recovered:
            return self.previous_retention_a
        return Decimal("0.00")

    @property
    def current_retention_b_recovery(self):
        if self.retention_recovery == 'B' and not self.was_retention_b_recovered:
            return self.previous_retention_b
        return Decimal("0.00")

    @property
    def cumulative_retention_a_recovered(self):
        total = Decimal("0.00")
        if self.retention_recovery == 'A' and not self.was_retention_a_recovered:
            total += self.previous_retention_a
        prev = Invoice.objects.filter(
            project=self.project, retention_recovery='A',
            inv_number__lt=self.inv_number
        ).order_by('-inv_number').first()
        if prev:
            total += prev.previous_retention_a
        return money(total)

    @property
    def cumulative_retention_b_recovered(self):
        total = Decimal("0.00")
        if self.retention_recovery == 'B' and not self.was_retention_b_recovered:
            total += self.previous_retention_b
        prev = Invoice.objects.filter(
            project=self.project, retention_recovery='B',
            inv_number__lt=self.inv_number
        ).order_by('-inv_number').first()
        if prev:
            total += prev.previous_retention_b
        return money(total)

    # Totals
    @property
    def net_total_invoiced_cumulative(self):
        if self.is_advance_invoice: return Decimal("0.00")
        base = money(
            self.cumulative_work_done
            - self.cumulative_advance_recovered
            - self.cumulative_retention_total
        )
        return money(
            base
            + self.cumulative_retention_a_recovered
            + self.cumulative_retention_b_recovered
        )

    @property
    def previous_net_total_invoiced(self):
        prev = Invoice.objects.filter(project=self.project, inv_number__lt=self.inv_number,
                                      is_advance_invoice=False).order_by('-inv_number').first()
        return prev.net_total_invoiced_cumulative if prev else Decimal("0.00")

    @property
    def current_net_before_vat(self):
        if self.is_advance_invoice:
            prev_adv = Invoice.objects.filter(project=self.project, is_advance_invoice=True,
                                              inv_number__lt=self.inv_number).exists()
            return Decimal("0.00") if prev_adv else self.project.total_advance_value
        return money(self.net_total_invoiced_cumulative - self.previous_net_total_invoiced)

    @property
    def vat_amount(self):
        return money(self.current_net_before_vat * (self.vat_percent / 100))

    @property
    def total_with_vat(self):
        return money(self.current_net_before_vat + self.vat_amount)

    @property
    def total_after_vat(self):
        return money(self.total_with_vat - self.material_supplied_by_client)

    def save(self, *args, **kwargs):
        if self.inv_number is None:
            last = Invoice.objects.filter(project=self.project).aggregate(Max("inv_number"))["inv_number__max"]
            self.inv_number = (last + 1) if last else 1
        super().save(*args, **kwargs)
        if not self.is_advance_invoice:
            for boq in self.project.boq_items.all():
                item, created = InvoiceItem.objects.get_or_create(invoice=self, boq_item=boq,
                                                                  defaults={'rate': boq.rate})
                item.save()


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    boq_item = models.ForeignKey(BOQItem, on_delete=models.PROTECT)
    billing_method = models.CharField(max_length=3, choices=[("QTY", "Qty"), ("PCT", "%")], default="PCT")
    current_qty = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_percentage = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    rate = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Historical Snapshots
    prev_qty = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False)
    prev_percentage = models.DecimalField(max_digits=8, decimal_places=2, default=0, editable=False)
    prev_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False)
    gross_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False)

    # Recovery Breakdown
    advance_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False)
    retention_a_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False)
    retention_b_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False)
    net_amount_value = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False)

    class Meta:
        unique_together = ('invoice', 'boq_item')

    @property
    def cum_qty(self):
        return money(self.prev_qty + self.current_qty)

    @property
    def cum_amt(self):
        return money(self.prev_amount + self.gross_amount)

    def save(self, *args, **kwargs):
        if not self.rate: self.rate = self.boq_item.rate
        prior = InvoiceItem.objects.filter(boq_item=self.boq_item, invoice__project=self.invoice.project,
                                           invoice__inv_number__lt=self.invoice.inv_number,
                                           invoice__is_advance_invoice=False)
        self.prev_qty = prior.aggregate(total=Sum('current_qty'))['total'] or Decimal("0.00")
        self.prev_amount = prior.aggregate(total=Sum('gross_amount'))['total'] or Decimal("0.00")

        if self.boq_item.quantity > 0:
            self.prev_percentage = money((self.prev_qty / self.boq_item.quantity) * 100)

        if self.billing_method == "PCT":
            self.current_percentage = Decimal(self.current_percentage or 0)
            self.current_qty = money(self.boq_item.quantity * (self.current_percentage / 100))
        else:
            if self.boq_item.quantity > 0:
                self.current_percentage = money((self.current_qty / self.boq_item.quantity) * 100)

        self.gross_amount = money(self.current_qty * self.rate)
        self.retention_a_amount = money(self.gross_amount * (self.invoice.project.retention_a_percent / 100))
        self.retention_b_amount = money(self.gross_amount * (self.invoice.project.retention_b_percent / 100))

        if self.invoice.was_advance_taken:
            self.advance_amount = money(self.gross_amount * (self.invoice.project.advance_percent / 100))
        else:
            self.advance_amount = Decimal("0.00")

        self.net_amount_value = money(
            self.gross_amount - self.retention_a_amount - self.retention_b_amount - self.advance_amount)
        super().save(*args, **kwargs)