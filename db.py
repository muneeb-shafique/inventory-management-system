import sys, os, uuid, sqlite3, datetime
import barcode
from barcode.writer import ImageWriter
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableView, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QComboBox, QDialogButtonBox, QTableWidget, QTableWidgetItem, QLabel, QHeaderView
)
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant
from PyQt5.QtGui import QPixmap, QFont
import qdarkstyle
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm

# -------------------- SQLite Database Initialization --------------------
DB_FILE = "inventory_billing.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS Categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT UNIQUE NOT NULL
    );
    CREATE TABLE IF NOT EXISTS Suppliers (
        supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_name TEXT,
        contact_email TEXT,
        phone_number TEXT
    );
    CREATE TABLE IF NOT EXISTS Products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category_id INTEGER,
        supplier_id INTEGER,
        price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL,
        barcode TEXT UNIQUE,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (category_id) REFERENCES Categories(category_id) ON DELETE SET NULL,
        FOREIGN KEY (supplier_id) REFERENCES Suppliers(supplier_id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS Customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone_number TEXT,
        address TEXT
    );
    CREATE TABLE IF NOT EXISTS Users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        role TEXT CHECK(role IN ('admin', 'cashier')) NOT NULL
    );
    CREATE TABLE IF NOT EXISTS Invoices (
        invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        user_id INTEGER,
        total_amount REAL NOT NULL,
        payment_status TEXT CHECK(payment_status IN ('paid','pending')) NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (customer_id) REFERENCES Customers(customer_id) ON DELETE SET NULL,
        FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS Invoice_Items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        product_id INTEGER,
        quantity INTEGER NOT NULL,
        price_per_item REAL NOT NULL,
        FOREIGN KEY (invoice_id) REFERENCES Invoices(invoice_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES Products(product_id) ON DELETE SET NULL
    );
    """)
    conn.commit()
    conn.close()

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

init_db()

# -------------------- Barcode Image Generation --------------------
def generate_barcode_image(data):
    if not os.path.exists("barcodes"):
        os.makedirs("barcodes")
    filename = f"barcodes/{data}"
    Code128 = barcode.get_barcode_class('code128')
    my_code = Code128(data, writer=ImageWriter())
    full_filename = my_code.save(filename)
    return full_filename

# -------------------- PDF Generation --------------------
def export_invoice_to_pdf(invoice_id, invoiceData, invoiceItems):
    pdf_file = f"invoice_{invoice_id}.pdf"
    c = canvas.Canvas(pdf_file, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 50, "Inventory Billing Program")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 100, f"Invoice ID: {invoice_id}")
    c.drawString(50, height - 120, f"Customer ID: {invoiceData.get('customer_id')}")
    c.drawString(50, height - 140, f"User ID: {invoiceData.get('user_id')}")
    c.drawString(50, height - 160, f"Payment Status: {invoiceData.get('payment_status')}")
    c.drawString(50, height - 180, f"Created At: {invoiceData.get('created_at')}")
    c.drawString(50, height - 210, "Invoice Items:")
    y = height - 240
    c.setFont("Helvetica", 12)
    c.drawString(50, y, "Product ID")
    c.drawString(150, y, "Product Name")
    c.drawString(350, y, "Quantity")
    c.drawString(450, y, "Price")
    c.drawString(550, y, "Total")
    y -= 20
    for item in invoiceItems:
        total = item["quantity"] * item["price_per_item"]
        c.drawString(50, y, str(item["product_id"]))
        c.drawString(150, y, item["product_name"])
        c.drawString(350, y, str(item["quantity"]))
        c.drawString(450, y, f'{item["price_per_item"]:.2f}')
        c.drawString(550, y, f'{total:.2f}')
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 50
    c.showPage()
    c.save()
    return pdf_file

# -------------------- Custom Table Model --------------------
class TableModel(QAbstractTableModel):
    def __init__(self, data, headers, parent=None):
        super(TableModel, self).__init__(parent)
        self._data = data
        self._headers = headers

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        row = self._data[index.row()]
        header = self._headers[index.column()]
        value = row[header] if header in row.keys() else ""
        if role == Qt.DisplayRole:
            if header.lower() == "barcode":
                return ""
            return str(value)
        if role == Qt.DecorationRole:
            if header.lower() == "barcode" and value:
                pixmap = QPixmap(value)
                if not pixmap.isNull():
                    return pixmap.scaled(200, 50, Qt.KeepAspectRatioByExpanding)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._headers[section]
            else:
                return section + 1
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return QVariant()

    def getRow(self, row):
        if 0 <= row < len(self._data):
            return dict(self._data[row])
        return None

# -------------------- Add Category Dialog --------------------
class AddCategoryDialog(QDialog):
    def __init__(self, parent=None):
        super(AddCategoryDialog, self).__init__(parent)
        self.setWindowTitle("Add Category")
        self.initUI()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.nameEdit = QLineEdit(self); self.nameEdit.setFont(QFont("Arial", 14))
        self.formLayout.addRow("Category Name:", self.nameEdit)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.addCategory)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def addCategory(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO Categories (category_name) VALUES (?)", (self.nameEdit.text(),))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Category added!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Add category failed:\n{e}")
            self.reject()

# -------------------- Edit Category Dialog --------------------
class EditCategoryDialog(QDialog):
    def __init__(self, parent=None, categoryData=None):
        super(EditCategoryDialog, self).__init__(parent)
        self.setWindowTitle("Edit Category")
        self.categoryData = categoryData
        self.initUI()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.nameEdit = QLineEdit(self); self.nameEdit.setFont(QFont("Arial", 14))
        self.nameEdit.setText(self.categoryData.get("category_name", ""))
        self.formLayout.addRow("Category Name:", self.nameEdit)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.updateCategory)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def updateCategory(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE Categories SET category_name = ? WHERE category_id = ?", (self.nameEdit.text(), self.categoryData.get("category_id")))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Category updated!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Update failed:\n{e}")
            self.reject()

# -------------------- Add Customer Dialog --------------------
class AddCustomerDialog(QDialog):
    def __init__(self, parent=None):
        super(AddCustomerDialog, self).__init__(parent)
        self.setWindowTitle("Add Customer")
        self.initUI()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.nameEdit = QLineEdit(self); self.nameEdit.setFont(QFont("Arial", 14))
        self.emailEdit = QLineEdit(self); self.emailEdit.setFont(QFont("Arial", 14))
        self.phoneEdit = QLineEdit(self); self.phoneEdit.setFont(QFont("Arial", 14))
        self.addressEdit = QLineEdit(self); self.addressEdit.setFont(QFont("Arial", 14))
        self.formLayout.addRow("Name:", self.nameEdit)
        self.formLayout.addRow("Email:", self.emailEdit)
        self.formLayout.addRow("Phone Number:", self.phoneEdit)
        self.formLayout.addRow("Address:", self.addressEdit)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.addCustomer)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def addCustomer(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO Customers (name, email, phone_number, address) VALUES (?, ?, ?, ?)",
                        (self.nameEdit.text(), self.emailEdit.text(), self.phoneEdit.text(), self.addressEdit.text()))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Customer added!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Add customer failed:\n{e}")
            self.reject()

# -------------------- Edit Customer Dialog --------------------
class EditCustomerDialog(QDialog):
    def __init__(self, parent=None, customerData=None):
        super(EditCustomerDialog, self).__init__(parent)
        self.setWindowTitle("Edit Customer")
        self.customerData = customerData
        self.initUI()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.nameEdit = QLineEdit(self); self.nameEdit.setFont(QFont("Arial", 14))
        self.emailEdit = QLineEdit(self); self.emailEdit.setFont(QFont("Arial", 14))
        self.phoneEdit = QLineEdit(self); self.phoneEdit.setFont(QFont("Arial", 14))
        self.addressEdit = QLineEdit(self); self.addressEdit.setFont(QFont("Arial", 14))
        self.nameEdit.setText(self.customerData.get("name", ""))
        self.emailEdit.setText(self.customerData.get("email", ""))
        self.phoneEdit.setText(self.customerData.get("phone_number", ""))
        self.addressEdit.setText(self.customerData.get("address", ""))
        self.formLayout.addRow("Name:", self.nameEdit)
        self.formLayout.addRow("Email:", self.emailEdit)
        self.formLayout.addRow("Phone Number:", self.phoneEdit)
        self.formLayout.addRow("Address:", self.addressEdit)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.updateCustomer)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def updateCustomer(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE Customers SET name = ?, email = ?, phone_number = ?, address = ? WHERE customer_id = ?",
                        (self.nameEdit.text(), self.emailEdit.text(), self.phoneEdit.text(), self.addressEdit.text(), self.customerData.get("customer_id")))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Customer updated!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Update failed:\n{e}")
            self.reject()

# -------------------- Main Window --------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventory Billing Program")
        self.setGeometry(100, 100, 1200, 800)
        self.initUI()

    def initUI(self):
        mainLayout = QVBoxLayout()
        # Header label
        headerLabel = QLabel("Inventory Billing Program")
        headerLabel.setFont(QFont("Arial", 28, QFont.Bold))
        headerLabel.setAlignment(Qt.AlignCenter)
        mainLayout.addWidget(headerLabel)
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { padding: 10px; margin: 2px; }")
        self.tabs.addTab(self.createProductsTab(), "Products")
        self.tabs.addTab(self.createInvoicesTab(), "Invoices")
        self.tabs.addTab(self.createSuppliersTab(), "Suppliers")
        self.tabs.addTab(self.createCategoriesTab(), "Categories")
        self.tabs.addTab(self.createCustomersTab(), "Customers")
        self.tabs.addTab(self.createUsersTab(), "Users")
        mainLayout.addWidget(self.tabs)
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)

    # ---------- Products Tab ----------
    def createProductsTab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        toolbar = QHBoxLayout()
        for text, slot in [("Add Product", self.addProduct), 
                           ("Edit Product", self.editProduct),
                           ("Delete Product", self.deleteProduct),
                           ("Refresh", self.refreshProducts)]:
            btn = QPushButton(text)
            btn.setStyleSheet("padding: 8px;")
            toolbar.addWidget(btn)
            btn.clicked.connect(slot)
        toolbar.addStretch()
        self.productsTable = QTableView()
        self.productsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addLayout(toolbar)
        layout.addWidget(self.productsTable)
        widget.setLayout(layout)
        self.refreshProducts()
        return widget

    def refreshProducts(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM Products")
            data = cur.fetchall()
            conn.close()
            headers = list(data[0].keys()) if data else ["product_id", "name", "category_id", "supplier_id", "price", "stock_quantity", "barcode", "created_at"]
            model = TableModel(data, headers)
            self.productsTable.setModel(model)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load products failed:\n{e}")

    def addProduct(self):
        dialog = ProductDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshProducts()

    def editProduct(self):
        idx = self.productsTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select a product to edit.")
            return
        row = idx[0].row()
        productData = self.productsTable.model().getRow(row)
        dialog = EditProductDialog(self, productData)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshProducts()

    def deleteProduct(self):
        idx = self.productsTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select a product to delete.")
            return
        row = idx[0].row()
        productData = self.productsTable.model().getRow(row)
        pid = productData.get("product_id")
        confirm = QMessageBox.question(self, "Confirm Delete",
                f"Delete product '{productData.get('name')}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM Products WHERE product_id = ?", (pid,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", "Product deleted!")
                self.refreshProducts()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete product failed:\n{e}")

    # ---------- Invoices Tab ----------
    def createInvoicesTab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        toolbar = QHBoxLayout()
        for text, slot in [("Add Invoice", self.addInvoice),
                           ("Edit Invoice", self.editInvoice),
                           ("Delete Invoice", self.deleteInvoice),
                           ("Export Invoice PDF", self.exportInvoicePDF),
                           ("Refresh", self.refreshInvoices)]:
            btn = QPushButton(text)
            btn.setStyleSheet("padding: 8px;")
            toolbar.addWidget(btn)
            btn.clicked.connect(slot)
        toolbar.addStretch()
        self.invoicesTable = QTableView()
        self.invoicesTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addLayout(toolbar)
        layout.addWidget(self.invoicesTable)
        widget.setLayout(layout)
        self.refreshInvoices()
        return widget

    def refreshInvoices(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM Invoices")
            data = cur.fetchall()
            conn.close()
            headers = list(data[0].keys()) if data else ["invoice_id", "customer_id", "user_id", "total_amount", "payment_status", "created_at"]
            model = TableModel(data, headers)
            self.invoicesTable.setModel(model)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load invoices failed:\n{e}")

    def addInvoice(self):
        dialog = InvoiceDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshInvoices()

    def editInvoice(self):
        idx = self.invoicesTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select an invoice to edit.")
            return
        row = idx[0].row()
        invoiceData = self.invoicesTable.model().getRow(row)
        dialog = InvoiceDialog(self, invoiceData)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshInvoices()

    def deleteInvoice(self):
        idx = self.invoicesTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select an invoice to delete.")
            return
        row = idx[0].row()
        invoiceData = self.invoicesTable.model().getRow(row)
        iid = invoiceData.get("invoice_id")
        confirm = QMessageBox.question(self, "Confirm Delete",
                f"Delete invoice ID '{iid}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM Invoice_Items WHERE invoice_id = ?", (iid,))
                cur.execute("DELETE FROM Invoices WHERE invoice_id = ?", (iid,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", "Invoice deleted!")
                self.refreshInvoices()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete invoice failed:\n{e}")


#     from reportlab.lib import colors
# from reportlab.lib.pagesizes import A4

# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
# from reportlab.lib.styles import getSampleStyleSheet
# from reportlab.pdfgen import canvas

    def exportInvoicePDF(self):
        # Get selected row from the invoices table
        idx = self.invoicesTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select an invoice to export.")
            return
        row = idx[0].row()
        invoiceData = self.invoicesTable.model().getRow(row)
        invoice_id = invoiceData.get("invoice_id")
        customer_id = invoiceData.get("customer_id")  # Assuming invoiceData has customer_id

        try:
            # Connect to the database
            conn = get_connection()
            cur = conn.cursor()

            # Retrieve invoice items with associated product details
            cur.execute("""
                SELECT ii.product_id, p.name as product_name, ii.quantity, ii.price_per_item 
                FROM Invoice_Items ii 
                JOIN Products p ON ii.product_id = p.product_id 
                WHERE invoice_id = ?
            """, (invoice_id,))
            items = cur.fetchall()
            items = [dict(i) for i in items]

            # Retrieve customer name using the customer_id
            cur.execute("SELECT name FROM Customers WHERE customer_id = ?", (customer_id,))
            result = cur.fetchone()
            if result:
                customer_name = result["name"]
            else:
                customer_name = "Unknown"
            conn.close()

            # Build the PDF file
            pdf_file = f"Invoice_{invoice_id}.pdf"
            doc = SimpleDocTemplate(pdf_file, pagesize=A4,
                                    rightMargin=20*mm, leftMargin=20*mm,
                                    topMargin=40*mm, bottomMargin=20*mm)
            styles = getSampleStyleSheet()
            elements = []

            # Invoice Header Section
            header_title = Paragraph(f"<b>Invoice #{invoice_id}</b>", styles["Title"])
            elements.append(header_title)
            elements.append(Spacer(1, 12))

            # Invoice Details Table with customer name included
            details = [
                ["Invoice Date:", invoiceData.get("created_at")],
                ["Customer Name:", customer_name],
                ["Total Amount:", f"${invoiceData.get('total_amount'):.2f}"]
            ]
            details_table = Table(details, colWidths=[120, 300])
            details_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(details_table)
            elements.append(Spacer(1, 12))

            # Invoice Items Table
            table_data = [["Product ID", "Product Name", "Quantity", "Price per Item", "Total"]]
            for item in items:
                total_price = item["quantity"] * item["price_per_item"]
                table_data.append([
                    item["product_id"],
                    item["product_name"],
                    item["quantity"],
                    f"${item['price_per_item']:.2f}",
                    f"${total_price:.2f}"
                ])
            items_table = Table(table_data, colWidths=[60, 200, 50, 80, 80])
            items_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8)
            ]))
            elements.append(items_table)
            elements.append(Spacer(1, 24))

            # Additional Notes
            notes = Paragraph("Please contact us if you have any questions regarding this invoice.", styles["Normal"])
            elements.append(notes)

            # Advanced Header/Footer Callback Function
            def draw_header_footer(c: canvas.Canvas, doc_obj):
                c.saveState()
                width, height = A4

                # Draw Header Background
                c.setFillColorRGB(0.2, 0.5, 0.8)  # blue tone
                c.rect(0, height - 60, width, 60, fill=1, stroke=0)

                # Draw Company Logo if available
                try:
                    logo = "logo.png"  # Adjust the image path as needed
                    c.drawImage(logo, 20, height - 50, width=40, height=40, preserveAspectRatio=True)
                except Exception:
                    pass

                # Header Text: Company Name and Tagline
                c.setFillColor(colors.whitesmoke)
                c.setFont("Helvetica-Bold", 16)
                c.drawString(70, height - 35, "Inventory Billing System")
                c.setFont("Helvetica", 10)
                c.drawString(70, height - 50, "Innovative Solutions for Modern Business")

                # Draw Footer Background
                c.setFillColorRGB(0.2, 0.5, 0.8)
                c.rect(0, 0, width, 30, fill=1, stroke=0)
                c.setFillColor(colors.whitesmoke)
                c.setFont("Helvetica", 9)
                # Page Number Centered
                page_number_text = f"Page {c.getPageNumber()}"
                c.drawCentredString(width / 2, 10, page_number_text)
                # Footer Message on the Right
                c.drawRightString(width - 20, 10, "Thank you for your business!")
                c.restoreState()

            # Build the PDF with the header/footer callback
            doc.build(elements, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
            QMessageBox.information(self, "PDF Exported", f"Invoice exported as {pdf_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"PDF export failed:\n{e}")




    # ---------- Suppliers Tab ----------
    def createSuppliersTab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        toolbar = QHBoxLayout()
        for text, slot in [("Add Supplier", self.addSupplier),
                           ("Edit Supplier", self.editSupplier),
                           ("Delete Supplier", self.deleteSupplier),
                           ("Refresh", self.refreshSuppliers)]:
            btn = QPushButton(text)
            btn.setStyleSheet("padding: 8px;")
            toolbar.addWidget(btn)
            btn.clicked.connect(slot)
        toolbar.addStretch()
        self.suppliersTable = QTableView()
        self.suppliersTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addLayout(toolbar)
        layout.addWidget(self.suppliersTable)
        widget.setLayout(layout)
        self.refreshSuppliers()
        return widget

    def refreshSuppliers(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM Suppliers")
            data = cur.fetchall()
            conn.close()
            headers = list(data[0].keys()) if data else ["supplier_id", "name", "contact_name", "contact_email", "phone_number"]
            model = TableModel(data, headers)
            self.suppliersTable.setModel(model)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load suppliers failed:\n{e}")

    def addSupplier(self):
        dialog = AddSupplierDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshSuppliers()

    def editSupplier(self):
        idx = self.suppliersTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select a supplier to edit.")
            return
        row = idx[0].row()
        supplierData = self.suppliersTable.model().getRow(row)
        dialog = EditSupplierDialog(self, supplierData)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshSuppliers()

    def deleteSupplier(self):
        idx = self.suppliersTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select a supplier to delete.")
            return
        row = idx[0].row()
        supplierData = self.suppliersTable.model().getRow(row)
        sid = supplierData.get("supplier_id")
        confirm = QMessageBox.question(self, "Confirm Delete",
                f"Delete supplier '{supplierData.get('name')}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM Suppliers WHERE supplier_id = ?", (sid,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", "Supplier deleted!")
                self.refreshSuppliers()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete supplier failed:\n{e}")

    # ---------- Categories Tab ----------
    def createCategoriesTab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        toolbar = QHBoxLayout()
        for text, slot in [("Add Category", self.addCategory),
                           ("Edit Category", self.editCategory),
                           ("Delete Category", self.deleteCategory),
                           ("Refresh", self.refreshCategories)]:
            btn = QPushButton(text)
            btn.setStyleSheet("padding: 8px;")
            toolbar.addWidget(btn)
            btn.clicked.connect(slot)
        toolbar.addStretch()
        self.categoriesTable = QTableView()
        self.categoriesTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addLayout(toolbar)
        layout.addWidget(self.categoriesTable)
        widget.setLayout(layout)
        self.refreshCategories()
        return widget

    def refreshCategories(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM Categories")
            data = cur.fetchall()
            conn.close()
            headers = list(data[0].keys()) if data else ["category_id", "category_name"]
            model = TableModel(data, headers)
            self.categoriesTable.setModel(model)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load categories failed:\n{e}")

    def addCategory(self):
        dialog = AddCategoryDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshCategories()

    def editCategory(self):
        idx = self.categoriesTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select a category to edit.")
            return
        row = idx[0].row()
        categoryData = self.categoriesTable.model().getRow(row)
        dialog = EditCategoryDialog(self, categoryData)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshCategories()

    def deleteCategory(self):
        idx = self.categoriesTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select a category to delete.")
            return
        row = idx[0].row()
        categoryData = self.categoriesTable.model().getRow(row)
        cid = categoryData.get("category_id")
        confirm = QMessageBox.question(self, "Confirm Delete",
                f"Delete category '{categoryData.get('category_name')}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM Categories WHERE category_id = ?", (cid,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", "Category deleted!")
                self.refreshCategories()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete category failed:\n{e}")

    # ---------- Customers Tab ----------
    def createCustomersTab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        toolbar = QHBoxLayout()
        for text, slot in [("Add Customer", self.addCustomer),
                           ("Edit Customer", self.editCustomer),
                           ("Delete Customer", self.deleteCustomer),
                           ("Refresh", self.refreshCustomers)]:
            btn = QPushButton(text)
            btn.setStyleSheet("padding: 8px;")
            toolbar.addWidget(btn)
            btn.clicked.connect(slot)
        toolbar.addStretch()
        self.customersTable = QTableView()
        self.customersTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addLayout(toolbar)
        layout.addWidget(self.customersTable)
        widget.setLayout(layout)
        self.refreshCustomers()
        return widget

    def refreshCustomers(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM Customers")
            data = cur.fetchall()
            conn.close()
            headers = list(data[0].keys()) if data else ["customer_id", "name", "email", "phone_number", "address"]
            model = TableModel(data, headers)
            self.customersTable.setModel(model)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load customers failed:\n{e}")

    def addCustomer(self):
        dialog = AddCustomerDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshCustomers()

    def editCustomer(self):
        idx = self.customersTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select a customer to edit.")
            return
        row = idx[0].row()
        customerData = self.customersTable.model().getRow(row)
        dialog = EditCustomerDialog(self, customerData)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshCustomers()

    def deleteCustomer(self):
        idx = self.customersTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select a customer to delete.")
            return
        row = idx[0].row()
        customerData = self.customersTable.model().getRow(row)
        cid = customerData.get("customer_id")
        confirm = QMessageBox.question(self, "Confirm Delete",
                f"Delete customer '{customerData.get('name')}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM Customers WHERE customer_id = ?", (cid,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", "Customer deleted!")
                self.refreshCustomers()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete customer failed:\n{e}")

    # ---------- Users Tab ----------
    def createUsersTab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        toolbar = QHBoxLayout()
        for text, slot in [("Add User", self.addUser),
                           ("Edit User", self.editUser),
                           ("Delete User", self.deleteUser),
                           ("Refresh", self.refreshUsers)]:
            btn = QPushButton(text)
            btn.setStyleSheet("padding: 8px;")
            toolbar.addWidget(btn)
            btn.clicked.connect(slot)
        toolbar.addStretch()
        self.usersTable = QTableView()
        self.usersTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addLayout(toolbar)
        layout.addWidget(self.usersTable)
        widget.setLayout(layout)
        self.refreshUsers()
        return widget

    def refreshUsers(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM Users")
            data = cur.fetchall()
            conn.close()
            headers = list(data[0].keys()) if data else ["user_id", "username", "password_hash", "role"]
            model = TableModel(data, headers)
            self.usersTable.setModel(model)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load users failed:\n{e}")

    def addUser(self):
        dialog = AddUserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshUsers()

    def editUser(self):
        idx = self.usersTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select a user to edit.")
            return
        row = idx[0].row()
        userData = self.usersTable.model().getRow(row)
        dialog = EditUserDialog(self, userData)
        if dialog.exec_() == QDialog.Accepted:
            self.refreshUsers()

    def deleteUser(self):
        idx = self.usersTable.selectionModel().selectedRows()
        if not idx:
            QMessageBox.warning(self, "Warning", "Select a user to delete.")
            return
        row = idx[0].row()
        userData = self.usersTable.model().getRow(row)
        uid = userData.get("user_id")
        confirm = QMessageBox.question(self, "Confirm Delete",
                f"Delete user '{userData.get('username')}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM Users WHERE user_id = ?", (uid,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", "User deleted!")
                self.refreshUsers()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete user failed:\n{e}")

# -------------------- Product Dialog (Add) --------------------
class ProductDialog(QDialog):
    def __init__(self, parent=None):
        super(ProductDialog, self).__init__(parent)
        self.setWindowTitle("Add Product")
        self.initUI()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.nameEdit = QLineEdit(self); self.nameEdit.setFont(QFont("Arial", 14))
        self.priceEdit = QLineEdit(self); self.priceEdit.setFont(QFont("Arial", 14))
        self.stockEdit = QLineEdit(self); self.stockEdit.setFont(QFont("Arial", 14))
        self.categoryCombo = QComboBox(self); self.categoryCombo.setFont(QFont("Arial", 14))
        self.supplierCombo = QComboBox(self); self.supplierCombo.setFont(QFont("Arial", 14))
        self.populateCategories()
        self.populateSuppliers()
        self.formLayout.addRow("Name:", self.nameEdit)
        self.formLayout.addRow("Category:", self.categoryCombo)
        self.formLayout.addRow("Supplier:", self.supplierCombo)
        self.formLayout.addRow("Price:", self.priceEdit)
        self.formLayout.addRow("Stock Quantity:", self.stockEdit)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.addProduct)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def populateCategories(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT category_id, category_name FROM Categories ORDER BY category_name")
            cats = cur.fetchall()
            conn.close()
            self.categoryCombo.clear()
            if cats:
                self.categoryCombo.addItem("Select Category", None)
                for cat in cats:
                    self.categoryCombo.addItem(cat["category_name"], cat["category_id"])
            else:
                self.categoryCombo.addItem("No Category Available", None)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load categories failed:\n{e}")

    def populateSuppliers(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT supplier_id, name FROM Suppliers ORDER BY name")
            sups = cur.fetchall()
            conn.close()
            self.supplierCombo.clear()
            if sups:
                self.supplierCombo.addItem("Select Supplier", None)
                for sup in sups:
                    self.supplierCombo.addItem(sup["name"], sup["supplier_id"])
            else:
                self.supplierCombo.addItem("No Supplier Available", None)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load suppliers failed:\n{e}")

    def addProduct(self):
        cat_id = self.categoryCombo.currentData()
        sup_id = self.supplierCombo.currentData()
        if cat_id is None:
            QMessageBox.critical(self, "Error", "Select a valid category.")
            return
        if sup_id is None:
            QMessageBox.critical(self, "Error", "Select a valid supplier.")
            return
        unique_code = uuid.uuid4().hex[:8]
        barcode_data = "BC-" + unique_code
        barcode_file = generate_barcode_image(barcode_data)
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO Products (name, category_id, supplier_id, price, stock_quantity, barcode)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (self.nameEdit.text(), cat_id, sup_id, float(self.priceEdit.text()), int(self.stockEdit.text()), barcode_file))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Product added!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Add product failed:\n{e}")
            self.reject()

class AddSupplierDialog(QDialog):
    def __init__(self, parent=None):
        super(AddSupplierDialog, self).__init__(parent)
        self.setWindowTitle("Add Supplier")
        self.initUI()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.nameEdit = QLineEdit(self); self.nameEdit.setFont(QFont("Arial", 14))
        self.contactNameEdit = QLineEdit(self); self.contactNameEdit.setFont(QFont("Arial", 14))
        self.contactEmailEdit = QLineEdit(self); self.contactEmailEdit.setFont(QFont("Arial", 14))
        self.phoneEdit = QLineEdit(self); self.phoneEdit.setFont(QFont("Arial", 14))
        self.formLayout.addRow("Name:", self.nameEdit)
        self.formLayout.addRow("Contact Name:", self.contactNameEdit)
        self.formLayout.addRow("Contact Email:", self.contactEmailEdit)
        self.formLayout.addRow("Phone Number:", self.phoneEdit)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.addSupplier)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def addSupplier(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO Suppliers (name, contact_name, contact_email, phone_number)
                VALUES (?, ?, ?, ?)
            """, (self.nameEdit.text(), self.contactNameEdit.text(), self.contactEmailEdit.text(), self.phoneEdit.text()))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Supplier added!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Add supplier failed:\n{e}")
            self.reject()

