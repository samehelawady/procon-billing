from django.shortcuts import render, get_object_or_404
from .models import Invoice

def invoice_report(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    items = invoice.items.all()
    return render(request, "sales/invoice_report.html", {
        "invoice": invoice,
        "items": items,
    })