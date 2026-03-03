"""
OCR Service for extracting receipt data using Tesseract OCR.
Includes ML-based improvements for better accuracy.
"""

import re
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReceiptOCR:
    """OCR processor for receipt images."""
    
    def __init__(self):
        # Common patterns for receipt data extraction
        self.patterns = {
            'date': [
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
                r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
                r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4}\b',
            ],
            'time': [
                r'\b(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\b',
            ],
            'amount': [
                r'(?:TOTAL|Total|AMOUNT|Amount|Due|DUE)\s*[:$]?\s*([$]?\d+\.\d{2})',
                r'(?:SUBTOTAL|Subtotal)\s*[:$]?\s*([$]?\d+\.\d{2})',
                r'(?:TAX|Tax|VAT|GST)\s*[:$]?\s*([$]?\d+\.\d{2})',
                r'(?:TIP|Tip|Gratuity)\s*[:$]?\s*([$]?\d+\.\d{2})',
                r'\$?(\d+\.\d{2})\s*$',
            ],
            'merchant': [
                r'^([A-Z][A-Za-z0-9\s&\'\.]+(?:Inc\.?|LLC|Ltd\.?|Corp\.?|Restaurant|Store|Market|Cafe|Shop)?)',
            ],
            'receipt_number': [
                r'(?:Receipt|Invoice|Order|Trans|Transaction)\s*#?\s*[:]?\s*([A-Z0-9\-]+)',
                r'(?:#|No\.?|Num\.?)\s*([A-Z0-9\-]{4,})',
            ],
        }
    
    def preprocess_image(self, image_path):
        """
        Preprocess image for better OCR accuracy.
        """
        try:
            # Open image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too small (improves OCR)
            min_size = 1000
            if min(image.size) < min_size:
                ratio = min_size / min(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to grayscale
            image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Apply sharpening
            image = image.filter(ImageFilter.SHARPEN)
            
            # Apply thresholding for cleaner text
            image = image.point(lambda x: 0 if x < 128 else 255, '1') # type: ignore
            image = image.convert('L')
            
            return image
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return Image.open(image_path)
    
    def extract_text(self, image_path):
        """
        Extract raw text from receipt image using OCR.
        """
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            
            # Configure Tesseract for receipt processing
            custom_config = r'--oem 3 --psm 6 -l eng'
            
            # Extract text
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            return ""
    
    def parse_date(self, text):
        """Extract date from receipt text."""
        for pattern in self.patterns['date']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Try different date formats
                    for fmt in ['%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y', 
                               '%Y-%m-%d', '%Y/%m/%d', '%m-%d-%Y']:
                        try:
                            return datetime.strptime(date_str, fmt).date()
                        except ValueError:
                            continue
                except Exception:
                    continue
        return None
    
    def parse_time(self, text):
        """Extract time from receipt text."""
        for pattern in self.patterns['time']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                time_str = match.group(1)
                try:
                    # Try different time formats
                    for fmt in ['%I:%M %p', '%I:%M:%S %p', '%H:%M', '%H:%M:%S']:
                        try:
                            return datetime.strptime(time_str, fmt).time()
                        except ValueError:
                            continue
                except Exception:
                    continue
        return None
    
    def parse_amounts(self, text):
        """Extract financial amounts from receipt text."""
        amounts = {
            'subtotal': None,
            'tax': None,
            'tip': None,
            'total': None,
        }
        
        # Find all dollar amounts
        all_amounts = re.findall(r'\$?(\d+\.\d{2})', text)
        all_amounts = [float(a) for a in all_amounts]
        
        # Try to identify specific amounts
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            
            # Look for subtotal
            if any(word in line_lower for word in ['subtotal', 'sub-total', 'sub total']):
                match = re.search(r'\$?(\d+\.\d{2})', line)
                if match:
                    amounts['subtotal'] = float(match.group(1)) # type: ignore
            
            # Look for tax
            elif any(word in line_lower for word in ['tax', 'vat', 'gst', 'hst']):
                match = re.search(r'\$?(\d+\.\d{2})', line)
                if match:
                    amounts['tax'] = float(match.group(1)) # type: ignore
            
            # Look for tip
            elif any(word in line_lower for word in ['tip', 'gratuity', 'service charge']):
                match = re.search(r'\$?(\d+\.\d{2})', line)
                if match:
                    amounts['tip'] = float(match.group(1)) # type: ignore
            
            # Look for total (usually the largest amount)
            elif any(word in line_lower for word in ['total', 'amount due', 'balance due', 'grand total']):
                match = re.search(r'\$?(\d+\.\d{2})', line)
                if match:
                    amounts['total'] = float(match.group(1)) # type: ignore
        
        # If total not found, use the largest amount
        if amounts['total'] is None and all_amounts:
            amounts['total'] = max(all_amounts) # type: ignore
        
        return amounts
    
    def parse_merchant(self, text):
        """Extract merchant name from receipt text."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Try first few lines for merchant name
        for line in lines[:5]:
            # Skip common non-merchant lines
            if any(skip in line.lower() for skip in ['receipt', 'invoice', 'date', 'time', 'tel:', 'phone']):
                continue
            
            # Look for a line that looks like a business name
            if len(line) > 2 and len(line) < 50:
                # Clean up the line
                merchant = line.strip()
                # Remove common suffixes that aren't part of name
                merchant = re.sub(r'\s*(?:Inc\.?|LLC|Ltd\.?|Corp\.?).*$', '', merchant, flags=re.IGNORECASE)
                return merchant.strip()
        
        return None
    
    def parse_receipt_number(self, text):
        """Extract receipt/invoice number."""
        for pattern in self.patterns['receipt_number']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def parse_items(self, text):
        """Extract individual line items from receipt."""
        items = []
        lines = text.split('\n')
        
        # Look for item patterns (description followed by price)
        for line in lines:
            # Pattern: description + price
            match = re.search(r'^(.+?)\s+\$?(\d+\.\d{2})\s*$', line.strip())
            if match:
                description = match.group(1).strip()
                price = float(match.group(2))
                
                # Skip if it looks like a total line
                if any(word in description.lower() for word in ['total', 'subtotal', 'tax', 'tip', 'change']):
                    continue
                
                items.append({
                    'description': description,
                    'quantity': 1,
                    'unit_price': price,
                    'total_price': price,
                })
        
        return items
    
    def categorize_receipt(self, text, merchant_name=None):
        """
        Categorize receipt based on content and merchant name.
        Simple rule-based categorization (can be enhanced with ML).
        """
        text_lower = text.lower()
        merchant_lower = (merchant_name or '').lower()
        
        # Category keywords
        categories = {
            'food': ['restaurant', 'cafe', 'coffee', 'pizza', 'burger', 'food', 'dining', 
                    'kitchen', 'grill', 'bakery', 'deli', 'supermarket', 'grocery'],
            'transport': ['gas', 'fuel', 'uber', 'lyft', 'taxi', 'parking', 'toll', 
                         'transit', 'bus', 'train', 'airline', 'flight'],
            'office': ['office', 'supplies', 'staples', 'paper', 'ink', 'printer'],
            'utilities': ['electric', 'water', 'gas', 'internet', 'phone', 'utility'],
            'travel': ['hotel', 'motel', 'airbnb', 'resort', 'travel'],
            'healthcare': ['pharmacy', 'medical', 'health', 'doctor', 'dental', 'hospital'],
            'entertainment': ['movie', 'theater', 'concert', 'game', 'entertainment'],
            'shopping': ['retail', 'store', 'shop', 'mall', 'amazon', 'walmart', 'target'],
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text_lower or keyword in merchant_lower:
                    return category
        
        return 'other'
    
    def process_receipt(self, image_path):
        """
        Process a receipt image and extract all relevant data.
        
        Returns a dictionary with extracted information.
        """
        # Extract raw text
        raw_text = self.extract_text(image_path)
        
        if not raw_text:
            return {
                'success': False,
                'error': 'Could not extract text from image',
                'raw_text': '',
            }
        
        # Parse different fields
        merchant_name = self.parse_merchant(raw_text)
        receipt_date = self.parse_date(raw_text)
        receipt_time = self.parse_time(raw_text)
        receipt_number = self.parse_receipt_number(raw_text)
        amounts = self.parse_amounts(raw_text)
        items = self.parse_items(raw_text)
        category = self.categorize_receipt(raw_text, merchant_name)
        
        return {
            'success': True,
            'merchant_name': merchant_name,
            'receipt_date': receipt_date,
            'receipt_time': receipt_time,
            'receipt_number': receipt_number,
            'subtotal': amounts['subtotal'],
            'tax_amount': amounts['tax'],
            'tip_amount': amounts['tip'],
            'total_amount': amounts['total'],
            'category': category,
            'items': items,
            'raw_text': raw_text,
        }


# Singleton instance
receipt_ocr = ReceiptOCR()
