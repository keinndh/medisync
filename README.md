# MediSync
### **Vitali District Medicine Inventory & Management System**

**MediSync** is a streamlined, web-based inventory management solution designed specifically for the **Vitali District Health Center**. It automates the tracking, categorization, and monitoring of medical supplies to ensure that essential medicines are always available for the community.

---

## Overview
Managing medicine in a barangay health center requires precision. **MediSync** replaces manual logging with a digital interface, allowing healthcare workers to manage stock levels, track expiration dates, and organize medicines by category with ease.

---

## Key Features
* **Medicine Inventory:** Real-time tracking of stock levels (In/Out).
* **Categorization:** Automated and manual sorting of medicines (e.g., *Antibiotics, Vitamins, Maintenance*).
* **PDF Integration:** Tools to extract and migrate medicine lists from official PDF documents directly into the database.
* **User-Friendly Dashboard:** A clean, responsive interface for healthcare staff to view current stock status.
* **Data Integrity:** Built-in migration scripts to ensure the database schema stays up-to-date.

---

## Tech Stack
| Component | Technology |
| :--- | :--- |
| **Backend** | Python (Flask) |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Database** | SQLite (SQLAlchemy ORM) |
| **Tools** | PDF Extraction scripts, Flask-Migrate |

---

## Project Structure
```plaintext
├── app.py                # Main application entry point
├── models.py             # Database schema and models
├── migrate_db.py         # Script for handling database migrations
├── extract_categories.py  # Utility for processing medicine lists
├── templates/            # HTML layouts and pages
├── static/               # CSS and JavaScript assets
└── dataset/              # Initial data and resource files
```

---

## Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/keinndh/medisync.git
   cd medisync
   ```

2. **Create a Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the Database:**
   ```bash
   python migrate_db.py
   ```

5. **Run the Application:**
   ```bash
   flask run
   ```
   > The app will be available at **[http://127.0.0.1:5000](http://127.0.0.1:5000)**.

---

## Future Roadmap
* **Low Stock Alerts:** Automated notifications when medicine levels fall below a certain threshold.
* **Expiration Tracking:** Visual warnings for medicines nearing their expiry date.
* **Reporting:** Generate monthly consumption reports for district-level submission.

---

## Contributing
This project is currently being developed for a specific health center. However, feedback and suggestions are welcome. Feel free to **open an issue** or **submit a pull request**.

---

## License
This project is licensed under the **MIT License** - see the `LICENSE` file for details.

---