# -------------------- Edit Supplier Dialog --------------------
class EditSupplierDialog(QDialog):
    def __init__(self, parent=None, supplierData=None):
        super(EditSupplierDialog, self).__init__(parent)
        self.setWindowTitle("Edit Supplier")
        self.supplierData = supplierData
        self.initUI()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.nameEdit = QLineEdit(self); self.nameEdit.setFont(QFont("Arial", 14))
        self.contactNameEdit = QLineEdit(self); self.contactNameEdit.setFont(QFont("Arial", 14))
        self.contactEmailEdit = QLineEdit(self); self.contactEmailEdit.setFont(QFont("Arial", 14))
        self.phoneEdit = QLineEdit(self); self.phoneEdit.setFont(QFont("Arial", 14))
        self.nameEdit.setText(self.supplierData.get("name", ""))
        self.contactNameEdit.setText(self.supplierData.get("contact_name", ""))
        self.contactEmailEdit.setText(self.supplierData.get("contact_email", ""))
        self.phoneEdit.setText(self.supplierData.get("phone_number", ""))
        self.formLayout.addRow("Name:", self.nameEdit)
        self.formLayout.addRow("Contact Name:", self.contactNameEdit)
        self.formLayout.addRow("Contact Email:", self.contactEmailEdit)
        self.formLayout.addRow("Phone Number:", self.phoneEdit)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.updateSupplier)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def updateSupplier(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE Suppliers
                SET name = ?, contact_name = ?, contact_email = ?, phone_number = ?
                WHERE supplier_id = ?
            """, (self.nameEdit.text(), self.contactNameEdit.text(), self.contactEmailEdit.text(), self.phoneEdit.text(), self.supplierData.get("supplier_id")))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Supplier updated!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Update failed:\n{e}")
            self.reject()

# -------------------- Edit Product Dialog --------------------
class EditProductDialog(QDialog):
    def __init__(self, parent=None, productData=None):
        super(EditProductDialog, self).__init__(parent)
        self.setWindowTitle("Edit Product")
        self.productData = productData
        self.initUI()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.nameEdit = QLineEdit(self); self.nameEdit.setFont(QFont("Arial", 14))
        self.priceEdit = QLineEdit(self); self.priceEdit.setFont(QFont("Arial", 14))
        self.stockEdit = QLineEdit(self); self.stockEdit.setFont(QFont("Arial", 14))
        self.categoryCombo = QComboBox(self); self.categoryCombo.setFont(QFont("Arial", 14))
        self.supplierCombo = QComboBox(self); self.supplierCombo.setFont(QFont("Arial", 14))
        self.populateCategories()
        self.populateSuppliers()
        self.nameEdit.setText(self.productData.get("name", ""))
        self.priceEdit.setText(str(self.productData.get("price", "")))
        self.stockEdit.setText(str(self.productData.get("stock_quantity", "")))
        cur_cat = self.productData.get("category_id")
        cur_sup = self.productData.get("supplier_id")
        index_cat = self.categoryCombo.findData(cur_cat)
        if index_cat >= 0:
            self.categoryCombo.setCurrentIndex(index_cat)
        index_sup = self.supplierCombo.findData(cur_sup)
        if index_sup >= 0:
            self.supplierCombo.setCurrentIndex(index_sup)
        self.formLayout.addRow("Name:", self.nameEdit)
        self.formLayout.addRow("Category:", self.categoryCombo)
        self.formLayout.addRow("Supplier:", self.supplierCombo)
        self.formLayout.addRow("Price:", self.priceEdit)
        self.formLayout.addRow("Stock Quantity:", self.stockEdit)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.updateProduct)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def populateCategories(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT category_id, category_name FROM Categories ORDER BY category_name")
            cats = cur.fetchall()
            conn.close()
            self.categoryCombo.clear()
            if cats:
                self.categoryCombo.addItem("Select Category", None)
                for cat in cats:
                    self.categoryCombo.addItem(cat["category_name"], cat["category_id"])
            else:
                self.categoryCombo.addItem("No Category Available", None)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load categories failed:\n{e}")

    def populateSuppliers(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT supplier_id, name FROM Suppliers ORDER BY name")
            sups = cur.fetchall()
            conn.close()
            self.supplierCombo.clear()
            if sups:
                self.supplierCombo.addItem("Select Supplier", None)
                for sup in sups:
                    self.supplierCombo.addItem(sup["name"], sup["supplier_id"])
            else:
                self.supplierCombo.addItem("No Supplier Available", None)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load suppliers failed:\n{e}")

    def updateProduct(self):
        cat_id = self.categoryCombo.currentData()
        sup_id = self.supplierCombo.currentData()
        if cat_id is None:
            QMessageBox.critical(self, "Error", "Select a valid category.")
            return
        if sup_id is None:
            QMessageBox.critical(self, "Error", "Select a valid supplier.")
            return
        pid = self.productData.get("product_id")
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE Products
                SET name = ?, category_id = ?, supplier_id = ?, price = ?, stock_quantity = ?
                WHERE product_id = ?
            """, (self.nameEdit.text(), cat_id, sup_id, float(self.priceEdit.text()), int(self.stockEdit.text()), pid))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Product updated!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Update product failed:\n{e}")
            self.reject()

