import PyPDF2
from models import db, MedicineCategory
from app import app
import sys
import os

def extract_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} not found.")
        return

    print(f"Extracting text from {pdf_path}...")
    try:
        categories = set()
        
        # Open the PDF file in read-binary mode
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Iterate through all the pages
            for i, page in enumerate(reader.pages):
                print(f"Processing Page {i+1}...")
                text = page.extract_text()
                
                if text:
                    # Split the extracted text line by line
                    lines = text.split('\n')
                    
                    for line in lines:
                        clean_val = line.strip()
                        
                        # Basic heuristic: Ignore empty lines or pure numbers
                        if len(clean_val) > 2 and not clean_val.isdigit():
                            categories.add(clean_val)
                            
        print(f"Total unique medicines identified: {len(categories)}")
        
        with app.app_context():
            # Recommendation: Clear the table first if you want a fresh import
            # db.session.query(MedicineCategory).delete() 
            
            db.create_all()
            count = 0
            for cat_name in categories:
                existing = MedicineCategory.query.filter_by(name=cat_name).first()
                if not existing:
                    new_cat = MedicineCategory(name=cat_name)
                    db.session.add(new_cat)
                    count += 1
            
            db.session.commit()
            print(f"Successfully saved {count} clean categories to the database.")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_categories.py <path_to_pdf>")
    else:
        extract_from_pdf(sys.argv[1])