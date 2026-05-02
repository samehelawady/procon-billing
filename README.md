# Procon Billing System

Django-based billing and project management portal for Procon General Contracting LLC.

## Features
- Client & Project Management
- Bill of Quantities (BOQ)
- Progress Invoicing with Retention & Advance Recovery
- Tax/Proforma Invoice Generation
- Analytics Reports (Statement, Outstanding, Progress, Project Analytics)

## Setup

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/procon-billing.git
cd procon-billing

# Virtual Environment
python -m venv venv
source venv/bin/activate

# Install
pip install -r requirements.txt

# Database
python manage.py migrate

# Create Superuser
python manage.py createsuperuser

# Run
python manage.py runserver