# -------------------- Invoice Dialog (Detailed) --------------------
class InvoiceDialog(QDialog):
    def __init__(self, parent=None, invoiceData=None):
        super(InvoiceDialog, self).__init__(parent)
        self.invoiceData = invoiceData
        if invoiceData:
            self.setWindowTitle("Edit Invoice")
        else:
            self.setWindowTitle("Add Invoice")
        self.invoiceItems = []  # List of dicts: {product_id, product_name, quantity, price_per_item}
        self.initUI()
        if invoiceData:
            self.loadInvoiceData()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.customerCombo = QComboBox(self)
        self.userCombo = QComboBox(self)
        for widget in (self.customerCombo, self.userCombo):
            widget.setFont(QFont("Arial", 14))
        self.populateCustomers()
        self.populateUsers()
        self.paymentStatusCombo = QComboBox(self)
        self.paymentStatusCombo.setFont(QFont("Arial", 14))
        self.paymentStatusCombo.addItems(["paid", "pending"])
        self.itemsTable = QTableWidget(0, 4, self)
        self.itemsTable.setHorizontalHeaderLabels(["Product ID", "Product Name", "Quantity", "Price"])
        self.itemsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.itemsTable.setFont(QFont("Arial", 14))
        self.addItemButton = QPushButton("Add Item")
        self.removeItemButton = QPushButton("Remove Selected Item")
        for btn in (self.addItemButton, self.removeItemButton):
            btn.setFont(QFont("Arial", 14))
            btn.setStyleSheet("padding: 8px;")
        self.addItemButton.clicked.connect(self.addInvoiceItem)
        self.removeItemButton.clicked.connect(self.removeInvoiceItem)
        self.totalLabel = QLabel("Total Amount: 0.00")
        self.totalLabel.setFont(QFont("Arial", 14))
        self.formLayout.addRow("Customer:", self.customerCombo)
        self.formLayout.addRow("User:", self.userCombo)
        self.formLayout.addRow("Payment Status:", self.paymentStatusCombo)
        self.formLayout.addRow("Invoice Items:", self.itemsTable)
        itemsButtonsLayout = QHBoxLayout()
        itemsButtonsLayout.addWidget(self.addItemButton)
        itemsButtonsLayout.addWidget(self.removeItemButton)
        self.formLayout.addRow("", itemsButtonsLayout)
        self.formLayout.addRow("", self.totalLabel)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.saveInvoice)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def populateCustomers(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT customer_id, name FROM Customers ORDER BY name")
            data = cur.fetchall()
            conn.close()
            self.customerCombo.clear()
            if data:
                for row in data:
                    self.customerCombo.addItem(row["name"], row["customer_id"])
            else:
                self.customerCombo.addItem("No Customer Available", None)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load customers failed:\n{e}")

    def populateUsers(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT user_id, username FROM Users ORDER BY username")
            data = cur.fetchall()
            conn.close()
            self.userCombo.clear()
            if data:
                for row in data:
                    self.userCombo.addItem(row["username"], row["user_id"])
            else:
                self.userCombo.addItem("No User Available", None)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load users failed:\n{e}")

    def addInvoiceItem(self):
        dialog = InvoiceItemDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            item = dialog.getItemData()
            self.invoiceItems.append(item)
            self.refreshItemsTable()
            self.calculateTotal()

    def removeInvoiceItem(self):
        selected = self.itemsTable.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Warning", "Select an item to remove.")
            return
        row = selected[0].row()
        del self.invoiceItems[row]
        self.refreshItemsTable()
        self.calculateTotal()

    def refreshItemsTable(self):
        self.itemsTable.setRowCount(0)
        for item in self.invoiceItems:
            rowPos = self.itemsTable.rowCount()
            self.itemsTable.insertRow(rowPos)
            self.itemsTable.setItem(rowPos, 0, QTableWidgetItem(str(item["product_id"])))
            self.itemsTable.setItem(rowPos, 1, QTableWidgetItem(item["product_name"]))
            self.itemsTable.setItem(rowPos, 2, QTableWidgetItem(str(item["quantity"])))
            self.itemsTable.setItem(rowPos, 3, QTableWidgetItem(f'{item["price_per_item"]:.2f}'))

    def calculateTotal(self):
        total = sum(item["quantity"] * item["price_per_item"] for item in self.invoiceItems)
        self.totalLabel.setText(f"Total Amount: {total:.2f}")

    def loadInvoiceData(self):
        self.customerCombo.setCurrentIndex(self.customerCombo.findData(self.invoiceData.get("customer_id")))
        self.userCombo.setCurrentIndex(self.userCombo.findData(self.invoiceData.get("user_id")))
        status = self.invoiceData.get("payment_status", "pending")
        self.paymentStatusCombo.setCurrentIndex(self.paymentStatusCombo.findText(status))
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT ii.product_id, p.name as product_name, ii.quantity, ii.price_per_item 
                FROM Invoice_Items ii JOIN Products p ON ii.product_id = p.product_id 
                WHERE invoice_id = ?
            """, (self.invoiceData.get("invoice_id"),))
            items = cur.fetchall()
            conn.close()
            self.invoiceItems = [dict(i) for i in items]
            self.refreshItemsTable()
            self.calculateTotal()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load invoice items failed:\n{e}")

    def saveInvoice(self):
        customer_id = self.customerCombo.currentData()
        user_id = self.userCombo.currentData()
        payment_status = self.paymentStatusCombo.currentText()
        total = sum(item["quantity"] * item["price_per_item"] for item in self.invoiceItems)
        if not customer_id or not user_id or not self.invoiceItems:
            QMessageBox.critical(self, "Error", "Select a valid customer, user and add at least one item.")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.invoiceData:
                invoice_id = self.invoiceData.get("invoice_id")
                cur.execute("""
                    UPDATE Invoices
                    SET customer_id = ?, user_id = ?, total_amount = ?, payment_status = ?
                    WHERE invoice_id = ?
                """, (customer_id, user_id, total, payment_status, invoice_id))
                cur.execute("DELETE FROM Invoice_Items WHERE invoice_id = ?", (invoice_id,))
            else:
                cur.execute("""
                    INSERT INTO Invoices (customer_id, user_id, total_amount, payment_status)
                    VALUES (?, ?, ?, ?)
                """, (customer_id, user_id, total, payment_status))
                invoice_id = cur.lastrowid
            for item in self.invoiceItems:
                cur.execute("""
                    INSERT INTO Invoice_Items (invoice_id, product_id, quantity, price_per_item)
                    VALUES (?, ?, ?, ?)
                """, (invoice_id, item["product_id"], item["quantity"], item["price_per_item"]))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "Invoice saved!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save invoice failed:\n{e}")
            self.reject()

# -------------------- Invoice Item Dialog --------------------
class InvoiceItemDialog(QDialog):
    def __init__(self, parent=None):
        super(InvoiceItemDialog, self).__init__(parent)
        self.setWindowTitle("Add Invoice Item")
        self.initUI()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.productCombo = QComboBox(self)
        self.productCombo.setFont(QFont("Arial", 14))
        self.populateProducts()
        self.quantityEdit = QLineEdit(self)
        self.quantityEdit.setFont(QFont("Arial", 14))
        self.priceLabel = QLabel("")
        self.priceLabel.setFont(QFont("Arial", 14))
        self.productCombo.currentIndexChanged.connect(self.updatePrice)
        self.formLayout.addRow("Product:", self.productCombo)
        self.formLayout.addRow("Quantity:", self.quantityEdit)
        self.formLayout.addRow("Price per Unit:", self.priceLabel)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def populateProducts(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT product_id, name, price FROM Products ORDER BY name")
            products = cur.fetchall()
            conn.close()
            self.productCombo.clear()
            if products:
                for p in products:
                    display = f'{p["name"]} (${p["price"]:.2f})'
                    self.productCombo.addItem(display, (p["product_id"], p["price"]))
            else:
                self.productCombo.addItem("No Product Available", None)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load products failed:\n{e}")

    def updatePrice(self):
        data = self.productCombo.currentData()
        if data:
            self.priceLabel.setText(f'{data[1]:.2f}')
        else:
            self.priceLabel.setText("0.00")

    def getItemData(self):
        data = self.productCombo.currentData()
        if data:
            product_id, price = data
        else:
            product_id, price = None, 0.0
        try:
            quantity = int(self.quantityEdit.text())
        except:
            quantity = 0
        product_name = self.productCombo.currentText().split(" ($")[0]
        return {"product_id": product_id, "product_name": product_name, "quantity": quantity, "price_per_item": price}

# -------------------- Add User Dialog --------------------
class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super(AddUserDialog, self).__init__(parent)
        self.setWindowTitle("Add User")
        self.initUI()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.usernameEdit = QLineEdit(self); self.usernameEdit.setFont(QFont("Arial", 14))
        self.passwordEdit = QLineEdit(self); self.passwordEdit.setFont(QFont("Arial", 14))
        self.passwordEdit.setEchoMode(QLineEdit.Password)
        self.roleCombo = QComboBox(self); self.roleCombo.setFont(QFont("Arial", 14))
        self.roleCombo.addItems(["admin", "cashier"])
        self.formLayout.addRow("Username:", self.usernameEdit)
        self.formLayout.addRow("Password:", self.passwordEdit)
        self.formLayout.addRow("Role:", self.roleCombo)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.addUser)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def addUser(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO Users (username, password_hash, role) VALUES (?, ?, ?)",
                        (self.usernameEdit.text(), self.passwordEdit.text(), self.roleCombo.currentText()))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "User added!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Add user failed:\n{e}")
            self.reject()

# -------------------- Edit User Dialog --------------------
class EditUserDialog(QDialog):
    def __init__(self, parent=None, userData=None):
        super(EditUserDialog, self).__init__(parent)
        self.setWindowTitle("Edit User")
        self.userData = userData
        self.initUI()

    def initUI(self):
        self.formLayout = QFormLayout(self)
        self.usernameEdit = QLineEdit(self); self.usernameEdit.setFont(QFont("Arial", 14))
        self.passwordEdit = QLineEdit(self); self.passwordEdit.setFont(QFont("Arial", 14))
        self.passwordEdit.setEchoMode(QLineEdit.Password)
        self.roleCombo = QComboBox(self); self.roleCombo.setFont(QFont("Arial", 14))
        self.roleCombo.addItems(["admin", "cashier"])
        self.usernameEdit.setText(self.userData.get("username", ""))
        self.formLayout.addRow("Username:", self.usernameEdit)
        self.formLayout.addRow("Password:", self.passwordEdit)
        self.formLayout.addRow("Role:", self.roleCombo)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.button(QDialogButtonBox.Ok).setFont(QFont("Arial", 14))
        self.buttonBox.button(QDialogButtonBox.Cancel).setFont(QFont("Arial", 14))
        self.buttonBox.accepted.connect(self.updateUser)
        self.buttonBox.rejected.connect(self.reject)
        self.formLayout.addWidget(self.buttonBox)

    def updateUser(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.passwordEdit.text().strip() == "":
                cur.execute("UPDATE Users SET username = ?, role = ? WHERE user_id = ?",
                            (self.usernameEdit.text(), self.roleCombo.currentText(), self.userData.get("user_id")))
            else:
                cur.execute("UPDATE Users SET username = ?, password_hash = ?, role = ? WHERE user_id = ?",
                            (self.usernameEdit.text(), self.passwordEdit.text(), self.roleCombo.currentText(), self.userData.get("user_id")))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", "User updated!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Update user failed:\n{e}")
            self.reject()

# -------------------- Main --------------------
def main():
    app = QApplication(sys.argv)
    style = qdarkstyle.load_stylesheet_pyqt5() + """
        QLineEdit, QComboBox, QLabel, QTableWidget, QTableView { font-size: 14px; }
        QPushButton { font-size: 14px; padding: 8px; }
        QTabBar::tab { padding: 10px; margin: 2px; }
    """
    app.setStyleSheet(style)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
   main()