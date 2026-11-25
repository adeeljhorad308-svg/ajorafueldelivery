// Table rows (tablet/laptop) open Track order on click, same as the mobile
// cards' own <a> wrapper; the trailing chevron link still works for keyboard
// and screen reader users without relying on the row click.
export function initMyOrdersTable() {
  document.querySelectorAll(".order-table__row[data-href]").forEach((row) => {
    row.addEventListener("click", (event) => {
      if (event.target.closest("a")) return;
      window.location.href = row.dataset.href;
    });
  });
}

initMyOrdersTable();
