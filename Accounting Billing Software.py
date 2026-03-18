import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


@dataclass
class InvoiceItem:
    product: str
    qty: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.qty * self.unit_price


class AccountingBillingApp:
    TAX_RATE = 0.18

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Accounting / Billing Software")
        self.root.geometry("980x650")

        self.items: list[InvoiceItem] = []
        self.sales_ledger: dict[str, int] = {}

        self._build_ui()
        self._refresh_totals()

    def _build_ui(self) -> None:
        title = ttk.Label(
            self.root,
            text="Accounting / Billing Software (Desktop)",
            font=("Segoe UI", 17, "bold"),
        )
        title.pack(pady=10)

        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill="x")

        self.customer_name_var = tk.StringVar()
        self.customer_phone_var = tk.StringVar()
        self.invoice_no_var = tk.StringVar(value=f"INV-{dt.datetime.now():%Y%m%d-%H%M%S}")

        ttk.Label(top_frame, text="Invoice #").grid(row=0, column=0, sticky="w")
        ttk.Entry(top_frame, textvariable=self.invoice_no_var, width=25).grid(
            row=1, column=0, padx=(0, 10), sticky="w"
        )

        ttk.Label(top_frame, text="Customer Name").grid(row=0, column=1, sticky="w")
        ttk.Entry(top_frame, textvariable=self.customer_name_var, width=35).grid(
            row=1, column=1, padx=(0, 10), sticky="w"
        )

        ttk.Label(top_frame, text="Customer Phone").grid(row=0, column=2, sticky="w")
        ttk.Entry(top_frame, textvariable=self.customer_phone_var, width=25).grid(
            row=1, column=2, sticky="w"
        )

        mid_frame = ttk.LabelFrame(self.root, text="Add Line Item", padding=10)
        mid_frame.pack(fill="x", padx=10, pady=8)

        self.product_var = tk.StringVar()
        self.qty_var = tk.StringVar(value="1")
        self.price_var = tk.StringVar(value="0.00")

        ttk.Label(mid_frame, text="Product / Service").grid(row=0, column=0, sticky="w")
        ttk.Entry(mid_frame, textvariable=self.product_var, width=35).grid(
            row=1, column=0, padx=(0, 10), sticky="w"
        )

        ttk.Label(mid_frame, text="Qty").grid(row=0, column=1, sticky="w")
        ttk.Entry(mid_frame, textvariable=self.qty_var, width=8).grid(
            row=1, column=1, padx=(0, 10), sticky="w"
        )

        ttk.Label(mid_frame, text="Unit Price").grid(row=0, column=2, sticky="w")
        ttk.Entry(mid_frame, textvariable=self.price_var, width=12).grid(
            row=1, column=2, padx=(0, 10), sticky="w"
        )

        ttk.Button(mid_frame, text="Add Item", command=self.add_item).grid(
            row=1, column=3, padx=(10, 0)
        )
        ttk.Button(mid_frame, text="Remove Selected", command=self.remove_selected).grid(
            row=1, column=4, padx=(10, 0)
        )

        table_frame = ttk.Frame(self.root, padding=10)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("product", "qty", "price", "subtotal"),
            show="headings",
            height=12,
        )
        self.tree.heading("product", text="Product / Service")
        self.tree.heading("qty", text="Qty")
        self.tree.heading("price", text="Unit Price")
        self.tree.heading("subtotal", text="Subtotal")

        self.tree.column("product", width=380)
        self.tree.column("qty", width=90, anchor="center")
        self.tree.column("price", width=130, anchor="e")
        self.tree.column("subtotal", width=130, anchor="e")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        totals_frame = ttk.LabelFrame(self.root, text="Summary", padding=10)
        totals_frame.pack(fill="x", padx=10, pady=8)

        self.subtotal_var = tk.StringVar(value="0.00")
        self.tax_var = tk.StringVar(value="0.00")
        self.total_var = tk.StringVar(value="0.00")

        ttk.Label(totals_frame, text="Subtotal").grid(row=0, column=0, sticky="w")
        ttk.Label(totals_frame, textvariable=self.subtotal_var, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=1, padx=(4, 20), sticky="w"
        )

        ttk.Label(totals_frame, text=f"Tax ({int(self.TAX_RATE * 100)}%)").grid(
            row=0, column=2, sticky="w"
        )
        ttk.Label(totals_frame, textvariable=self.tax_var, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=3, padx=(4, 20), sticky="w"
        )

        ttk.Label(totals_frame, text="Grand Total").grid(row=0, column=4, sticky="w")
        ttk.Label(
            totals_frame,
            textvariable=self.total_var,
            font=("Segoe UI", 11, "bold"),
            foreground="#0b6d1b",
        ).grid(row=0, column=5, padx=(4, 20), sticky="w")

        actions = ttk.Frame(self.root, padding=10)
        actions.pack(fill="x")

        ttk.Button(actions, text="Export Invoice (CSV)", command=self.export_invoice_csv).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Print Summary (TXT)", command=self.export_invoice_txt).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Top Selling Items", command=self.show_top_selling).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="New Invoice", command=self.reset_invoice).pack(side="right")

    def add_item(self) -> None:
        product = self.product_var.get().strip()
        if not product:
            messagebox.showerror("Missing Product", "Please enter product/service name.")
            return

        try:
            qty = int(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Quantity", "Quantity should be a positive integer.")
            return

        try:
            price = float(self.price_var.get())
            if price < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Price", "Unit price should be a non-negative number.")
            return

        item = InvoiceItem(product=product, qty=qty, unit_price=price)
        self.items.append(item)
        self.sales_ledger[product] = self.sales_ledger.get(product, 0) + qty

        self.tree.insert(
            "",
            "end",
            values=(
                item.product,
                item.qty,
                f"{item.unit_price:,.2f}",
                f"{item.subtotal:,.2f}",
            ),
        )

        self.product_var.set("")
        self.qty_var.set("1")
        self.price_var.set("0.00")
        self._refresh_totals()

    def remove_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Select a row to remove.")
            return

        for row_id in selected:
            values = self.tree.item(row_id, "values")
            product = str(values[0])
            qty = int(values[1])
            self.sales_ledger[product] = max(0, self.sales_ledger.get(product, 0) - qty)
            self.tree.delete(row_id)

        self.items = []
        for row_id in self.tree.get_children(""):
            values = self.tree.item(row_id, "values")
            self.items.append(
                InvoiceItem(
                    product=str(values[0]),
                    qty=int(values[1]),
                    unit_price=float(str(values[2]).replace(",", "")),
                )
            )

        self._refresh_totals()

    def _refresh_totals(self) -> None:
        subtotal = sum(item.subtotal for item in self.items)
        tax = subtotal * self.TAX_RATE
        total = subtotal + tax

        self.subtotal_var.set(f"{subtotal:,.2f}")
        self.tax_var.set(f"{tax:,.2f}")
        self.total_var.set(f"{total:,.2f}")

    def export_invoice_csv(self) -> None:
        if not self.items:
            messagebox.showwarning("No Data", "Please add at least one item first.")
            return

        default_name = f"{self.invoice_no_var.get() or 'invoice'}.csv"
        file_path = filedialog.asksaveasfilename(
            title="Save Invoice CSV",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV Files", "*.csv")],
        )
        if not file_path:
            return

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Invoice #", self.invoice_no_var.get()])
            writer.writerow(["Date", f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}"])
            writer.writerow(["Customer", self.customer_name_var.get()])
            writer.writerow(["Phone", self.customer_phone_var.get()])
            writer.writerow([])
            writer.writerow(["Product", "Qty", "Unit Price", "Subtotal"])
            for item in self.items:
                writer.writerow([item.product, item.qty, f"{item.unit_price:.2f}", f"{item.subtotal:.2f}"])

            subtotal = sum(i.subtotal for i in self.items)
            tax = subtotal * self.TAX_RATE
            total = subtotal + tax

            writer.writerow([])
            writer.writerow(["", "", "Subtotal", f"{subtotal:.2f}"])
            writer.writerow(["", "", "Tax", f"{tax:.2f}"])
            writer.writerow(["", "", "Total", f"{total:.2f}"])

        messagebox.showinfo("Saved", f"Invoice exported to:\n{file_path}")

    def export_invoice_txt(self) -> None:
        if not self.items:
            messagebox.showwarning("No Data", "Please add at least one item first.")
            return

        default_name = f"{self.invoice_no_var.get() or 'invoice'}.txt"
        file_path = filedialog.asksaveasfilename(
            title="Save Invoice Summary",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text Files", "*.txt")],
        )
        if not file_path:
            return

        subtotal = sum(i.subtotal for i in self.items)
        tax = subtotal * self.TAX_RATE
        total = subtotal + tax

        lines = [
            "=" * 60,
            "INVOICE SUMMARY",
            "=" * 60,
            f"Invoice #: {self.invoice_no_var.get()}",
            f"Date: {dt.datetime.now():%Y-%m-%d %H:%M:%S}",
            f"Customer: {self.customer_name_var.get()}",
            f"Phone: {self.customer_phone_var.get()}",
            "-" * 60,
            f"{'Item':25} {'Qty':>5} {'Price':>12} {'Subtotal':>12}",
            "-" * 60,
        ]

        for item in self.items:
            lines.append(
                f"{item.product[:25]:25} {item.qty:>5} {item.unit_price:>12.2f} {item.subtotal:>12.2f}"
            )

        lines.extend(
            [
                "-" * 60,
                f"{'Subtotal':>44} {subtotal:>12.2f}",
                f"{'Tax':>44} {tax:>12.2f}",
                f"{'Grand Total':>44} {total:>12.2f}",
                "=" * 60,
            ]
        )

        Path(file_path).write_text("\n".join(lines), encoding="utf-8")
        messagebox.showinfo("Saved", f"Summary exported to:\n{file_path}")

    def show_top_selling(self) -> None:
        ranked = sorted(
            ((name, qty) for name, qty in self.sales_ledger.items() if qty > 0),
            key=lambda x: x[1],
            reverse=True,
        )

        if not ranked:
            messagebox.showinfo("No Sales Yet", "Add line items to build the selling report.")
            return

        message = "Top Selling Items\n\n" + "\n".join(
            f"{idx}. {name} - {qty} unit(s)" for idx, (name, qty) in enumerate(ranked[:10], start=1)
        )
        messagebox.showinfo("Fastest Selling", message)

    def reset_invoice(self) -> None:
        self.items.clear()
        self.tree.delete(*self.tree.get_children())
        self.customer_name_var.set("")
        self.customer_phone_var.set("")
        self.invoice_no_var.set(f"INV-{dt.datetime.now():%Y%m%d-%H%M%S}")
        self._refresh_totals()


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    app = AccountingBillingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()