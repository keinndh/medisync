import tabula
import pandas as pd
from models import db, MedicineCategory
from app import app
import sys
import os

def extract_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} not found.")
        return

    print(f"Extracting tables from {pdf_path} using Lattice mode...")
    try:
        # lattice=True is key for keeping multi-line text inside a single 'cell' or bounding box
        dfs = tabula.read_pdf(pdf_path, pages='all', lattice=True)
        
        categories = set()
        column_found = False

        for i, df in enumerate(dfs):
            # Clean dataframe column names to find the 'Active Ingredient' header
            df.columns = [str(c).replace('\r', ' ').replace('\n', ' ').strip() for c in df.columns]
            
            target_col = None
            for col in df.columns:
                if 'active ingredient' in col.lower() or 'generic name' in col.lower():
                    target_col = col
                    column_found = True
                    break
            
            if target_col:
                print(f"Page {i+1}: Processing column '{target_col}'")
                for val in df[target_col].dropna():
                    # Replace internal newlines with a space to merge multi-line names
                    val_str = str(val).replace('\r', ' ').replace('\n', ' ').strip()
                    
                    # Remove double spaces caused by the merge (e.g. "Word  Word" -> "Word Word")
                    clean_val = " ".join(val_str.split())
                    
                    # Heuristic: Ignore fragments like "Acid" or "Specific" and pure numbers
                    if len(clean_val) > 4 and not clean_val.isdigit():
                        if 'active ingredient' not in clean_val.lower():
                            categories.add(clean_val)
        
        if not column_found:
            print("Warning: Could not find 'Active Ingredient' column header.")
            return

        print(f"Total unique medicines identified: {len(categories)}")
        
        with app.app_context():
            # Recommendation: Clear the table first to avoid duplicates or UNIQUE constraint errors
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