import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk


class InventoryBarcodeApp:
    DB_NAME = "inventory_barcode.db"

    L_CODES = {
        "0": "0001101", "1": "0011001", "2": "0010011", "3": "0111101", "4": "0100011",
        "5": "0110001", "6": "0101111", "7": "0111011", "8": "0110111", "9": "0001011"
    }
    G_CODES = {
        "0": "0100111", "1": "0110011", "2": "0011011", "3": "0100001", "4": "0011101",
        "5": "0111001", "6": "0000101", "7": "0010001", "8": "0001001", "9": "0010111"
    }
    R_CODES = {
        "0": "1110010", "1": "1100110", "2": "1101100", "3": "1000010", "4": "1011100",
        "5": "1001110", "6": "1010000", "7": "1000100", "8": "1001000", "9": "1110100"
    }
    PARITY = {
        "0": "LLLLLL", "1": "LLGLGG", "2": "LLGGLG", "3": "LLGGGL", "4": "LGLLGG",
        "5": "LGGLLG", "6": "LGGGLL", "7": "LGLGLG", "8": "LGLGGL", "9": "LGGLGL"
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Inventory + Barcode System")
        self.root.geometry("1100x700")

        self.conn = sqlite3.connect(self.DB_NAME)
        self.cursor = self.conn.cursor()
        self._init_db()

        self.barcode_text = tk.StringVar()
        self.search_text = tk.StringVar()
        self._build_ui()
        self.load_items()

    def _init_db(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                sku TEXT UNIQUE NOT NULL,
                barcode TEXT UNIQUE NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL
            )
            """
        )
        self.conn.commit()

    def _build_ui(self):
        title = tk.Label(
            self.root,
            text="Inventory + Barcode System Desktop App",
            font=("Arial", 20, "bold"),
            fg="#1f2937"
        )
        title.pack(pady=10)

        form = tk.LabelFrame(self.root, text="Item Details", padx=10, pady=10)
        form.pack(fill="x", padx=12, pady=6)

        self.item_name_entry = self._add_form_row(form, "Item Name", 0)
        self.sku_entry = self._add_form_row(form, "SKU", 1)
        self.barcode_entry = self._add_form_row(form, "Barcode (12/13 digits)", 2)
        self.quantity_entry = self._add_form_row(form, "Quantity", 3)
        self.price_entry = self._add_form_row(form, "Unit Price", 4)

        button_frame = tk.Frame(form)
        button_frame.grid(row=5, column=0, columnspan=2, pady=8)

        tk.Button(button_frame, text="Add Item", width=14, command=self.add_item).grid(row=0, column=0, padx=5)
        tk.Button(button_frame, text="Update Item", width=14, command=self.update_item).grid(row=0, column=1, padx=5)
        tk.Button(button_frame, text="Delete Item", width=14, command=self.delete_item).grid(row=0, column=2, padx=5)
        tk.Button(button_frame, text="Clear", width=14, command=self.clear_inputs).grid(row=0, column=3, padx=5)

        search_frame = tk.LabelFrame(self.root, text="Find by Barcode / SKU / Name", padx=10, pady=8)
        search_frame.pack(fill="x", padx=12, pady=6)

        tk.Entry(search_frame, textvariable=self.search_text, width=45).grid(row=0, column=0, padx=6)
        tk.Button(search_frame, text="Search", width=12, command=self.search_items).grid(row=0, column=1, padx=4)
        tk.Button(search_frame, text="Show All", width=12, command=self.load_items).grid(row=0, column=2, padx=4)

        table_frame = tk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=12, pady=6)

        columns = ("id", "item_name", "sku", "barcode", "quantity", "unit_price", "stock_value")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)

        headers = {
            "id": "ID",
            "item_name": "Item Name",
            "sku": "SKU",
            "barcode": "Barcode",
            "quantity": "Quantity",
            "unit_price": "Unit Price",
            "stock_value": "Stock Value",
        }

        for col in columns:
            self.tree.heading(col, text=headers[col])
            width = 85 if col in ("id", "quantity") else 150
            self.tree.column(col, width=width, anchor="center")

        self.tree.column("item_name", width=210, anchor="w")
        self.tree.column("stock_value", width=120, anchor="center")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)

        barcode_panel = tk.LabelFrame(self.root, text="Barcode Preview (EAN-13)", padx=10, pady=8)
        barcode_panel.pack(fill="x", padx=12, pady=6)

        self.barcode_canvas = tk.Canvas(barcode_panel, width=900, height=120, bg="white", highlightthickness=0)
        self.barcode_canvas.pack(fill="x")

        self.barcode_label = tk.Label(barcode_panel, textvariable=self.barcode_text, font=("Consolas", 10, "bold"))
        self.barcode_label.pack(pady=2)

        summary_frame = tk.Frame(self.root)
        summary_frame.pack(fill="x", padx=12, pady=4)
        self.summary_label = tk.Label(summary_frame, text="", font=("Arial", 11, "bold"), anchor="w")
        self.summary_label.pack(fill="x")

    @staticmethod
    def _add_form_row(parent, label, row):
        tk.Label(parent, text=label, width=24, anchor="w").grid(row=row, column=0, sticky="w", pady=2)
        entry = tk.Entry(parent, width=35)
        entry.grid(row=row, column=1, sticky="w", pady=2)
        return entry

    def load_items(self):
        self.cursor.execute("SELECT id, item_name, sku, barcode, quantity, unit_price FROM inventory ORDER BY id DESC")
        rows = self.cursor.fetchall()
        self._render_rows(rows)

    def search_items(self):
        term = self.search_text.get().strip()
        if not term:
            self.load_items()
            return

        like_term = f"%{term}%"
        self.cursor.execute(
            """
            SELECT id, item_name, sku, barcode, quantity, unit_price
            FROM inventory
            WHERE barcode = ? OR sku LIKE ? OR item_name LIKE ?
            ORDER BY id DESC
            """,
            (term, like_term, like_term)
        )
        rows = self.cursor.fetchall()
        self._render_rows(rows)

    def _render_rows(self, rows):
        self.tree.delete(*self.tree.get_children())

        total_items = 0
        total_units = 0
        total_value = 0.0

        for row in rows:
            item_id, name, sku, barcode, qty, price = row
            stock_value = qty * price
            self.tree.insert(
                "", "end",
                values=(item_id, name, sku, barcode, qty, f"${price:.2f}", f"${stock_value:.2f}")
            )
            total_items += 1
            total_units += qty
            total_value += stock_value

        self.summary_label.config(
            text=f"Items: {total_items}   |   Units in Stock: {total_units}   |   Inventory Value: ${total_value:.2f}"
        )

    def add_item(self):
        payload = self._validate_input(require_id=False)
        if not payload:
            return

        name, sku, barcode, qty, price = payload
        try:
            self.cursor.execute(
                "INSERT INTO inventory (item_name, sku, barcode, quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
                (name, sku, barcode, qty, price),
            )
            self.conn.commit()
            self.load_items()
            self.draw_barcode(barcode)
            self.clear_inputs()
            messagebox.showinfo("Success", "Item added successfully.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate", "SKU or Barcode already exists.")

    def update_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Select an item to update.")
            return

        payload = self._validate_input(require_id=False)
        if not payload:
            return

        item_id = self.tree.item(selected[0], "values")[0]
        name, sku, barcode, qty, price = payload

        try:
            self.cursor.execute(
                """
                UPDATE inventory
                SET item_name = ?, sku = ?, barcode = ?, quantity = ?, unit_price = ?
                WHERE id = ?
                """,
                (name, sku, barcode, qty, price, item_id),
            )
            self.conn.commit()
            self.load_items()
            self.draw_barcode(barcode)
            messagebox.showinfo("Updated", "Item updated successfully.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate", "SKU or Barcode already exists.")

    def delete_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Select an item to delete.")
            return

        item_id = self.tree.item(selected[0], "values")[0]
        confirm = messagebox.askyesno("Confirm", "Delete selected item?")
        if not confirm:
            return

        self.cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        self.conn.commit()
        self.load_items()
        self.clear_inputs()

    def on_row_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return

        row = self.tree.item(selected[0], "values")
        _, name, sku, barcode, qty, price, _ = row

        self.item_name_entry.delete(0, tk.END)
        self.item_name_entry.insert(0, name)

        self.sku_entry.delete(0, tk.END)
        self.sku_entry.insert(0, sku)

        self.barcode_entry.delete(0, tk.END)
        self.barcode_entry.insert(0, barcode)

        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, qty)

        self.price_entry.delete(0, tk.END)
        self.price_entry.insert(0, str(price).replace("$", ""))

        self.draw_barcode(barcode)

    def _validate_input(self, require_id=False):
        name = self.item_name_entry.get().strip()
        sku = self.sku_entry.get().strip().upper()
        barcode = self.barcode_entry.get().strip()
        quantity = self.quantity_entry.get().strip()
        unit_price = self.price_entry.get().strip()

        if not all([name, sku, barcode, quantity, unit_price]):
            messagebox.showerror("Missing", "All fields are required.")
            return None

        if not barcode.isdigit() or len(barcode) not in (12, 13):
            messagebox.showerror("Barcode", "Barcode must be 12 or 13 digits.")
            return None

        try:
            qty = int(quantity)
            price = float(unit_price)
            if qty < 0 or price < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid", "Quantity must be integer and price must be numeric.")
            return None

        barcode13 = self.to_ean13(barcode)
        if not barcode13:
            messagebox.showerror("Barcode", "Could not generate a valid EAN-13 barcode.")
            return None

        return name, sku, barcode13, qty, price

    @staticmethod
    def to_ean13(barcode):
        if len(barcode) == 13:
            if InventoryBarcodeApp.ean13_checksum(barcode[:-1]) == barcode[-1]:
                return barcode
            return None

        if len(barcode) == 12 and barcode.isdigit():
            return barcode + InventoryBarcodeApp.ean13_checksum(barcode)
        return None

    @staticmethod
    def ean13_checksum(first_twelve):
        digits = [int(d) for d in first_twelve]
        odd_sum = sum(digits[::2])
        even_sum = sum(digits[1::2])
        check = (10 - ((odd_sum + (3 * even_sum)) % 10)) % 10
        return str(check)

    def draw_barcode(self, code):
        code = self.to_ean13(str(code))
        self.barcode_canvas.delete("all")
        if not code:
            self.barcode_text.set("")
            return

        bits = self.ean13_to_bits(code)
        x = 20
        bar_width = 2
        normal_height = 70
        guard_height = 90

        for idx, bit in enumerate(bits):
            if bit == "1":
                is_guard = idx < 3 or 45 <= idx < 50 or idx >= 92
                height = guard_height if is_guard else normal_height
                self.barcode_canvas.create_rectangle(x, 10, x + bar_width, 10 + height, fill="black", outline="")
            x += bar_width

        self.barcode_canvas.create_text(450, 110, text=code, font=("Consolas", 12, "bold"), fill="#111827")
        self.barcode_text.set(f"EAN-13: {code}")

    def ean13_to_bits(self, code):
        first = code[0]
        left = code[1:7]
        right = code[7:]

        left_pattern = self.PARITY[first]
        bits = "101"

        for digit, mode in zip(left, left_pattern):
            bits += self.L_CODES[digit] if mode == "L" else self.G_CODES[digit]

        bits += "01010"

        for digit in right:
            bits += self.R_CODES[digit]

        bits += "101"
        return bits

    def clear_inputs(self):
        for entry in [self.item_name_entry, self.sku_entry, self.barcode_entry, self.quantity_entry, self.price_entry]:
            entry.delete(0, tk.END)
        self.barcode_canvas.delete("all")
        self.barcode_text.set("")

    def on_close(self):
        self.conn.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryBarcodeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()