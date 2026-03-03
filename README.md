# Smart Invoice & Receipt Processor

A Django-based web application for automatically processing receipts and invoices using OCR (Optical Character Recognition) and ML techniques. Track expenses, generate tax summaries, and manage your finances with ease.

## Features

### Core Functionality
- **Receipt Upload**: Upload receipt images (JPG, PNG) via drag-and-drop or file selection
- **AI-Powered OCR**: Automatic extraction of:
  - Merchant name
  - Receipt date and time
  - Total, subtotal, tax, and tip amounts
  - Receipt/invoice number
  - Individual line items
  - Expense category (auto-categorized)

### Expense Tracking
- **Dashboard**: Overview of monthly spending, receipt count, and tax-deductible expenses
- **Category Breakdown**: Visual charts showing spending by category
- **Receipt Management**: View, edit, and organize all receipts
- **Filtering**: Filter by date range, category, and search terms

### Tax Summaries
- **Tax-Deductible Tracking**: Mark receipts as tax-deductible
- **Annual Reports**: Generate comprehensive tax reports by year
- **Category Breakdown**: See deductions organized by expense type
- **Monthly Trends**: Track deductible expenses throughout the year
- **Print-Friendly Reports**: Export or print tax summaries

### Visual Analytics
- Interactive charts using Chart.js
- Monthly spending trends
- Category distribution (pie/doughnut charts)
- Top merchants by spending

## Tech Stack

- **Backend**: Django 6.0+
- **OCR**: Tesseract OCR via pytesseract
- **Image Processing**: Pillow (PIL)
- **Data Analysis**: pandas, numpy
- **Visualization**: matplotlib, seaborn, Chart.js
- **Frontend**: Bootstrap 5, Font Awesome
- **Database**: SQLite (default, configurable)

## Installation

### Prerequisites
- Python 3.10+
- Tesseract OCR (system dependency)

### Install Tesseract

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

### Setup

1. Clone the repository:
```bash
cd receipt_processor
```

2. Install Python dependencies:
```bash
pip install django pytesseract pillow pandas matplotlib seaborn numpy
```

3. Run migrations:
```bash
python manage.py migrate
```

4. Create a superuser:
```bash
python manage.py createsuperuser
```

5. Collect static files:
```bash
python manage.py collectstatic
```

6. Run the development server:
```bash
python manage.py runserver
```

7. Access the application:
- Web app: http://127.0.0.1:8000/
- Admin panel: http://127.0.0.1:8000/admin/

## Usage

### Getting Started
1. Register a new account or login
2. Navigate to the Dashboard for an overview
3. Click "Upload Receipt" to process your first receipt
4. Review and edit the extracted data
5. Mark tax-deductible expenses
6. View expense summaries and tax reports

### Receipt Categories
- Food & Dining
- Transportation
- Office Supplies
- Utilities
- Travel
- Healthcare
- Entertainment
- Shopping
- Other

### API Endpoints
- `GET /api/receipts/` - List all receipts (JSON)
- `GET /api/stats/` - Get dashboard statistics
- `GET /api/chart/?type=category&year=2024` - Generate spending charts

## Project Structure

```
receipt_processor/
├── receipt_processor/      # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── receipts/               # Main application
│   ├── models.py          # Receipt, ReceiptItem, ExpenseBudget models
│   ├── views.py           # All views and API endpoints
│   ├── urls.py            # URL routing
│   ├── ocr_service.py     # OCR processing logic
│   ├── admin.py           # Admin configuration
│   └── templates/         # HTML templates
│       └── receipts/
├── media/                 # Uploaded receipt images
├── staticfiles/           # Collected static files
├── db.sqlite3            # Database
└── manage.py             # Django management script
```

## OCR Processing

The OCR service (`ocr_service.py`) uses Tesseract with the following preprocessing:
1. Image resizing for better accuracy
2. Grayscale conversion
3. Contrast enhancement
4. Sharpening
5. Thresholding for cleaner text

Extracted data includes:
- Merchant information
- Dates and times
- Financial amounts (using regex patterns)
- Line items
- Automatic categorization

## Configuration

### Environment Variables
```python
# Optional: Configure Tesseract path (Windows)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### Settings
Key settings in `receipt_processor/settings.py`:
- `MEDIA_ROOT`: Where uploaded receipts are stored
- `STATIC_ROOT`: Where static files are collected
- Database configuration (default: SQLite)

## Future Enhancements

- [ ] ML-based categorization improvement
- [ ] Multi-currency support
- [ ] Receipt sharing
- [ ] Mobile app
- [ ] Cloud storage integration
- [ ] Automated tax form generation
- [ ] Expense approval workflows
- [ ] Budget alerts and notifications

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
=======

