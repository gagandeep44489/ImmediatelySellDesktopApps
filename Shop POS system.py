import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk


class POSDatabase:
    def __init__(self, db_path: str = "shop_pos.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._seed_default_products()

    def _create_tables(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sold_at TEXT NOT NULL,
                total REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY(sale_id) REFERENCES sales(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
            """
        )
        self.conn.commit()

    def _seed_default_products(self) -> None:
        existing = self.conn.execute("SELECT COUNT(*) AS count FROM products").fetchone()["count"]
        if existing:
            return
        defaults = [
            ("Milk", 1.99, 30),
            ("Bread", 1.49, 25),
            ("Eggs (12)", 2.99, 20),
            ("Coffee", 5.50, 15),
            ("Rice 1kg", 3.20, 40),
        ]
        self.conn.executemany(
            "INSERT INTO products(name, price, stock) VALUES (?, ?, ?)", defaults
        )
        self.conn.commit()

    def get_products(self):
        return self.conn.execute(
            "SELECT id, name, price, stock FROM products ORDER BY name"
        ).fetchall()

    def add_product(self, name: str, price: float, stock: int) -> None:
        self.conn.execute(
            "INSERT INTO products(name, price, stock) VALUES (?, ?, ?)",
            (name, price, stock),
        )
        self.conn.commit()

    def record_sale(self, cart_items):
        total = sum(item["line_total"] for item in cart_items)
        sold_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO sales(sold_at, total) VALUES (?, ?)", (sold_at, total))
        sale_id = cursor.lastrowid

        for item in cart_items:
            cursor.execute(
                """
                INSERT INTO sale_items(sale_id, product_id, quantity, unit_price, line_total)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    sale_id,
                    item["product_id"],
                    item["quantity"],
                    item["unit_price"],
                    item["line_total"],
                ),
            )
            cursor.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )

        self.conn.commit()
        return sale_id, sold_at, total

    def recent_sales(self, limit: int = 10):
        return self.conn.execute(
            "SELECT id, sold_at, total FROM sales ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


class POSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Shop POS System")
        self.geometry("980x600")
        self.minsize(900, 520)

        self.db = POSDatabase()
        self.cart = []

        self._build_ui()
        self.refresh_products()
        self.refresh_sales()

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=2)
        root.columnconfigure(1, weight=2)
        root.columnconfigure(2, weight=1)
        root.rowconfigure(1, weight=1)

        ttk.Label(root, text="Product Catalog", font=("Arial", 13, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(root, text="Cart", font=("Arial", 13, "bold")).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(root, text="New Product", font=("Arial", 13, "bold")).grid(
            row=0, column=2, sticky="w"
        )

        self.products_tree = ttk.Treeview(
            root,
            columns=("id", "name", "price", "stock"),
            show="headings",
            selectmode="browse",
            height=16,
        )
        for col, width in (("id", 60), ("name", 220), ("price", 80), ("stock", 70)):
            self.products_tree.heading(col, text=col.upper())
            self.products_tree.column(col, width=width, anchor="center")
        self.products_tree.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        cart_frame = ttk.Frame(root)
        cart_frame.grid(row=1, column=1, sticky="nsew", padx=(0, 10))
        cart_frame.columnconfigure(0, weight=1)
        cart_frame.rowconfigure(0, weight=1)

        self.cart_tree = ttk.Treeview(
            cart_frame,
            columns=("name", "qty", "unit", "line"),
            show="headings",
            height=16,
        )
        for col, width in (("name", 190), ("qty", 50), ("unit", 70), ("line", 80)):
            self.cart_tree.heading(col, text=col.upper())
            self.cart_tree.column(col, width=width, anchor="center")
        self.cart_tree.grid(row=0, column=0, sticky="nsew")

        controls = ttk.Frame(cart_frame)
        controls.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(controls, text="Qty").pack(side=tk.LEFT)
        self.qty_var = tk.StringVar(value="1")
        ttk.Entry(controls, width=5, textvariable=self.qty_var).pack(side=tk.LEFT, padx=6)
        ttk.Button(controls, text="Add to Cart", command=self.add_to_cart).pack(side=tk.LEFT)
        ttk.Button(controls, text="Remove Selected", command=self.remove_selected_from_cart).pack(
            side=tk.LEFT, padx=6
        )

        self.total_var = tk.StringVar(value="Total: $0.00")
        ttk.Label(cart_frame, textvariable=self.total_var, font=("Arial", 11, "bold")).grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Button(cart_frame, text="Checkout", command=self.checkout).grid(
            row=3, column=0, sticky="ew", pady=(8, 0)
        )

        add_frame = ttk.Frame(root)
        add_frame.grid(row=1, column=2, sticky="nsew")
        self.name_var = tk.StringVar()
        self.price_var = tk.StringVar()
        self.stock_var = tk.StringVar(value="0")

        ttk.Label(add_frame, text="Name").pack(anchor="w")
        ttk.Entry(add_frame, textvariable=self.name_var).pack(fill=tk.X, pady=(0, 6))
        ttk.Label(add_frame, text="Price").pack(anchor="w")
        ttk.Entry(add_frame, textvariable=self.price_var).pack(fill=tk.X, pady=(0, 6))
        ttk.Label(add_frame, text="Stock").pack(anchor="w")
        ttk.Entry(add_frame, textvariable=self.stock_var).pack(fill=tk.X, pady=(0, 8))
        ttk.Button(add_frame, text="Add Product", command=self.add_product).pack(fill=tk.X)

        sales_wrap = ttk.LabelFrame(root, text="Recent Sales")
        sales_wrap.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(12, 0))
        self.sales_tree = ttk.Treeview(
            sales_wrap, columns=("id", "time", "total"), show="headings", height=6
        )
        for col, width in (("id", 80), ("time", 220), ("total", 90)):
            self.sales_tree.heading(col, text=col.upper())
            self.sales_tree.column(col, width=width, anchor="center")
        self.sales_tree.pack(fill=tk.BOTH, expand=True)

    def refresh_products(self):
        for row in self.products_tree.get_children():
            self.products_tree.delete(row)
        for p in self.db.get_products():
            self.products_tree.insert(
                "", tk.END, values=(p["id"], p["name"], f"{p['price']:.2f}", p["stock"])
            )

    def refresh_cart(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        for item in self.cart:
            self.cart_tree.insert(
                "",
                tk.END,
                values=(
                    item["name"],
                    item["quantity"],
                    f"{item['unit_price']:.2f}",
                    f"{item['line_total']:.2f}",
                ),
            )
        total = sum(item["line_total"] for item in self.cart)
        self.total_var.set(f"Total: ${total:.2f}")

    def refresh_sales(self):
        for row in self.sales_tree.get_children():
            self.sales_tree.delete(row)
        for s in self.db.recent_sales():
            self.sales_tree.insert("", tk.END, values=(s["id"], s["sold_at"], f"{s['total']:.2f}"))

    def add_to_cart(self):
        selected = self.products_tree.selection()
        if not selected:
            messagebox.showwarning("No product", "Select a product first.")
            return

        try:
            qty = int(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid quantity", "Quantity must be a positive integer.")
            return

        values = self.products_tree.item(selected[0], "values")
        product_id = int(values[0])
        name = values[1]
        unit_price = float(values[2])
        stock = int(values[3])

        cart_qty = sum(item["quantity"] for item in self.cart if item["product_id"] == product_id)
        if cart_qty + qty > stock:
            messagebox.showerror("Insufficient stock", "Not enough items in stock.")
            return

        for item in self.cart:
            if item["product_id"] == product_id:
                item["quantity"] += qty
                item["line_total"] = item["quantity"] * item["unit_price"]
                break
        else:
            self.cart.append(
                {
                    "product_id": product_id,
                    "name": name,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "line_total": unit_price * qty,
                }
            )

        self.refresh_cart()

    def remove_selected_from_cart(self):
        selected = self.cart_tree.selection()
        if not selected:
            return
        index = self.cart_tree.index(selected[0])
        if 0 <= index < len(self.cart):
            self.cart.pop(index)
        self.refresh_cart()

    def add_product(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Invalid name", "Name cannot be empty.")
            return

        try:
            price = float(self.price_var.get())
            stock = int(self.stock_var.get())
            if price <= 0 or stock < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid values", "Price must be > 0 and stock must be >= 0."
            )
            return

        self.db.add_product(name, price, stock)
        self.name_var.set("")
        self.price_var.set("")
        self.stock_var.set("0")
        self.refresh_products()

    def checkout(self):
        if not self.cart:
            messagebox.showwarning("Empty cart", "Add at least one product to checkout.")
            return

        sale_id, sold_at, total = self.db.record_sale(self.cart)
        self.cart.clear()
        self.refresh_cart()
        self.refresh_products()
        self.refresh_sales()

        messagebox.showinfo(
            "Payment successful",
            f"Sale #{sale_id}\nTime: {sold_at}\nTotal: ${total:.2f}",
        )


if __name__ == "__main__":
    app = POSApp()
    app.mainloop()